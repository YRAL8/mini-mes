"""Visitor tracker: tails Caddy's JSON access log and reports new visitors to
Telegram. Offline GeoIP (country + network operator) via geoip2fast — no
third-party lookup service sees the visitor's IP.

Repeat hits from the same IP within NOTIFY_COOLDOWN_SEC are collapsed into one
notification, so a single visit browsing several pages does not spam the chat.
Starts at the end of the log file: history from before the container's first
boot is not replayed.
"""

import json
import os
import time
from ipaddress import ip_address
from pathlib import Path

import requests
import geoip2fast
from geoip2fast import GeoIP2Fast

LOG_PATH = Path(os.getenv("ACCESS_LOG_PATH", "/var/log/caddy/access.log"))
STATE_PATH = Path(os.getenv("STATE_PATH", "/state/seen_ips.json"))
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
COOLDOWN_SEC = int(os.getenv("NOTIFY_COOLDOWN_SEC", "1800"))
EXCLUDE_IPS = {ip.strip() for ip in os.getenv("EXCLUDE_IPS", "").split(",") if ip.strip()}

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# The plain package ships country-only data; the ASN-enabled database
# (bundled alongside it) additionally names the network operator.
_asn_db_path = os.path.join(os.path.dirname(geoip2fast.__file__), "geoip2fast-asn.dat.gz")
geoip = GeoIP2Fast(geoip2fast_data_file=_asn_db_path, verbose=False)


def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state))


def notify(text: str) -> None:
    try:
        requests.post(TELEGRAM_API, data={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except requests.RequestException as exc:
        print(f"[watcher] Telegram send failed: {exc}", flush=True)


def describe(ip: str, path: str, user_agent: str, referer: str) -> str:
    info = geoip.lookup(ip)
    place = info.country_name or "unbekannt"
    org = info.asn_name or "unbekannter Provider"
    ref = referer if referer and referer != "-" else "direkt"
    return (
        f"\U0001F440 Neuer Besucher\n"
        f"IP: {ip}\n"
        f"Ort/Netz: {place} — {org}\n"
        f"Seite: {path}\n"
        f"Herkunft: {ref}\n"
        f"User-Agent: {user_agent[:120]}"
    )


def handle_line(line: str, state: dict) -> None:
    try:
        rec = json.loads(line)
    except json.JSONDecodeError:
        return
    # An unnamed `log` block in the Caddyfile gets an auto name (log0, log1, ...
    # appended to the logger), so match the prefix rather than the exact string.
    if not rec.get("logger", "").startswith("http.log.access"):
        return

    req = rec.get("request", {})
    ip = req.get("remote_ip", "")
    if not ip or ip in EXCLUDE_IPS:
        return
    try:
        if ip_address(ip).is_private or ip_address(ip).is_loopback:
            return
    except ValueError:
        return

    now = time.time()
    last = state.get(ip, 0)
    if now - last < COOLDOWN_SEC:
        state[ip] = now
        return

    headers = req.get("headers", {})
    user_agent = (headers.get("User-Agent") or [""])[0]
    referer = (headers.get("Referer") or [""])[0]
    path = req.get("uri", "/")

    notify(describe(ip, path, user_agent, referer))
    state[ip] = now


def follow(path: Path):
    """Yield new lines appended to `path`, transparently handling Caddy's
    roll-based log rotation (the file's inode changes when it rolls)."""
    while not path.exists():
        time.sleep(2)
    f = path.open("r")
    f.seek(0, os.SEEK_END)
    inode = os.fstat(f.fileno()).st_ino
    while True:
        line = f.readline()
        if line:
            yield line
            continue
        time.sleep(1)
        try:
            if os.stat(path).st_ino != inode:
                f.close()
                f = path.open("r")
                inode = os.fstat(f.fileno()).st_ino
        except FileNotFoundError:
            continue


def main() -> None:
    state = load_state()
    print(f"[watcher] watching {LOG_PATH}, cooldown {COOLDOWN_SEC}s", flush=True)
    last_save = time.time()
    for line in follow(LOG_PATH):
        handle_line(line, state)
        if time.time() - last_save > 30:
            save_state(state)
            last_save = time.time()


if __name__ == "__main__":
    main()

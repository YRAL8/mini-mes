"""Machine emulator for a bottle-decorating line (OT side).

Simulates a single production line ("Linie 1") as a small state machine and
publishes telemetry + events to MQTT once per tick. This stands in for a real
PLC / BDE terminal: the rest of the stack never knows the data is simulated.

Topics:
  mini-mes/line1/telemetry  – per-tick production data (JSON)
  mini-mes/line1/events     – state-change events, German text (JSON)
"""

import json
import os
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MACHINE_ID = os.getenv("MACHINE_ID", "line1")
TICK_S = float(os.getenv("TICK_S", "1.0"))
# Ideal cycle time per bottle. 333 ms  ->  3 bottles/s at full performance.
IDEAL_CYCLE_MS = float(os.getenv("IDEAL_CYCLE_MS", "333"))

TOPIC_TELEMETRY = f"mini-mes/{MACHINE_ID}/telemetry"
TOPIC_EVENTS = f"mini-mes/{MACHINE_ID}/events"

# State-transition probabilities per tick. Tuned so the line behaves like a real
# one: a short stop roughly every two minutes, a fault every few minutes, each
# lasting long enough to matter. Availability settles around 87 %.
P_RUN_TO_ERROR = 0.004
P_RUN_TO_IDLE = 0.008
P_IDLE_TO_RUN = 0.10
P_ERROR_TO_RUN = 0.06
REJECT_RATE = 0.02  # share of produced bottles that are defective

# The emulator is the OT side and knows nothing about warehouse levels, so its
# idle text stays neutral. The material-shortage message ("Warten auf Nachschub")
# is booked by the ERP module in the backend, which does know the real stock.
EVENT_TEXT = {
    ("running", "error"): ("error", "Störung erkannt — Linie gestoppt"),
    ("running", "idle"): ("warn", "Kurzstillstand — Linie im Leerlauf"),
    ("idle", "running"): ("info", "Linie wieder in Betrieb"),
    ("error", "running"): ("info", "Störung behoben — Produktion läuft"),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def next_status(status: str) -> str:
    r = random.random()
    if status == "running":
        if r < P_RUN_TO_ERROR:
            return "error"
        if r < P_RUN_TO_ERROR + P_RUN_TO_IDLE:
            return "idle"
        return "running"
    if status == "idle":
        return "running" if r < P_IDLE_TO_RUN else "idle"
    # error
    return "running" if r < P_ERROR_TO_RUN else "error"


def main() -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"emulator-{MACHINE_ID}")
    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
            break
        except OSError as exc:
            print(f"[emulator] MQTT not ready ({exc}); retrying in 2s", flush=True)
            time.sleep(2)
    client.loop_start()
    print(f"[emulator] connected to {MQTT_HOST}:{MQTT_PORT}, publishing to {TOPIC_TELEMETRY}", flush=True)

    status = "running"
    while True:
        new_status = next_status(status)
        if new_status != status:
            key = (status, new_status)
            if key in EVENT_TEXT:
                level, message = EVENT_TEXT[key]
                client.publish(
                    TOPIC_EVENTS,
                    json.dumps({"machine_id": MACHINE_ID, "ts": now_iso(),
                                "level": level, "message": message}),
                )
            status = new_status

        produced = 0
        rejects = 0
        cycle_ms = IDEAL_CYCLE_MS
        if status == "running":
            # Performance loss: real cycle a bit slower than ideal.
            cycle_ms = IDEAL_CYCLE_MS * random.uniform(1.0, 1.25)
            total = max(1, round(TICK_S * 1000.0 / cycle_ms))
            rejects = sum(1 for _ in range(total) if random.random() < REJECT_RATE)
            produced = total - rejects

        client.publish(
            TOPIC_TELEMETRY,
            json.dumps({
                "machine_id": MACHINE_ID,
                "ts": now_iso(),
                "status": status,
                "produced": produced,
                "rejects": rejects,
                "cycle_ms": round(cycle_ms, 1),
            }),
        )
        time.sleep(TICK_S)


if __name__ == "__main__":
    main()

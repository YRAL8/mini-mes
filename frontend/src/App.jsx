import React, { useEffect, useRef, useState } from "react";

// ---- Design tokens (dark industrial: factory floor at night) ----
// bg #14181C · panel #1D2329 · hairline #2A3138
// amber #E8A33D (bottle glass) · teal #4FB286 (running) · red #E15B4F (error)
// ink #EDEFF1 · ink-dim #8A939C

const STATUS_META = {
  running: { label: "LÄUFT", color: "#4FB286", glow: "rgba(79,178,134,0.35)" },
  idle: { label: "LEERLAUF", color: "#E8A33D", glow: "rgba(232,163,61,0.35)" },
  error: { label: "STÖRUNG", color: "#E15B4F", glow: "rgba(225,91,79,0.35)" },
};

const WS_URL =
  import.meta.env.VITE_WS_URL ||
  `ws://${window.location.hostname}:8000/ws`;

function fmtTime(iso) {
  if (!iso) return "--:--:--";
  const d = new Date(iso);
  return d.toTimeString().slice(0, 8);
}

function Bottle({ fillPct, color }) {
  const clampedFill = Math.max(0, Math.min(100, fillPct || 0));
  return (
    <svg width="34" height="64" viewBox="0 0 34 64" aria-hidden="true">
      <defs>
        <clipPath id="bottleClip">
          <path d="M12 2 H22 V12 C22 14 26 16 26 22 V58 C26 61 23 63 20 63 H14 C11 63 8 61 8 58 V22 C8 16 12 14 12 12 Z" />
        </clipPath>
      </defs>
      <path
        d="M12 2 H22 V12 C22 14 26 16 26 22 V58 C26 61 23 63 20 63 H14 C11 63 8 61 8 58 V22 C8 16 12 14 12 12 Z"
        fill="none"
        stroke="#3A4149"
        strokeWidth="1.5"
      />
      <g clipPath="url(#bottleClip)">
        <rect
          x="6"
          y={63 - (58 * clampedFill) / 100}
          width="22"
          height={(58 * clampedFill) / 100}
          fill={color}
          opacity="0.85"
          style={{ transition: "y 0.6s ease, height 0.6s ease" }}
        />
      </g>
    </svg>
  );
}

function StatBlock({ eyebrow, value, unit, accent }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 19, letterSpacing: "0.12em", color: "#8A939C", textTransform: "uppercase" }}>
        {eyebrow}
      </span>
      <span style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
        <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 60, fontWeight: 600, color: accent || "#EDEFF1", lineHeight: 1 }}>
          {value}
        </span>
        {unit && (
          <span style={{ fontSize: 22, color: "#8A939C", fontFamily: "'IBM Plex Mono', monospace" }}>{unit}</span>
        )}
      </span>
    </div>
  );
}

// The two stocks are critical at opposite ends of the same bar: raw material
// when it runs out (line starves), finished goods when the buffer fills up
// (line blocks). `critical` says which end deserves the alarm colour.
function InventoryBar({ label, current, max, unit, critical = "empty" }) {
  const pct = Math.max(0, Math.min(100, (current / max) * 100));
  const alarm = critical === "empty" ? pct < 20 : pct >= 98;
  const warn = critical === "empty" ? pct < 35 : pct >= 85;
  const barColor = alarm ? "#E15B4F" : warn ? "#E8A33D" : "#4FB286";
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <span style={{ fontSize: 22, color: "#8A939C", fontFamily: "'IBM Plex Mono', monospace" }}>{label}</span>
        <span style={{ fontSize: 22, fontFamily: "'IBM Plex Mono', monospace", color: alarm ? "#E15B4F" : "#EDEFF1" }}>
          {Math.round(current).toLocaleString("de-DE")} {unit}
        </span>
      </div>
      <div style={{ height: 6, background: "#2A3138", borderRadius: 3, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${pct}%`, background: barColor, transition: "width 0.6s ease, background 0.4s ease" }} />
      </div>
    </div>
  );
}

const EMPTY = {
  status: "idle",
  units_produced: 0,
  oee: 0,
  availability: 0,
  raw_material: 0,
  finished_goods: 0,
  raw_start: 4000,
  finished_capacity: 3000,
  reichweite_min: null,
  downtime_risk: 0,
  events: [],
};

export default function App() {
  const [snap, setSnap] = useState(EMPTY);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);

  useEffect(() => {
    let stopped = false;
    let retry;

    function connect() {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;
      ws.onopen = () => setConnected(true);
      ws.onmessage = (ev) => {
        try {
          setSnap(JSON.parse(ev.data));
        } catch {
          /* ignore malformed frame */
        }
      };
      ws.onclose = () => {
        setConnected(false);
        if (!stopped) retry = setTimeout(connect, 1500);
      };
      ws.onerror = () => ws.close();
    }
    connect();
    return () => {
      stopped = true;
      clearTimeout(retry);
      wsRef.current?.close();
    };
  }, []);

  const meta = STATUS_META[snap.status] || STATUS_META.idle;
  const oee = snap.oee || 0;
  const risk = snap.downtime_risk || 0;
  const riskColor = risk > 60 ? "#E15B4F" : risk > 30 ? "#E8A33D" : "#4FB286";

  return (
    <div style={{ minHeight: "100vh", background: "#14181C", color: "#EDEFF1", fontFamily: "'Inter', -apple-system, sans-serif", padding: "28px 20px 60px" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
        * { box-sizing: border-box; }
      `}</style>

      {/* Header */}
      <div style={{ maxWidth: 1240, margin: "0 auto 24px", display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 12 }}>
        <div>
          <div style={{ fontSize: 19, letterSpacing: "0.16em", color: "#8A939C", fontFamily: "'IBM Plex Mono', monospace", marginBottom: 6 }}>
            MINI-MES · LINIE 1 · HEHLEN
          </div>
          <h1 style={{ margin: 0, fontSize: 52, fontWeight: 700, letterSpacing: "-0.01em" }}>
            Produktions- &amp; Lager-Dashboard
          </h1>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, fontFamily: "'IBM Plex Mono', monospace", fontSize: 22, color: connected ? "#4FB286" : "#E15B4F" }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: connected ? "#4FB286" : "#E15B4F" }} />
          {connected ? "LIVE · WebSocket" : "getrennt — verbinde…"}
        </div>
      </div>

      <div style={{ maxWidth: 1240, margin: "0 auto", display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: 16 }}>
        {/* Machine status / MES card */}
        <div style={{ background: "#1D2329", border: "1px solid #2A3138", borderRadius: 12, padding: 30, display: "flex", flexDirection: "column", gap: 24 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ width: 10, height: 10, borderRadius: "50%", background: meta.color, boxShadow: `0 0 0 6px ${meta.glow}` }} />
            <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 24, fontWeight: 600, color: meta.color, letterSpacing: "0.04em" }}>
              {meta.label}
            </span>
            <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 22, color: "#8A939C", marginLeft: "auto" }}>Maschine #1</span>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
            <StatBlock eyebrow="Stück produziert" value={(snap.units_produced || 0).toLocaleString("de-DE")} unit="Stk" />
            <StatBlock eyebrow="OEE" value={oee.toFixed(1)} unit="%" accent={oee > 75 ? "#4FB286" : oee > 50 ? "#E8A33D" : "#E15B4F"} />
            <StatBlock eyebrow="Verfügbarkeit" value={(snap.availability || 0).toFixed(1)} unit="%" />
          </div>

          {/* How that OEE came about — every factor traceable to the raw data. */}
          <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 19, color: "#8A939C", marginTop: -8 }}>
            OEE = Verfügbarkeit {(snap.availability || 0).toFixed(1)} %
            {" × "}Leistung {(snap.performance || 0).toFixed(1)} %
            {" × "}Qualität {(snap.quality || 0).toFixed(1)} %
          </div>

          {/* KI module: downtime risk */}
          <div style={{ display: "flex", alignItems: "center", gap: 12, borderTop: "1px solid #2A3138", paddingTop: 14 }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 19, letterSpacing: "0.12em", color: "#8A939C", fontFamily: "'IBM Plex Mono', monospace", textTransform: "uppercase", marginBottom: 6 }}>
                KI · Störungsrisiko
              </div>
              <div style={{ height: 6, background: "#2A3138", borderRadius: 3, overflow: "hidden" }}>
                <div style={{ height: "100%", width: `${Math.min(100, risk)}%`, background: riskColor, transition: "width 0.6s ease, background 0.4s ease" }} />
              </div>
            </div>
            <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 33, fontWeight: 600, color: riskColor }}>{risk.toFixed(0)}%</span>
          </div>

          <div>
            <div style={{ fontSize: 19, letterSpacing: "0.12em", color: "#8A939C", fontFamily: "'IBM Plex Mono', monospace", marginBottom: 8, textTransform: "uppercase" }}>
              Ereignisprotokoll
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {(snap.events || []).length === 0 && (
                <div style={{ fontSize: 22, fontFamily: "'IBM Plex Mono', monospace", color: "#5C646C" }}>— warte auf Ereignisse —</div>
              )}
              {(snap.events || []).map((e, i) => (
                <div key={i} style={{ display: "flex", gap: 10, fontSize: 22, fontFamily: "'IBM Plex Mono', monospace", color: i === 0 ? "#EDEFF1" : "#5C646C" }}>
                  <span>{fmtTime(e.ts)}</span>
                  <span>{e.message}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Warehouse / ERP card */}
        <div style={{ background: "#1D2329", border: "1px solid #2A3138", borderRadius: 12, padding: 30, display: "flex", flexDirection: "column", gap: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: 19, letterSpacing: "0.12em", color: "#8A939C", fontFamily: "'IBM Plex Mono', monospace", textTransform: "uppercase" }}>
              ERP · Lagerbestand
            </span>
            <Bottle fillPct={((snap.finished_goods || 0) / (snap.finished_capacity || 1)) * 100} color="#E8A33D" />
          </div>

          <InventoryBar label="Rohmaterial (Vorformlinge)" current={snap.raw_material || 0} max={snap.raw_start || 4000} unit="Stk" critical="empty" />
          <InventoryBar label="Fertigware" current={snap.finished_goods || 0} max={snap.finished_capacity || 3000} unit="Stk" critical="full" />

          <div style={{ borderTop: "1px solid #2A3138", paddingTop: 14, display: "flex", flexDirection: "column", gap: 4 }}>
            <span style={{ fontSize: 19, color: "#8A939C", fontFamily: "'IBM Plex Mono', monospace" }}>
              Reichweite Rohmaterial bei aktueller Rate
            </span>
            <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 33, fontWeight: 600 }}>
              {snap.reichweite_min == null ? "—" : `~ ${Math.round(snap.reichweite_min)} Min`}
            </span>
          </div>
        </div>
      </div>

      <div style={{ maxWidth: 1240, margin: "18px auto 0", fontSize: 19, color: "#5C646C", fontFamily: "'IBM Plex Mono', monospace", lineHeight: 1.6 }}>
        Live-Daten aus der Kette Maschine (OT) → MQTT → FastAPI → PostgreSQL → Dashboard.
        MES-Kennzahlen links, ERP-Lagerbestand rechts — orchestriert über Docker Compose.
      </div>
    </div>
  );
}

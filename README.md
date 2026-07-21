# Mini-MES

Ein kompaktes **Manufacturing-Execution-System** als Portfolio-Projekt: von den
Maschinendaten (OT) über MES-Kennzahlen und automatischen Lagerabgleich (ERP)
bis zum Live-Dashboard — vollständig containerisiert und mit **einem Befehl**
lauffähig.

Ein einziges Maschinenereignis durchläuft die gesamte Kette:

```
Maschine (OT) → MQTT → FastAPI (MES) → PostgreSQL → ERP-Lager → KPI-Dashboard
```

## Schnellstart

Voraussetzung: Docker und Docker Compose.

```bash
git clone https://github.com/YRAL8/mini-mes.git
cd mini-mes
docker compose up --build
```

Danach:

- **Dashboard:** http://localhost:5173
- **API-Doku (Swagger):** http://localhost:8000/docs
- **Aktueller Zustand:** http://localhost:8000/api/state

Der Emulator startet automatisch und speist die Kette mit Live-Daten.

## Was das Projekt zeigt

| Fähigkeit | Umsetzung im Projekt |
| --- | --- |
| **MES / BDE / MDE** | Live-Erfassung von Maschinenstatus, Stückzahl und OEE |
| **ERP-Anbindung (Lager)** | Automatischer Bestandsabgleich Rohmaterial ↔ Fertigware, Wareneingangsbuchung |
| **KI-gestützte Analyse** | Anomalieerkennung (IsolationForest) → Störungsrisiko |
| **OT/IT-Integration** | Entkopplung über MQTT: Maschine → Backend → Datenbank → UI |
| **KPI-Dashboard** | Live-Ansicht: Produktion links, Lager rechts (WebSocket) |
| **Python-Stack** | Emulator, MES-Logik und API vollständig in Python |

## Architektur

Siehe [docs/architecture.md](docs/architecture.md) für das Diagramm und den
Datenfluss im Detail.

```
┌─────────────┐   MQTT    ┌──────────────┐   SQL    ┌────────────┐
│  Emulator   │ ────────▶ │  FastAPI-MES │ ───────▶ │ PostgreSQL │
│ Maschine OT │           │  OEE · ERP   │          │  KPI-Store │
└─────────────┘           │  KI-Risiko   │          └────────────┘
                          └──────┬───────┘
                                 │ WebSocket / REST
                                 ▼
                          ┌────────────┐
                          │  Dashboard │
                          │   (React)  │
                          └────────────┘
```

## OEE — nachvollziehbar berechnet

```
OEE = Verfügbarkeit × Leistung × Qualität

  Verfügbarkeit = Laufzeit / (Laufzeit + Stillstand)
  Leistung      = produzierte Menge / ideale Menge (bei Idealtakt)
  Qualität      = Gutmenge / produzierte Menge
```

Alle Werte leiten sich direkt aus den Rohdaten der Maschine ab — jede Kennzahl
ist bis zum einzelnen Maschinen-Tick rückverfolgbar.

## Tech-Stack

| Bereich | Technologie |
| --- | --- |
| Backend / MES | Python, FastAPI, paho-mqtt |
| Nachrichten (OT→IT) | MQTT / Eclipse Mosquitto |
| Datenbank | PostgreSQL (SQLAlchemy) |
| KI | scikit-learn (IsolationForest) |
| Dashboard | React (Vite) |
| Betrieb | Docker Compose |

## Projektstruktur

```
mini-mes/
├── emulator/     Maschinen-Emulator (OT), MQTT-Publish
├── backend/      FastAPI-MES: MQTT-Consumer, OEE, ERP, KI, API/WebSocket
├── frontend/     React-KPI-Dashboard
├── mosquitto/    MQTT-Broker-Konfiguration
├── docs/         Architektur & Datenfluss
└── docker-compose.yml
```

## Konfiguration

Alle Parameter (Lagerbestände, Idealtakt, Meldebestand …) sind über
Umgebungsvariablen einstellbar — siehe [.env.example](.env.example).

## Lizenz

MIT — siehe [LICENSE](LICENSE).

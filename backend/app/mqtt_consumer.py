"""MQTT ingest — the OT->IT bridge.

Runs a paho client in its own thread (loop_start). Each message updates the
in-memory LineStore and is persisted to PostgreSQL.
"""

import json

import paho.mqtt.client as mqtt

from .config import MACHINE_ID, MQTT_HOST, MQTT_PORT
from .db import SessionLocal
from .models import Event, Telemetry
from .store import LineStore

TOPIC_TELEMETRY = f"mini-mes/{MACHINE_ID}/telemetry"
TOPIC_EVENTS = f"mini-mes/{MACHINE_ID}/events"


class MqttConsumer:
    def __init__(self, store: LineStore) -> None:
        self.store = store
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                  client_id="mes-backend")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def start(self) -> None:
        self.client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
        self.client.loop_start()

    def stop(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        client.subscribe([(TOPIC_TELEMETRY, 0), (TOPIC_EVENTS, 0)])
        print(f"[backend] subscribed to {TOPIC_TELEMETRY}, {TOPIC_EVENTS}", flush=True)

    def _on_message(self, client, userdata, message) -> None:
        try:
            payload = json.loads(message.payload.decode())
        except (ValueError, UnicodeDecodeError):
            return

        if message.topic == TOPIC_TELEMETRY:
            self._handle_telemetry(payload)
        elif message.topic == TOPIC_EVENTS:
            self._handle_event(payload)

    def _handle_telemetry(self, payload: dict) -> None:
        erp_events = self.store.process_telemetry(payload)
        with SessionLocal() as session:
            session.add(Telemetry(
                machine_id=payload.get("machine_id", MACHINE_ID),
                status=payload["status"],
                produced=int(payload.get("produced", 0)),
                rejects=int(payload.get("rejects", 0)),
                cycle_ms=float(payload.get("cycle_ms", 0.0)),
            ))
            for level, msg in erp_events:
                self.store.add_event(level, msg)
                session.add(Event(machine_id=MACHINE_ID, level=level, message=msg))
            session.commit()

    def _handle_event(self, payload: dict) -> None:
        level = payload.get("level", "info")
        msg = payload.get("message", "")
        self.store.add_event(level, msg)
        with SessionLocal() as session:
            session.add(Event(
                machine_id=payload.get("machine_id", MACHINE_ID),
                level=level, message=msg,
            ))
            session.commit()

"""In-memory line state, updated by the MQTT thread and read by the API/WS.

A single lock guards the accumulators; snapshots are cheap dict copies so the
web layer never blocks the ingest path for long.
"""

import threading
from collections import deque
from datetime import datetime, timezone

from . import oee
from .ai import DowntimeRiskModel
from .config import FINISHED_CAPACITY, MACHINE_ID, RAW_START
from .erp import Warehouse


class LineStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.status = "idle"
        self.good_total = 0
        self.reject_total = 0
        self.runtime_sec = 0.0
        self.downtime_sec = 0.0
        self.last_cycle_ms = 0.0
        self.downtime_risk = 0.0
        self.warehouse = Warehouse()
        self.model = DowntimeRiskModel()
        self._recent_produced: deque[int] = deque(maxlen=60)  # ~1 min window
        self._events: deque[dict] = deque(maxlen=30)
        self.updated_at = datetime.now(timezone.utc)

    def add_event(self, level: str, message: str) -> None:
        with self._lock:
            self._events.appendleft({
                "ts": datetime.now(timezone.utc).isoformat(),
                "level": level,
                "message": message,
            })

    def process_telemetry(self, msg: dict) -> str | None:
        """Fold one telemetry message into the running state.

        Returns an ERP event message if a goods receipt was booked, else None.
        """
        with self._lock:
            self.status = msg["status"]
            produced = int(msg.get("produced", 0))
            rejects = int(msg.get("rejects", 0))
            self.last_cycle_ms = float(msg.get("cycle_ms", 0.0))

            if self.status == "running":
                self.runtime_sec += 1.0
                self.good_total += produced
                self.reject_total += rejects
                self._recent_produced.append(produced)
                self.downtime_risk = self.model.update(self.last_cycle_ms, rejects)
            else:
                self.downtime_sec += 1.0
                self._recent_produced.append(0)

            erp_msg = self.warehouse.book_production(produced, rejects)
            self.updated_at = datetime.now(timezone.utc)
            return erp_msg

    def snapshot(self) -> dict:
        with self._lock:
            r = oee.compute(self.runtime_sec, self.downtime_sec,
                            self.good_total, self.reject_total)
            units_per_min = float(sum(self._recent_produced))
            reichweite = self.warehouse.reichweite_min(units_per_min)
            return {
                "machine_id": MACHINE_ID,
                "ts": self.updated_at.isoformat(),
                "status": self.status,
                "units_produced": self.good_total,
                "rejects_total": self.reject_total,
                "oee": round(r.oee * 100, 1),
                "availability": round(r.availability * 100, 1),
                "performance": round(r.performance * 100, 1),
                "quality": round(r.quality * 100, 1),
                "raw_material": self.warehouse.raw_material,
                "finished_goods": self.warehouse.finished_goods,
                "raw_start": RAW_START,
                "finished_capacity": FINISHED_CAPACITY,
                "reichweite_min": None if reichweite == float("inf") else round(reichweite, 1),
                "downtime_risk": round(self.downtime_risk, 1),
                "events": list(self._events)[:6],
            }

    def kpi_row(self) -> dict:
        """Flat dict for persisting a KPI snapshot."""
        s = self.snapshot()
        return {
            "machine_id": s["machine_id"],
            "oee": s["oee"], "availability": s["availability"],
            "performance": s["performance"], "quality": s["quality"],
            "units_produced": s["units_produced"],
            "raw_material": s["raw_material"], "finished_goods": s["finished_goods"],
            "downtime_risk": s["downtime_risk"],
        }

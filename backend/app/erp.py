"""ERP warehouse module — automatic stock reconciliation.

Every produced bottle (good or reject) consumes one raw preform; good bottles
increase finished-goods stock. When raw stock falls below the reorder level, an
automatic goods receipt ("Wareneingang") is booked — the kind of raw<->finished
reconciliation the job posting asks an ERP link to provide.
"""

from dataclasses import dataclass, field

from .config import (FINISHED_CAPACITY, RAW_REORDER_LEVEL, RAW_REORDER_QTY,
                     RAW_START)


@dataclass
class Warehouse:
    raw_material: int = RAW_START
    finished_goods: int = 0
    last_receipt_qty: int = 0

    def book_production(self, good: int, rejects: int) -> str | None:
        """Apply one telemetry tick to stock. Returns an ERP event message if a
        goods receipt was triggered, else None."""
        consumed = good + rejects
        self.raw_material = max(0, self.raw_material - consumed)
        self.finished_goods = min(FINISHED_CAPACITY, self.finished_goods + good)

        if self.raw_material <= RAW_REORDER_LEVEL:
            self.raw_material += RAW_REORDER_QTY
            self.last_receipt_qty = RAW_REORDER_QTY
            return f"Wareneingang gebucht: +{RAW_REORDER_QTY} Vorformlinge"
        return None

    def reichweite_min(self, units_per_min: float) -> float:
        """Estimated raw-material coverage in minutes at the current rate."""
        if units_per_min <= 0:
            return float("inf")
        return self.raw_material / units_per_min

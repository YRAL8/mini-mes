"""ERP warehouse module — automatic stock reconciliation.

Every produced bottle (good or reject) consumes one raw preform; good bottles
increase finished-goods stock. The module books three kinds of ERP event by
itself — the raw<->finished reconciliation the job posting asks an ERP link to
provide:

  * raw stock runs low            -> "Warten auf Nachschub" (warning)
  * raw stock hits reorder level   -> "Wareneingang" (goods receipt)
  * finished buffer reaches capacity -> "Warenausgang" (pallet picked up)

Unlike the machine emulator, this module knows the real stock levels, so its
messages always agree with the figures the dashboard shows next to them.
"""

from dataclasses import dataclass, field

from .config import (FINISHED_CAPACITY, FINISHED_SHIPMENT_QTY,
                     RAW_LOW_WARN_LEVEL, RAW_REORDER_LEVEL, RAW_REORDER_QTY,
                     RAW_START)


@dataclass
class Warehouse:
    raw_material: int = RAW_START
    finished_goods: int = 0
    last_receipt_qty: int = 0
    # Latched so the shortage is reported once per depletion cycle, not per tick.
    low_stock_reported: bool = field(default=False, repr=False)

    def book_production(self, good: int, rejects: int) -> list[tuple[str, str]]:
        """Apply one telemetry tick to stock.

        Returns the ERP events booked for this tick as (level, message) pairs.
        """
        events: list[tuple[str, str]] = []
        consumed = good + rejects
        self.raw_material = max(0, self.raw_material - consumed)
        self.finished_goods = min(FINISHED_CAPACITY, self.finished_goods + good)

        if self.raw_material <= RAW_LOW_WARN_LEVEL and not self.low_stock_reported:
            self.low_stock_reported = True
            events.append(
                ("warn", f"Rohmaterial knapp ({self.raw_material} Stk) — Warten auf Nachschub")
            )

        if self.raw_material <= RAW_REORDER_LEVEL:
            self.raw_material += RAW_REORDER_QTY
            self.last_receipt_qty = RAW_REORDER_QTY
            self.low_stock_reported = False
            events.append(("info", f"Wareneingang gebucht: +{RAW_REORDER_QTY} Vorformlinge"))

        if self.finished_goods >= FINISHED_CAPACITY:
            shipped = min(FINISHED_SHIPMENT_QTY, self.finished_goods)
            self.finished_goods -= shipped
            events.append(("info", f"Warenausgang gebucht: −{shipped} Fertigware abgeholt"))

        return events

    def reichweite_min(self, units_per_min: float) -> float:
        """Estimated raw-material coverage in minutes at the current rate."""
        if units_per_min <= 0:
            return float("inf")
        return self.raw_material / units_per_min

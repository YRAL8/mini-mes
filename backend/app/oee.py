"""OEE calculation — the core MES metric.

OEE = Availability x Performance x Quality

  Availability = runtime / (runtime + downtime)
  Performance  = produced_total / ideal_output(runtime)
  Quality      = good / produced_total

All inputs are simple accumulators updated tick by tick, so the numbers are
fully traceable back to the raw machine data.
"""

from dataclasses import dataclass

from .config import IDEAL_CYCLE_MS


@dataclass
class OeeResult:
    oee: float
    availability: float
    performance: float
    quality: float


def compute(runtime_sec: float, downtime_sec: float,
            good_total: int, reject_total: int) -> OeeResult:
    total_time = runtime_sec + downtime_sec
    availability = runtime_sec / total_time if total_time > 0 else 1.0

    produced_total = good_total + reject_total
    ideal_output = runtime_sec * (1000.0 / IDEAL_CYCLE_MS)
    performance = min(1.0, produced_total / ideal_output) if ideal_output > 0 else 1.0

    quality = good_total / produced_total if produced_total > 0 else 1.0

    return OeeResult(
        oee=availability * performance * quality,
        availability=availability,
        performance=performance,
        quality=quality,
    )

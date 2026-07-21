"""Persistent tables: raw telemetry, events and periodic KPI snapshots."""

from datetime import datetime, timezone

from sqlalchemy import Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Telemetry(Base):
    __tablename__ = "telemetry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(default=utcnow, server_default=func.now())
    machine_id: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16))
    produced: Mapped[int] = mapped_column(Integer)
    rejects: Mapped[int] = mapped_column(Integer)
    cycle_ms: Mapped[float] = mapped_column(Float)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(default=utcnow, server_default=func.now())
    machine_id: Mapped[str] = mapped_column(String(32))
    level: Mapped[str] = mapped_column(String(16))
    message: Mapped[str] = mapped_column(String(256))


class KpiSnapshot(Base):
    __tablename__ = "kpi_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(default=utcnow, server_default=func.now())
    machine_id: Mapped[str] = mapped_column(String(32))
    oee: Mapped[float] = mapped_column(Float)
    availability: Mapped[float] = mapped_column(Float)
    performance: Mapped[float] = mapped_column(Float)
    quality: Mapped[float] = mapped_column(Float)
    units_produced: Mapped[int] = mapped_column(Integer)
    raw_material: Mapped[int] = mapped_column(Integer)
    finished_goods: Mapped[int] = mapped_column(Integer)
    downtime_risk: Mapped[float] = mapped_column(Float)

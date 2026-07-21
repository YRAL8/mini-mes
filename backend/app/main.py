"""FastAPI application: REST + WebSocket for the KPI dashboard."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc, select

from .db import SessionLocal, init_db
from .models import Event, KpiSnapshot
from .mqtt_consumer import MqttConsumer
from .store import LineStore

store = LineStore()
consumer = MqttConsumer(store)


async def _persist_kpi_loop() -> None:
    """Write a KPI snapshot to PostgreSQL every 10 s for the history charts."""
    while True:
        await asyncio.sleep(10)
        try:
            with SessionLocal() as session:
                session.add(KpiSnapshot(**store.kpi_row()))
                session.commit()
        except Exception as exc:  # noqa: BLE001 — never kill the loop
            print(f"[backend] KPI persist failed: {exc}", flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    consumer.start()
    task = asyncio.create_task(_persist_kpi_loop())
    yield
    task.cancel()
    consumer.stop()


app = FastAPI(title="Mini-MES Backend", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/state")
def get_state() -> dict:
    return store.snapshot()


@app.get("/api/events")
def get_events(limit: int = 20) -> list[dict]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(Event).order_by(desc(Event.ts)).limit(limit)
        ).all()
        return [
            {"ts": r.ts.isoformat(), "level": r.level, "message": r.message}
            for r in rows
        ]


@app.get("/api/history")
def get_history(limit: int = 120) -> list[dict]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(KpiSnapshot).order_by(desc(KpiSnapshot.ts)).limit(limit)
        ).all()
        return [
            {
                "ts": r.ts.isoformat(), "oee": r.oee, "availability": r.availability,
                "performance": r.performance, "quality": r.quality,
                "units_produced": r.units_produced, "raw_material": r.raw_material,
                "finished_goods": r.finished_goods, "downtime_risk": r.downtime_risk,
            }
            for r in reversed(rows)
        ]


@app.websocket("/ws")
async def ws(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(store.snapshot())
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return

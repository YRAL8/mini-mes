"""Database engine/session setup (SQLAlchemy 2.0)."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def init_db(retries: int = 30, delay: float = 2.0) -> None:
    """Create tables, waiting for PostgreSQL to accept connections first."""
    import time

    from sqlalchemy.exc import OperationalError

    from . import models  # noqa: F401 — register models on Base

    for attempt in range(retries):
        try:
            Base.metadata.create_all(engine)
            return
        except OperationalError:
            time.sleep(delay)
    # Last attempt — let the error surface.
    Base.metadata.create_all(engine)

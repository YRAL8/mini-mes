"""Central configuration, read from environment (12-factor style)."""

import os

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MACHINE_ID = os.getenv("MACHINE_ID", "line1")

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg2://mes:mes@localhost:5432/mes"
)

# ERP / warehouse
RAW_START = int(os.getenv("RAW_START", "4000"))          # Vorformlinge in stock at boot
FINISHED_CAPACITY = int(os.getenv("FINISHED_CAPACITY", "3000"))
RAW_REORDER_LEVEL = int(os.getenv("RAW_REORDER_LEVEL", "600"))
RAW_REORDER_QTY = int(os.getenv("RAW_REORDER_QTY", "2500"))
# Stock level at which the line reports "waiting for supply" — still above the
# reorder level, so the warning comes before the goods receipt.
RAW_LOW_WARN_LEVEL = int(os.getenv("RAW_LOW_WARN_LEVEL", str(RAW_REORDER_LEVEL * 2)))
# Pallets leave the buffer once it is full, otherwise finished goods would sit
# pinned at capacity forever.
FINISHED_SHIPMENT_QTY = int(os.getenv("FINISHED_SHIPMENT_QTY", "1500"))

# MES
IDEAL_CYCLE_MS = float(os.getenv("IDEAL_CYCLE_MS", "333"))  # ideal time per bottle

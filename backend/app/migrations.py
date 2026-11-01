"""v1.1 - Migración de la BD v1.0 a v1.1 sin perder datos (mantenimiento).

SQLite no permite quitar NOT NULL con ALTER, por eso la tabla notifications se reconstruye.
"""
from sqlalchemy import Engine, inspect, text

from .database import Base

NOTIF_COLS = "id, reservation_id, customer_id, type, channel, recipient, subject, message, status, sent_at"


def migrate(engine: Engine) -> list[str]:
    """Aplica los cambios pendientes y devuelve la lista de pasos ejecutados."""
    steps: list[str] = []
    insp = inspect(engine)
    tables = insp.get_table_names()
    rebuild_notifications = False
    with engine.begin() as conn:
        if "customers" in tables:
            cols = {c["name"] for c in insp.get_columns("customers")}
            for col in ("points", "lifetime_points"):
                if col not in cols:
                    conn.execute(text(f"ALTER TABLE customers ADD COLUMN {col} INTEGER NOT NULL DEFAULT 0"))
                    steps.append(f"customers.{col} agregado")
        if "notifications" in tables:
            rid = next(c for c in insp.get_columns("notifications") if c["name"] == "reservation_id")
            if not rid["nullable"]:
                conn.execute(text("ALTER TABLE notifications RENAME TO notifications_v1"))
                rebuild_notifications = True
    Base.metadata.create_all(bind=engine)  # crea reward_transactions y la nueva notifications
    if rebuild_notifications:
        with engine.begin() as conn:
            conn.execute(text(f"INSERT INTO notifications ({NOTIF_COLS}) SELECT {NOTIF_COLS} FROM notifications_v1"))
            conn.execute(text("DROP TABLE notifications_v1"))
        steps.append("notifications.reservation_id ahora admite NULL (tabla reconstruida, datos copiados)")
    if "reward_transactions" not in tables and tables:
        steps.append("tabla reward_transactions creada")
    return steps

"""Adds new nullable columns to tables that already exist (e.g. on Neon).
SQLAlchemy's create_all() creates missing TABLES but never alters existing
ones, so new fields need this tiny, safe upgrade step. Idempotent."""
from sqlalchemy import inspect, text
from app import db

USER_COLUMNS = {
    "date_of_birth": "DATE",
    "gender": "VARCHAR(20)",
    "nationality": "VARCHAR(60)",
    "city": "VARCHAR(80)",
    "qualification": "VARCHAR(120)",
}


def ensure_user_columns():
    try:
        existing = {c["name"] for c in inspect(db.engine).get_columns("users")}
    except Exception:
        return
    for name, ddl in USER_COLUMNS.items():
        if name in existing:
            continue
        try:
            with db.engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {name} {ddl}"))
        except Exception:
            pass  # another worker added it first, or it already exists

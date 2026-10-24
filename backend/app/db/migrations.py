"""Database schema migrations for FLEETGUARD.

Performs idempotent schema migrations before application startup queries run.
In particular, checks existing database tables for missing columns relative to
the model definitions (e.g. adding missing `incidents.trip_id` column to older databases
and Phase 3 evidence columns) without dropping or resetting tables or losing existing data.
"""

import logging
import os
import sqlite3
from typing import Any

logger = logging.getLogger("fleet.db.migrations")

# Schema specification: Table -> List of (column_name, type_sql, is_nullable, is_indexed)
MIGRATION_SCHEMA: dict[str, list[tuple[str, str, bool, bool]]] = {
    "incidents": [
        ("trip_id", "VARCHAR", True, True),
        ("safety_event_id", "VARCHAR", True, False),
        ("acknowledged_by", "VARCHAR", True, False),
    ],
    "evidence": [
        ("snapshot_path", "VARCHAR", True, False),
        ("sha256_hash", "VARCHAR", True, False),
        ("status", "VARCHAR", True, True),
        ("error_message", "VARCHAR", True, False),
        ("cloud_upload_status", "VARCHAR", True, False),
        ("event_timestamp", "DATETIME", True, False),
        ("recording_start_timestamp", "DATETIME", True, False),
        ("recording_end_timestamp", "DATETIME", True, False),
        ("expires_at", "DATETIME", True, False),
    ],
}


def migrate_sqlite_db_path(db_path: str) -> None:
    """Migrate a SQLite database file directly using standard library sqlite3 (zero dependencies)."""
    if not os.path.exists(db_path):
        logger.info("Database file %s does not exist yet. Migration skipped.", db_path)
        return

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        tables = [t[0] for t in cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]

        for table_name, columns in MIGRATION_SCHEMA.items():
            if table_name not in tables:
                continue

            existing_cols = [c[1] for c in cursor.execute(f"PRAGMA table_info({table_name});").fetchall()]
            for col_name, col_type, nullable, indexed in columns:
                if col_name not in existing_cols:
                    logger.info("Migration: Adding missing column '%s.%s' (%s)", table_name, col_name, col_type)
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type};")
                    if indexed:
                        cursor.execute(f"CREATE INDEX IF NOT EXISTS ix_{table_name}_{col_name} ON {table_name} ({col_name});")
        cursor.close()
        conn.commit()
    finally:
        conn.close()


def run_migrations(engine: Any = None) -> None:
    """Run schema migrations against SQLAlchemy engine or default SQLite database file."""
    if engine is not None:
        try:
            from sqlalchemy import inspect, text

            with engine.connect() as conn:
                inspector = inspect(conn)
                existing_tables = set(inspector.get_table_names())

                for table_name, columns in MIGRATION_SCHEMA.items():
                    if table_name not in existing_tables:
                        continue

                    existing_columns = {c["name"] for c in inspector.get_columns(table_name)}
                    for col_name, col_type, nullable, indexed in columns:
                        if col_name not in existing_columns:
                            logger.info(
                                "Migration: Adding missing column '%s.%s' (%s)",
                                table_name,
                                col_name,
                                col_type,
                            )
                            sql = text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}")
                            conn.execute(sql)
                            if indexed:
                                idx_name = f"ix_{table_name}_{col_name}"
                                conn.execute(
                                    text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} ({col_name})")
                                )
                conn.commit()
            return
        except Exception as e:
            logger.warning("SQLAlchemy migration fallback to sqlite3: %s", e)

    # Direct sqlite3 fallback using configured database or relative default
    default_db_path = os.path.join(os.path.dirname(__file__), "..", "..", "fleet.db")
    migrate_sqlite_db_path(os.path.abspath(default_db_path))


if __name__ == "__main__":
    import sys

    db_file = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "..", "fleet.db")
    print(f"Running migration on {db_file}...")
    migrate_sqlite_db_path(db_file)
    print("Migration complete.")

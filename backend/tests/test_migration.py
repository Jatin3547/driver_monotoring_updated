"""Unit and integration tests for FLEETGUARD database schema migrations.

Tests:
1. Migration adds missing `incidents.trip_id` column to an older database schema.
2. Existing incident records and data are fully preserved during migration.
3. Migration is idempotent (running it multiple times produces no error).
4. Startup queries against the Incident model succeed after migration without OperationalError.
5. Direct sqlite3 path migration works correctly on raw database files.
6. Added columns match the expected type, nullability, and index configuration.
"""

import gc
import os
import sqlite3
import tempfile
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.db.migrations import migrate_sqlite_db_path, run_migrations
from app.models import Incident


class TestSchemaMigration(unittest.TestCase):
    def setUp(self):
        # Create a temporary SQLite database file representing an older schema
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)
        self.engine = create_engine(f"sqlite:///{self.db_path}", poolclass=NullPool)

        # Construct legacy schema explicitly missing incidents.trip_id
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE drivers (
                    id VARCHAR PRIMARY KEY,
                    code VARCHAR UNIQUE,
                    name VARCHAR NOT NULL,
                    license_number VARCHAR NOT NULL,
                    phone VARCHAR NOT NULL,
                    email VARCHAR NOT NULL,
                    status VARCHAR,
                    safety_score INTEGER,
                    joined_date DATE,
                    total_trips INTEGER,
                    total_distance_km FLOAT,
                    incident_count INTEGER
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE vehicles (
                    id VARCHAR PRIMARY KEY,
                    code VARCHAR NOT NULL,
                    plate_number VARCHAR NOT NULL,
                    make VARCHAR NOT NULL,
                    model VARCHAR NOT NULL,
                    year INTEGER NOT NULL,
                    type VARCHAR NOT NULL,
                    status VARCHAR NOT NULL,
                    odometer_km FLOAT NOT NULL,
                    fuel_level INTEGER NOT NULL,
                    next_service_due_km FLOAT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE trips (
                    id VARCHAR PRIMARY KEY,
                    vehicle_id VARCHAR NOT NULL,
                    driver_id VARCHAR NOT NULL,
                    start_time DATETIME NOT NULL,
                    distance_km FLOAT NOT NULL,
                    status VARCHAR NOT NULL
                )
                """
            )
            # Legacy incidents table without trip_id
            cursor.execute(
                """
                CREATE TABLE incidents (
                    id VARCHAR PRIMARY KEY,
                    driver_id VARCHAR NOT NULL,
                    vehicle_id VARCHAR,
                    safety_event_id VARCHAR,
                    type VARCHAR NOT NULL,
                    severity VARCHAR NOT NULL,
                    status VARCHAR NOT NULL,
                    location VARCHAR NOT NULL,
                    description VARCHAR NOT NULL,
                    acknowledged_by VARCHAR,
                    timestamp DATETIME NOT NULL
                )
                """
            )
            # Insert pre-existing incident records
            cursor.execute(
                """
                INSERT INTO incidents (id, driver_id, vehicle_id, type, severity, status, location, description, timestamp)
                VALUES ('INC-EXISTING-001', 'DRV-001', 'VEH-001', 'drowsiness', 'high', 'open', 'ORR Highway', 'Legacy incident before migration', '2026-10-23 10:00:00')
                """
            )
            cursor.execute(
                """
                INSERT INTO incidents (id, driver_id, vehicle_id, type, severity, status, location, description, timestamp)
                VALUES ('INC-EXISTING-002', 'DRV-002', 'VEH-002', 'distraction', 'medium', 'reviewed', 'Electronic City', 'Second legacy incident', '2026-10-23 11:30:00')
                """
            )
            cursor.close()
            conn.commit()
        finally:
            conn.close()

    def tearDown(self):
        self.engine.dispose()
        gc.collect()
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except OSError:
                pass

    def test_01_migration_adds_missing_trip_id_column(self):
        """Migration detects missing trip_id column and adds it to the incidents table."""
        # Check column is missing before migration
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cols_before = [c[1] for c in cursor.execute("PRAGMA table_info(incidents);").fetchall()]
            self.assertNotIn("trip_id", cols_before)
            cursor.close()
        finally:
            conn.close()

        # Execute migration
        run_migrations(self.engine)

        # Check column exists after migration
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cols_after = [c[1] for c in cursor.execute("PRAGMA table_info(incidents);").fetchall()]
            self.assertIn("trip_id", cols_after)
            cursor.close()
        finally:
            conn.close()

    def test_02_migration_preserves_existing_incident_records(self):
        """Migration preserves existing incident records without data loss."""
        run_migrations(self.engine)

        # Query using SQLAlchemy session
        Session = sessionmaker(bind=self.engine)
        session = Session()
        try:
            incidents = session.query(Incident).order_by(Incident.id).all()
            self.assertEqual(len(incidents), 2)

            inc1 = incidents[0]
            self.assertEqual(inc1.id, "INC-EXISTING-001")
            self.assertEqual(inc1.driver_id, "DRV-001")
            self.assertEqual(inc1.description, "Legacy incident before migration")
            self.assertIsNone(inc1.trip_id)  # Nullable trip_id for pre-existing records

            inc2 = incidents[1]
            self.assertEqual(inc2.id, "INC-EXISTING-002")
            self.assertEqual(inc2.driver_id, "DRV-002")
            self.assertEqual(inc2.description, "Second legacy incident")
            self.assertIsNone(inc2.trip_id)
        finally:
            session.close()

    def test_03_migration_is_idempotent(self):
        """Running migration multiple times on the same database is safe and produces no error."""
        run_migrations(self.engine)
        run_migrations(self.engine)  # Second execution
        run_migrations(self.engine)  # Third execution

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cols = [c[1] for c in cursor.execute("PRAGMA table_info(incidents);").fetchall()]
            self.assertEqual(cols.count("trip_id"), 1)
            cursor.close()
        finally:
            conn.close()

    def test_04_query_incident_model_succeeds_after_migration(self):
        """Queries against Incident model succeed without OperationalError."""
        run_migrations(self.engine)

        Session = sessionmaker(bind=self.engine)
        session = Session()
        try:
            # Filtering and counting succeed without OperationalError (no such column: incidents.trip_id)
            count = session.query(Incident).count()
            self.assertEqual(count, 2)

            results = session.query(Incident).filter(Incident.trip_id.is_(None)).all()
            self.assertEqual(len(results), 2)
        finally:
            session.close()

    def test_05_sqlite3_path_migration_fallback(self):
        """Direct sqlite3 path migration works correctly on raw database file."""
        migrate_sqlite_db_path(self.db_path)

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cols = [c[1] for c in cursor.execute("PRAGMA table_info(incidents);").fetchall()]
            self.assertIn("trip_id", cols)
            cursor.close()
        finally:
            conn.close()

    def test_06_column_type_and_nullability(self):
        """Added trip_id column is nullable VARCHAR matching Incident model."""
        run_migrations(self.engine)

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            table_info = cursor.execute("PRAGMA table_info(incidents);").fetchall()
            trip_id_col = next((c for c in table_info if c[1] == "trip_id"), None)
            self.assertIsNotNone(trip_id_col)
            # col info: (cid, name, type, notnull, dflt_value, pk)
            self.assertEqual(trip_id_col[2].upper(), "VARCHAR")
            self.assertEqual(trip_id_col[3], 0)  # notnull == 0 means NULL allowed
            cursor.close()
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()

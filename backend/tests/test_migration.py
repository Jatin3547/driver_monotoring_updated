"""Unit and integration tests for FLEETGUARD database schema migrations.

Tests:
1. Migration adds missing `incidents.trip_id` column to an older database schema.
2. Existing incident records and data are fully preserved during migration.
3. Migration is idempotent (running it multiple times produces no error).
4. Startup queries against the Incident model succeed after migration without OperationalError.
"""

import os
import sqlite3
import tempfile
import unittest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db.migrations import run_migrations
from app.models import Incident
from app.db.session import Base


class TestSchemaMigration(unittest.TestCase):
    def setUp(self):
        # Create a temporary SQLite database file representing an older schema
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        self.engine = create_engine(f"sqlite:///{self.db_path}")

        # Construct legacy schema explicitly missing incidents.trip_id
        with sqlite3.connect(self.db_path) as conn:
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
            # Insert pre-existing incident record
            cursor.execute(
                """
                INSERT INTO incidents (id, driver_id, vehicle_id, type, severity, status, location, description, timestamp)
                VALUES ('INC-EXISTING-001', 'DRV-001', 'VEH-001', 'drowsiness', 'high', 'open', 'ORR Highway', 'Legacy incident before migration', '2026-10-23 10:00:00')
                """
            )
            conn.commit()

    def tearDown(self):
        self.engine.dispose()
        os.close(self.db_fd)
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_01_migration_adds_missing_trip_id_column(self):
        """Migration detects missing trip_id column and adds it to the incidents table."""
        # Check column is missing before migration
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cols_before = [c[1] for c in cursor.execute("PRAGMA table_info(incidents);").fetchall()]
            self.assertNotIn("trip_id", cols_before)

        # Execute migration
        run_migrations(self.engine)

        # Check column exists after migration
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cols_after = [c[1] for c in cursor.execute("PRAGMA table_info(incidents);").fetchall()]
            self.assertIn("trip_id", cols_after)

    def test_02_migration_preserves_existing_incident_records(self):
        """Migration preserves existing incident records without data loss."""
        run_migrations(self.engine)

        # Query using SQLAlchemy session
        Session = sessionmaker(bind=self.engine)
        session = Session()

        incidents = session.query(Incident).all()
        self.assertEqual(len(incidents), 1)
        inc = incidents[0]
        self.assertEqual(inc.id, "INC-EXISTING-001")
        self.assertEqual(inc.driver_id, "DRV-001")
        self.assertEqual(inc.description, "Legacy incident before migration")
        self.assertIsNone(inc.trip_id)  # Nullable trip_id for pre-existing records
        session.close()

    def test_03_migration_is_idempotent(self):
        """Running migration multiple times on the same database is safe and produces no error."""
        run_migrations(self.engine)
        run_migrations(self.engine)  # Second execution

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cols = [c[1] for c in cursor.execute("PRAGMA table_info(incidents);").fetchall()]
            self.assertEqual(cols.count("trip_id"), 1)

    def test_04_query_incident_model_succeeds_after_migration(self):
        """Queries against Incident model succeed without OperationalError."""
        run_migrations(self.engine)

        Session = sessionmaker(bind=self.engine)
        session = Session()
        try:
            # Filtering by trip_id succeeds without OperationalError (no such column)
            results = session.query(Incident).filter(Incident.trip_id == None).all()
            self.assertEqual(len(results), 1)
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()

"""Unit and integration tests for the safety escalation engine and cooldown deduplication.

Verifies:
1. Always persists SafetyEvent row for audit history.
2. Escalates high-severity events to Incident + Alert.
3. Suppresses duplicate incidents within the 30-second cooldown window.
4. Correctly creates new incidents after the cooldown period elapses.
5. Preserves medium-severity events without creating duplicate incidents.
"""

import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.ai.base import DetectionResult
from app.db.session import Base
from app.models import Alert, Driver, Fleet, Incident, SafetyEvent, Vehicle
from app.services.safety_engine import process_detection


class TestSafetyEngine(unittest.TestCase):
    def setUp(self):
        # In-memory SQLite for isolated, fast, clean tests
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        # Seed minimal fleet entities
        fleet = Fleet(name="Test Fleet", description="Test")
        self.db.add(fleet)
        self.db.flush()

        self.vehicle = Vehicle(
            code="VEH-TEST", plate_number="KA-01-9999", make="Tata", model="Ace",
            year=2022, type="truck", status="active", odometer_km=10000,
            fuel_level=80, next_service_due_km=20000, fleet_id=fleet.id
        )
        self.db.add(self.vehicle)
        self.db.flush()

        self.driver = Driver(
            code="DRV-TEST", name="Test Driver", license_number="LIC-1234",
            phone="+919999999999", email="test@fleet.com", status="on-trip",
            safety_score=90, joined_date=datetime.now(timezone.utc).date(),
            total_trips=10, total_distance_km=500, incident_count=0,
            assigned_vehicle_id=self.vehicle.id
        )
        self.db.add(self.driver)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_persists_safety_event_always(self):
        """Every detection produces a persisted SafetyEvent row."""
        detection = DetectionResult(
            event_type="eye_closure", severity="medium", confidence=0.75, source="live"
        )
        res = process_detection(self.db, self.driver, self.vehicle, detection)

        self.assertIsNotNone(res["event"])
        self.assertEqual(res["event"].event_type, "eye_closure")
        self.assertEqual(res["event"].severity, "medium")
        self.assertIsNone(res["incident"])  # Medium severity does not escalate
        self.assertIsNone(res["alert"])

        events = self.db.query(SafetyEvent).all()
        self.assertEqual(len(events), 1)

    def test_high_severity_escalates_to_incident_and_alert(self):
        """High severity detections escalate to Incident and Alert and bump incident count."""
        detection = DetectionResult(
            event_type="drowsiness", severity="high", confidence=0.92, source="live"
        )
        res = process_detection(self.db, self.driver, self.vehicle, detection)

        self.assertIsNotNone(res["event"])
        self.assertIsNotNone(res["incident"])
        self.assertIsNotNone(res["alert"])

        self.assertEqual(res["incident"].type, "drowsiness")
        self.assertEqual(res["incident"].status, "open")
        self.assertEqual(res["alert"].type, "drowsiness")
        self.assertEqual(self.driver.incident_count, 1)

    def test_cooldown_prevents_duplicate_incidents(self):
        """Repeated high-severity detections within 30s window do NOT create new incidents."""
        detection = DetectionResult(
            event_type="drowsiness", severity="high", confidence=0.92, source="live"
        )

        # First detection: creates incident
        res1 = process_detection(self.db, self.driver, self.vehicle, detection)
        self.assertIsNotNone(res1["incident"])
        self.assertEqual(self.driver.incident_count, 1)

        # Second detection 5 seconds later: creates SafetyEvent but suppresses Incident + Alert
        res2 = process_detection(self.db, self.driver, self.vehicle, detection)
        self.assertIsNotNone(res2["event"])
        self.assertIsNone(res2["incident"])
        self.assertIsNone(res2["alert"])
        self.assertEqual(self.driver.incident_count, 1)  # Stays 1, not 2

        # 2 events logged, but only 1 incident
        self.assertEqual(self.db.query(SafetyEvent).count(), 2)
        self.assertEqual(self.db.query(Incident).count(), 1)
        self.assertEqual(self.db.query(Alert).count(), 1)

    def test_incident_created_after_cooldown_expires(self):
        """Once 30s cooldown expires, a new high-severity detection creates a new incident."""
        detection = DetectionResult(
            event_type="drowsiness", severity="high", confidence=0.92, source="live"
        )

        # First incident
        res1 = process_detection(self.db, self.driver, self.vehicle, detection)
        incident_1 = res1["incident"]

        # Manually age the first incident by 35 seconds to simulate wall-clock passage
        incident_1.timestamp = datetime.now(timezone.utc) - timedelta(seconds=35)
        self.db.commit()

        # Second detection after cooldown: should create a second incident
        res2 = process_detection(self.db, self.driver, self.vehicle, detection)
        self.assertIsNotNone(res2["incident"])
        self.assertIsNotNone(res2["alert"])
        self.assertEqual(self.driver.incident_count, 2)
        self.assertEqual(self.db.query(Incident).count(), 2)


if __name__ == "__main__":
    unittest.main()

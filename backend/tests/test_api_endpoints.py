"""Integration tests for FastAPI REST endpoints using TestClient."""

import unittest
from fastapi.testclient import TestClient

from app.main import app


class TestApiIntegration(unittest.TestCase):
    def setUp(self):
        from app.db.init_db import init_db
        init_db()
        self.client = TestClient(app)

    def test_health_check(self):
        """GET /api/health returns healthy status."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "healthy")

    def test_monitoring_status_endpoint(self):
        """GET /api/monitoring/status returns list of driver statuses with metrics."""
        response = self.client.get("/api/monitoring/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        if len(data) > 0:
            first = data[0]
            self.assertIn("driverId", first)
            self.assertIn("metrics", first)
            self.assertIn("source", first)

    def test_monitoring_ai_status_endpoint(self):
        """GET /api/monitoring/ai-status returns honest diagnostic reporting."""
        response = self.client.get("/api/monitoring/ai-status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("configuredMode", data)
        self.assertIn("activeSource", data)
        self.assertIn("visionDependenciesInstalled", data)

    def test_auth_login_demo_credentials(self):
        """POST /api/auth/login succeeds with demo credentials."""
        response = self.client.post(
            "/api/auth/login",
            data={"username": "admin@fleetguard.demo", "password": "admin123"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertEqual(data.get("token_type"), "bearer")


    def test_incident_crud_and_delete(self):
        """Test listing, creating, and deleting incidents with evidence cleanup."""
        # 1. Create an incident
        res = self.client.post(
            "/api/incidents",
            json={
                "driverId": "DRV-001",
                "vehicleId": "VEH-001",
                "type": "drowsiness",
                "severity": "high",
                "location": "Test Location",
                "description": "Test incident description",
            },
        )
        self.assertEqual(res.status_code, 201)
        inc = res.json()
        inc_id = inc["id"]
        self.assertEqual(inc["type"], "drowsiness")

        # 2. Verify it shows in list
        list_res = self.client.get("/api/incidents?limit=10")
        self.assertEqual(list_res.status_code, 200)
        items = list_res.json()
        self.assertTrue(any(i["id"] == inc_id for i in items))

        # 3. Delete the incident
        del_res = self.client.delete(f"/api/incidents/{inc_id}")
        self.assertEqual(del_res.status_code, 200)
        del_data = del_res.json()
        self.assertTrue(del_data.get("ok"))
        self.assertEqual(del_data.get("id"), inc_id)

        # 4. Verify 404 on deleting non-existent incident
        del_again = self.client.delete(f"/api/incidents/{inc_id}")
        self.assertEqual(del_again.status_code, 404)


    def test_incident_delete_with_evidence_files(self):
        """Deleting an incident physically purges MP4 and snapshot files from storage."""
        from pathlib import Path
        from app.db.session import SessionLocal
        from app.models import Driver, Incident, Evidence, Vehicle
        from app.services.storage import get_storage_provider

        db = SessionLocal()
        try:
            driver = db.query(Driver).first()
            vehicle = db.query(Vehicle).first()
            self.assertIsNotNone(driver)
            self.assertIsNotNone(vehicle)
            prev_count = driver.incident_count

            # Create incident
            inc = Incident(
                driver_id=driver.id,
                vehicle_id=vehicle.id,
                type="distraction",
                severity="high",
                status="open",
                description="Test distraction incident",
            )
            db.add(inc)
            driver.incident_count += 1
            db.flush()

            # Create dummy evidence files
            storage = get_storage_provider()
            v_path = storage.base_dir / f"{inc.id}_test.mp4"
            s_path = storage.base_dir / f"{inc.id}_test.jpg"
            v_path.write_bytes(b"fake-mp4-data")
            s_path.write_bytes(b"fake-jpg-data")

            ev = Evidence(
                incident_id=inc.id,
                driver_id=driver.id,
                vehicle_id=vehicle.id,
                file_path=str(v_path),
                snapshot_path=str(s_path),
                file_size_bytes=13,
                duration_seconds=15.0,
            )
            db.add(ev)
            db.commit()
            inc_id = inc.id
            driver_id = driver.id
        finally:
            db.close()

        self.assertTrue(v_path.exists())
        self.assertTrue(s_path.exists())

        # DELETE incident via API
        del_res = self.client.delete(f"/api/incidents/{inc_id}")
        self.assertEqual(del_res.status_code, 200)

        # Verify physical files removed
        self.assertFalse(v_path.exists())
        self.assertFalse(s_path.exists())

        # Verify DB records deleted and driver counter decremented
        db2 = SessionLocal()
        try:
            self.assertIsNone(db2.query(Incident).filter(Incident.id == inc_id).first())
            self.assertIsNone(db2.query(Evidence).filter(Evidence.incident_id == inc_id).first())
            d_after = db2.query(Driver).filter(Driver.id == driver_id).first()
            self.assertEqual(d_after.incident_count, prev_count)
        finally:
            db2.close()


if __name__ == "__main__":
    unittest.main()

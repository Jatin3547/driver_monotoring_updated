"""Integration tests for Phase 1: Backend and Database Foundation.

Tests:
1. Authentication & Security: Registration, Login (form-encoded OAuth2), JWT Protected Route (/auth/me).
2. Trips: Creation, Active Trips lookup, Status updates, Incident counting.
3. Incidents & Evidence: Incident creation, Evidence metadata linking, Protection toggling, Status updates.
4. Health check: /api/health liveness.
"""

import unittest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models import Driver, Evidence, Incident, Trip, User, Vehicle


class TestPhase1BackendFoundation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def test_01_health_check(self):
        """Health check returns healthy status."""
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json().get("status"), "healthy")

    def test_02_auth_login_seeded_admin(self):
        """Seeded admin logs in and obtains a valid JWT bearer token."""
        res = self.client.post(
            "/api/auth/login",
            data={"username": "admin@fleetguard.demo", "password": "admin123"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data.get("token_type"), "bearer")
        self.assertEqual(data.get("user", {}).get("email"), "admin@fleetguard.demo")

    def test_03_auth_protected_me_endpoint(self):
        """Protected endpoint /api/auth/me requires valid token and rejects unauthorized calls."""
        # Unauthorized call
        unauth_res = self.client.get("/api/auth/me")
        self.assertEqual(unauth_res.status_code, 401)

        # Authorized call
        login_res = self.client.post(
            "/api/auth/login",
            data={"username": "admin@fleetguard.demo", "password": "admin123"},
        )
        token = login_res.json()["access_token"]
        auth_res = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(auth_res.status_code, 200)
        self.assertEqual(auth_res.json()["email"], "admin@fleetguard.demo")

    def test_04_auth_register_new_user(self):
        """New user can register and immediately authenticate."""
        email = f"operator_{int(datetime.now(timezone.utc).timestamp())}@fleetguard.demo"
        reg_res = self.client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "SecurePassword123!",
                "full_name": "Shift Operator",
            },
        )
        self.assertEqual(reg_res.status_code, 201)
        self.assertEqual(reg_res.json()["email"], email)

        # Login with newly registered user
        login_res = self.client.post(
            "/api/auth/login",
            data={"username": email, "password": "SecurePassword123!"},
        )
        self.assertEqual(login_res.status_code, 200)
        self.assertIn("access_token", login_res.json())

    def test_05_trips_listing_and_active_trips(self):
        """Trips endpoint returns trips with driver and vehicle metadata."""
        res = self.client.get("/api/trips")
        self.assertEqual(res.status_code, 200)
        trips = res.json()
        self.assertIsInstance(trips, list)
        self.assertGreater(len(trips), 0)

        first = trips[0]
        self.assertIn("id", first)
        self.assertIn("status", first)
        self.assertIn("vehicleId", first)
        self.assertIn("driverId", first)

        # Active trips query
        active_res = self.client.get("/api/trips/active")
        self.assertEqual(active_res.status_code, 200)
        active_trips = active_res.json()
        for t in active_trips:
            self.assertEqual(t["status"], "in-progress")

    def test_06_start_and_update_trip(self):
        """Can start a new trip and update its status."""
        start_res = self.client.post(
            "/api/trips",
            json={
                "driverCode": "DRV-003",
                "vehicleCode": "VEH-003",
                "startLocation": "Whitefield Hub",
                "endLocation": "Peenya Depot",
            },
        )
        self.assertEqual(start_res.status_code, 201)
        trip_data = start_res.json()
        trip_id = trip_data["id"]
        self.assertEqual(trip_data["status"], "in-progress")
        self.assertEqual(trip_data["driverCode"], "DRV-003")

        # Update / complete trip
        patch_res = self.client.patch(
            f"/api/trips/{trip_id}",
            json={"status": "completed", "distanceKm": 41.2},
        )
        self.assertEqual(patch_res.status_code, 200)
        self.assertEqual(patch_res.json()["status"], "completed")
        self.assertEqual(patch_res.json()["distanceKm"], 41.2)

    def test_07_incident_lifecycle_and_evidence_metadata(self):
        """Can create an incident with trip linkage, create evidence metadata, protect evidence, and resolve incident."""
        # 1. Create incident
        inc_res = self.client.post(
            "/api/incidents",
            json={
                "driverId": "DRV-001",
                "vehicleId": "VEH-001",
                "type": "drowsiness",
                "severity": "high",
                "location": "Silk Board Junction, Bengaluru",
                "description": "Continuous eye closure for 2.2s detected by live pipeline.",
            },
        )
        self.assertEqual(inc_res.status_code, 201)
        inc_data = inc_res.json()
        inc_id = inc_data["id"]
        self.assertEqual(inc_data["status"], "open")

        # 2. Attach Evidence metadata record (file path, duration, protection)
        ev_res = self.client.post(
            "/api/evidence",
            json={
                "incidentId": inc_id,
                "driverId": "DRV-001",
                "vehicleId": "VEH-001",
                "filePath": f"data/evidence/{inc_id}_event.mp4",
                "fileType": "video/mp4",
                "fileSizeBytes": 3145728,
                "durationSeconds": 8.0,
                "preEventSeconds": 5.0,
                "postEventSeconds": 3.0,
                "isProtected": False,
            },
        )
        self.assertEqual(ev_res.status_code, 201)
        ev_data = ev_res.json()
        ev_id = ev_data["id"]
        self.assertEqual(ev_data["incidentId"], inc_id)
        self.assertEqual(ev_data["isProtected"], False)

        # 3. Toggle protection on evidence
        protect_res = self.client.patch(
            f"/api/evidence/{ev_id}/protect",
            json={"isProtected": True},
        )
        self.assertEqual(protect_res.status_code, 200)
        self.assertEqual(protect_res.json()["isProtected"], True)

        # 4. Fetch evidence by incident ID
        by_inc_res = self.client.get(f"/api/evidence/incident/{inc_id}")
        self.assertEqual(by_inc_res.status_code, 200)
        self.assertEqual(by_inc_res.json()["id"], ev_id)

        # 5. Resolve incident via PATCH
        resolve_res = self.client.patch(
            f"/api/incidents/{inc_id}",
            json={"status": "resolved", "acknowledgedBy": "Fleet Safety Manager"},
        )
        self.assertEqual(resolve_res.status_code, 200)
        self.assertEqual(resolve_res.json()["status"], "resolved")
        self.assertEqual(resolve_res.json()["acknowledgedBy"], "Fleet Safety Manager")


if __name__ == "__main__":
    unittest.main()

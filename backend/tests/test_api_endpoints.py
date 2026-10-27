"""Integration tests for FastAPI REST endpoints using TestClient."""

import unittest
from fastapi.testclient import TestClient

from app.main import app


def _get_admin_token(client: TestClient) -> str:
    """Helper: obtain a JWT for the seeded fleet_admin account."""
    resp = client.post(
        "/api/auth/login",
        data={"username": "admin@fleetguard.demo", "password": "admin123"},
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    return resp.json()["access_token"]


def _get_driver_token(client: TestClient) -> str:
    """Helper: obtain a JWT for a seeded driver account (DRV-001)."""
    from app.db.session import SessionLocal
    from app.models import Driver
    from app.services.driver_accounts import driver_bootstrap_password

    db = SessionLocal()
    try:
        driver = db.query(Driver).filter(Driver.code == "DRV-001").first()
        email = driver.email
        password = driver_bootstrap_password(email)
    finally:
        db.close()

    resp = client.post(
        "/api/auth/login",
        data={"username": email, "password": password},
    )
    assert resp.status_code == 200, f"Driver login failed: {resp.text}"
    return resp.json()["access_token"]


class TestApiIntegration(unittest.TestCase):
    def setUp(self):
        from app.db.init_db import init_db
        init_db()
        self.client = TestClient(app)
        self.admin_token = _get_admin_token(self.client)
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}

    def test_health_check(self):
        """GET /api/health returns healthy status."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "healthy")

    def test_monitoring_status_endpoint(self):
        """GET /api/monitoring/status returns list of driver statuses with metrics."""
        response = self.client.get("/api/monitoring/status", headers=self.admin_headers)
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
        response = self.client.get("/api/monitoring/ai-status", headers=self.admin_headers)
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
        # Returned user should have fleet_admin role
        self.assertEqual(data["user"]["role"], "fleet_admin")

    def test_auth_login_with_manager_scope(self):
        """POST /api/auth/login with scope=manager succeeds for fleet_admin and fails for driver."""
        # Manager account succeeds
        resp_ok = self.client.post(
            "/api/auth/login",
            data={"username": "admin@fleetguard.demo", "password": "admin123", "scope": "manager"},
        )
        self.assertEqual(resp_ok.status_code, 200)

        # Driver account with manager scope should fail
        from app.db.session import SessionLocal
        from app.models import Driver
        from app.services.driver_accounts import driver_bootstrap_password

        db = SessionLocal()
        try:
            driver = db.query(Driver).filter(Driver.code == "DRV-001").first()
            email = driver.email
            password = driver_bootstrap_password(email)
        finally:
            db.close()

        resp_fail = self.client.post(
            "/api/auth/login",
            data={"username": email, "password": password, "scope": "manager"},
        )
        self.assertEqual(resp_fail.status_code, 403)

    def test_auth_login_driver_portal(self):
        """Driver-role user can log in with scope=driver and obtains a user with role=driver."""
        from app.db.session import SessionLocal
        from app.models import Driver
        from app.services.driver_accounts import driver_bootstrap_password

        db = SessionLocal()
        try:
            driver = db.query(Driver).filter(Driver.code == "DRV-001").first()
            self.assertIsNotNone(driver, "DRV-001 not found")
            self.assertIsNotNone(driver.user_id, "DRV-001 has no linked user account")
            email = driver.email
            password = driver_bootstrap_password(email)
        finally:
            db.close()

        resp = self.client.post(
            "/api/auth/login",
            data={"username": email, "password": password, "scope": "driver"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertEqual(data["user"]["role"], "driver")
        self.assertEqual(data["user"]["driver_code"], "DRV-001")

    def test_existing_driver_accounts_are_linked_once(self):
        """Every existing driver has one distinct driver-role account in the database."""
        from app.db.session import SessionLocal
        from app.models import Driver, User

        db = SessionLocal()
        try:
            drivers = db.query(Driver).order_by(Driver.code).all()
            self.assertTrue(drivers)
            linked_ids = [driver.user_id for driver in drivers]
            self.assertTrue(all(linked_ids), "At least one driver has no linked user account")
            self.assertEqual(len(linked_ids), len(set(linked_ids)), "A user account is linked to multiple drivers")
            for user_id in linked_ids:
                user = db.query(User).filter(User.id == user_id).first()
                self.assertIsNotNone(user)
                self.assertEqual(user.role, "driver")
        finally:
            db.close()

    def test_driver_cannot_access_manager_only_endpoints(self):
        """Driver-role token is rejected by fleet-manager-only endpoints."""
        driver_token = _get_driver_token(self.client)
        driver_headers = {"Authorization": f"Bearer {driver_token}"}

        # /api/drivers list — manager only
        resp = self.client.get("/api/drivers", headers=driver_headers)
        self.assertEqual(resp.status_code, 403)

        # /api/trips list — manager only
        resp2 = self.client.get("/api/trips", headers=driver_headers)
        self.assertEqual(resp2.status_code, 403)

        # /api/incidents list — manager only
        resp3 = self.client.get("/api/incidents", headers=driver_headers)
        self.assertEqual(resp3.status_code, 403)

        for path in (
            "/api/vehicles",
            "/api/gps/vehicles",
            "/api/monitoring/ai-status",
            "/api/monitoring/thresholds",
            "/api/analytics/driver-leaderboard",
            "/api/fleet/summary",
            "/api/evidence/storage-stats",
        ):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path, headers=driver_headers).status_code, 403)

    def test_driver_can_access_own_profile(self):
        """Driver-role token can access /auth/me and /auth/me/driver-profile."""
        driver_token = _get_driver_token(self.client)
        driver_headers = {"Authorization": f"Bearer {driver_token}"}

        resp_me = self.client.get("/api/auth/me", headers=driver_headers)
        self.assertEqual(resp_me.status_code, 200)
        self.assertEqual(resp_me.json()["role"], "driver")

        resp_profile = self.client.get("/api/auth/me/driver-profile", headers=driver_headers)
        self.assertEqual(resp_profile.status_code, 200)
        profile = resp_profile.json()
        self.assertEqual(profile["id"], "DRV-001")

    def test_driver_dashboard_data_endpoints_are_scoped(self):
        """All real dashboard calls succeed and return the authenticated driver's data."""
        driver_token = _get_driver_token(self.client)
        driver_headers = {"Authorization": f"Bearer {driver_token}"}

        profile = self.client.get("/api/auth/me/driver-profile", headers=driver_headers).json()
        self.assertEqual(profile["id"], "DRV-001")
        self.assertEqual(profile["email"], "arjun.mehta@fleetmail.com")
        self.assertIn("safetyScore", profile)

        vehicle = self.client.get("/api/vehicles/assigned", headers=driver_headers)
        self.assertEqual(vehicle.status_code, 200, vehicle.text)
        self.assertEqual(vehicle.json()["id"], "VEH-001")

        trips = self.client.get("/api/trips/my-trips", headers=driver_headers)
        self.assertEqual(trips.status_code, 200, trips.text)
        self.assertTrue(all(trip["driverId"] == "DRV-001" for trip in trips.json()))

        incidents = self.client.get("/api/incidents/mine", headers=driver_headers)
        self.assertEqual(incidents.status_code, 200, incidents.text)
        self.assertTrue(all(item["driverId"] == "DRV-001" for item in incidents.json()))

        gps = self.client.get("/api/gps/my-vehicle", headers=driver_headers)
        self.assertEqual(gps.status_code, 200, gps.text)
        self.assertEqual(gps.json()["vehicleId"], "VEH-001")
        self.assertIn("lat", gps.json())

    def test_driver_can_access_own_trips(self):
        """Driver-role user can list their own trips via /trips/my-trips."""
        driver_token = _get_driver_token(self.client)
        driver_headers = {"Authorization": f"Bearer {driver_token}"}

        resp = self.client.get("/api/trips/my-trips", headers=driver_headers)
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.json(), list)

    def test_driver_cannot_access_another_drivers_record(self):
        """Driver-role user can access their own driver record but not another's."""
        driver_token = _get_driver_token(self.client)
        driver_headers = {"Authorization": f"Bearer {driver_token}"}

        # Own record
        own = self.client.get("/api/drivers/DRV-001", headers=driver_headers)
        self.assertEqual(own.status_code, 200)

        # Another driver's record — should be forbidden
        other = self.client.get("/api/drivers/DRV-002", headers=driver_headers)
        self.assertEqual(other.status_code, 403)

    def test_evidence_is_manager_only(self):
        """Evidence metadata and stored footage cannot be accessed anonymously or by drivers."""
        driver_token = _get_driver_token(self.client)
        driver_headers = {"Authorization": f"Bearer {driver_token}"}
        self.assertEqual(self.client.get("/api/evidence/storage-stats").status_code, 401)
        self.assertEqual(self.client.get("/api/evidence/storage-stats", headers=driver_headers).status_code, 403)

    def test_register_cannot_self_assign_manager_role(self):
        """Registration endpoint always sets role to 'registered', ignoring any injected role field."""
        import random, string
        rand = "".join(random.choices(string.ascii_lowercase, k=8))
        resp = self.client.post(
            "/api/auth/register",
            json={
                "email": f"{rand}@test.example",
                "password": "TestPass123!",
                "full_name": "Test User",
            },
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["role"], "registered")

    def test_incident_crud_and_delete(self):
        """Test listing, creating, and deleting incidents with evidence cleanup (manager auth)."""
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
            headers=self.admin_headers,
        )
        self.assertEqual(res.status_code, 201)
        inc = res.json()
        inc_id = inc["id"]
        self.assertEqual(inc["type"], "drowsiness")

        # 2. Verify it shows in list
        list_res = self.client.get("/api/incidents?limit=10", headers=self.admin_headers)
        self.assertEqual(list_res.status_code, 200)
        items = list_res.json()
        self.assertTrue(any(i["id"] == inc_id for i in items))

        # 3. Delete the incident
        del_res = self.client.delete(f"/api/incidents/{inc_id}", headers=self.admin_headers)
        self.assertEqual(del_res.status_code, 200)
        del_data = del_res.json()
        self.assertTrue(del_data.get("ok"))
        self.assertEqual(del_data.get("id"), inc_id)

        # 4. Verify 404 on deleting non-existent incident
        del_again = self.client.delete(f"/api/incidents/{inc_id}", headers=self.admin_headers)
        self.assertEqual(del_again.status_code, 404)

    def test_incident_delete_with_evidence_files(self):
        """Deleting an incident physically purges MP4 and snapshot files from storage."""
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

        # DELETE incident via API with manager auth
        del_res = self.client.delete(f"/api/incidents/{inc_id}", headers=self.admin_headers)
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

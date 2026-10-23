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


if __name__ == "__main__":
    unittest.main()

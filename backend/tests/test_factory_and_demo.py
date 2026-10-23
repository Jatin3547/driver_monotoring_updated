"""Unit tests for AI factory, demo fallback, and structured monitoring status."""

import unittest
from app.ai.factory import ai_status, get_detector, get_driver_status, shutdown_detector
from app.ai.simulator import SimulatedDetector


from unittest.mock import patch
from app.core.config import settings


class TestAIFactoryAndDemo(unittest.TestCase):
    def tearDown(self):
        shutdown_detector()

    def test_default_simulation_mode(self):
        """In demo mode, returns SimulatedDetector with honest simulation source."""
        with patch.object(settings, "ai_mode", "demo"):
            shutdown_detector()
            detector = get_detector()
            self.assertIsInstance(detector, SimulatedDetector)

            status = ai_status()
            self.assertEqual(status["activeSource"], "simulation")

    def test_structured_driver_status_contract(self):
        """get_driver_status returns structured dictionary matching frontend contract."""
        status = get_driver_status("DRV-001", "VEH-001")

        required_keys = {
            "driverId", "vehicleId", "isOnline", "presenceDetected",
            "eyeState", "drowsinessLevel", "yawnStatus", "phoneUseStatus",
            "distractionStatus", "lastUpdated", "source", "metrics",
            "cameraStatus", "aiHealth",
        }
        self.assertTrue(required_keys.issubset(status.keys()))
        self.assertEqual(status["driverId"], "DRV-001")
        self.assertEqual(status["vehicleId"], "VEH-001")
        self.assertIn("ear", status["metrics"])
        self.assertIn("mar", status["metrics"])
        self.assertIn("headYaw", status["metrics"])


if __name__ == "__main__":
    unittest.main()

"""Unit tests for CameraManager lifecycle, error handling, diagnostics, and clean shutdown."""

import unittest
from app.ai.camera import CameraManager


class TestCameraManagerLifecycle(unittest.TestCase):
    def setUp(self):
        self.camera = CameraManager(camera_index=99, target_fps=15, max_reconnect_retries=2)

    def tearDown(self):
        self.camera.stop(timeout=1.0)

    def test_initial_state(self):
        """Camera starts in stopped state."""
        self.assertEqual(self.camera.status, "stopped")
        self.assertFalse(self.camera.is_connected)

        ok, frame, ts = self.camera.get_latest_frame()
        self.assertFalse(ok)
        self.assertIsNone(frame)

    def test_diagnostics_structure(self):
        """Diagnostics dictionary exposes expected telemetry keys."""
        diag = self.camera.diagnostics
        expected_keys = {
            "cameraIndex", "status", "isConnected", "fpsTarget",
            "fpsActual", "frameWidth", "frameHeight", "frameCount",
            "lastError", "reconnectAttempts"
        }
        self.assertTrue(expected_keys.issubset(diag.keys()))
        self.assertEqual(diag["cameraIndex"], 99)
        self.assertEqual(diag["fpsTarget"], 15)

    def test_clean_shutdown_when_stopped(self):
        """Calling stop() on an unstarted or stopped camera is safe and idempotent."""
        self.camera.stop()
        self.assertEqual(self.camera.status, "stopped")
        self.assertFalse(self.camera.is_connected)


if __name__ == "__main__":
    unittest.main()

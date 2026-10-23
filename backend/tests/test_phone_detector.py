"""Unit tests for PhoneDetector and spatial driver interaction heuristics."""

import unittest
from unittest.mock import MagicMock, patch
import numpy as np

from app.ai.phone_detector import PhoneDetection, PhoneDetector


class TestPhoneDetectorUnit(unittest.TestCase):
    def setUp(self):
        # Create detector without actually loading heavy weights during mock tests
        with patch.object(PhoneDetector, "_initialize_model", return_value=True):
            self.detector = PhoneDetector(model_name="yolov8n.pt", conf_threshold=0.35)
            self.detector.available = True

    def tearDown(self):
        self.detector.shutdown()

    def test_phone_detection_dataclass_defaults(self):
        detection = PhoneDetection()
        self.assertFalse(detection.detected)
        self.assertEqual(detection.confidence, 0.0)
        self.assertIsNone(detection.bbox)
        self.assertFalse(detection.in_driver_zone)
        self.assertIsNone(detection.error)

    def test_spatial_heuristic_inside_ear_zone(self):
        """Phone placed near the driver's right ear/cheek is classified inside driver zone."""
        frame_shape = (480, 640)
        face_bbox = (200, 100, 360, 280)  # w=160, h=180
        # Phone held to the right ear
        phone_bbox = (330, 120, 390, 240)
        in_zone = self.detector.is_in_driver_zone(phone_bbox, face_bbox, frame_shape)
        self.assertTrue(in_zone)

    def test_spatial_heuristic_inside_lap_hand_zone(self):
        """Phone placed below face near upper chest/hands is inside driver zone."""
        frame_shape = (480, 640)
        face_bbox = (200, 100, 360, 280)  # w=160, h=180
        # Phone held in front of chest/steering wheel
        phone_bbox = (230, 300, 310, 420)
        in_zone = self.detector.is_in_driver_zone(phone_bbox, face_bbox, frame_shape)
        self.assertTrue(in_zone)

    def test_spatial_heuristic_outside_zone_passenger(self):
        """Phone held on far passenger side is classified OUTSIDE driver zone."""
        frame_shape = (480, 640)
        face_bbox = (150, 100, 270, 260)  # Driver sitting on left
        # Phone at x=550 (far passenger side)
        phone_bbox = (540, 150, 600, 270)
        in_zone = self.detector.is_in_driver_zone(phone_bbox, face_bbox, frame_shape)
        self.assertFalse(in_zone)

    def test_spatial_heuristic_fallback_no_face(self):
        """When face landmarks momentarily dropout, central viewing zone heuristic applies."""
        frame_shape = (480, 640)
        # Center phone
        center_phone = (280, 200, 360, 320)
        self.assertTrue(self.detector.is_in_driver_zone(center_phone, None, frame_shape))

        # Edge phone (e.g. window or far side)
        edge_phone = (5, 5, 45, 80)
        self.assertFalse(self.detector.is_in_driver_zone(edge_phone, None, frame_shape))

    def test_diagnostics_structure(self):
        diag = self.detector.get_diagnostics()
        self.assertIn("available", diag)
        self.assertIn("model", diag)
        self.assertIn("confidenceThreshold", diag)
        self.assertIn("avgInferenceMs", diag)
        self.assertEqual(diag["model"], "yolov8n.pt")

    def test_unavailable_detector_honest_reporting(self):
        """When model fails to load, detector reports available=False and explicit error."""
        detector = PhoneDetector(model_name="non_existent_weights_xyz.pt")
        # Should cleanly mark unavailable without unhandled exception
        self.assertFalse(detector.available)
        self.assertIsNotNone(detector.last_error)

        det = detector.detect_non_blocking(np.zeros((100, 100, 3), dtype=np.uint8))
        self.assertFalse(det.detected)
        self.assertIsNotNone(det.error)
        detector.shutdown()


if __name__ == "__main__":
    unittest.main()

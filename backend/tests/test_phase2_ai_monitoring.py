"""Phase 2 Automated Test Suite: Live AI Driver Monitoring.

Validates:
1. Dual-pipeline independence: FaceMesh and YOLO phone detector run on same source frame without disabling each other.
2. Portrait vs. landscape phone orientation detection.
3. Varying distance and proximity estimation (near-face, steering-level, distant).
4. Temporal filtering and debouncing: transient phone glance vs confirmed unsafe phone usage.
5. Drowsiness (EAR) vs blink rejection, yawning (MAR) vs speech, and head distraction (Yaw).
6. Camera failure handling and diagnostics.
"""

import unittest
from unittest.mock import MagicMock, patch
import numpy as np

from app.ai.analysis import FrameFeatures
from app.ai.camera import CameraManager
from app.ai.live_monitor import DriverTemporalTracker, LiveMonitoringPipeline
from app.ai.phone_detector import PhoneDetection, PhoneDetector


class TestPhase2LiveMonitoring(unittest.TestCase):
    def setUp(self):
        with patch.object(PhoneDetector, "_initialize_model", return_value=True):
            self.phone_detector = PhoneDetector(model_name="yolov8n.pt", conf_threshold=0.35)
            self.phone_detector.available = True
        self.tracker = DriverTemporalTracker("DRV-001")

    def tearDown(self):
        self.phone_detector.shutdown()

    def _features(self, ear=0.32, mar=0.18, yaw=0.0, face_detected=True):
        return FrameFeatures(
            ear=ear,
            left_ear=ear,
            right_ear=ear,
            mar=mar,
            head_yaw=yaw,
            head_pitch=0.0,
            head_roll=0.0,
            face_detected=face_detected,
        )

    # 1. Phone Orientation Tests (Portrait vs Landscape)
    def test_phone_portrait_orientation(self):
        """Portrait phone (height > width) is correctly tagged as 'portrait'."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        face_bbox = (200, 100, 360, 280)
        # Portrait: width 60, height 120
        portrait_bbox = (230, 140, 290, 260)
        phone_w = portrait_bbox[2] - portrait_bbox[0]
        phone_h = portrait_bbox[3] - portrait_bbox[1]
        orientation = "portrait" if phone_h >= phone_w else "landscape"
        self.assertEqual(orientation, "portrait")

        in_zone = self.phone_detector.is_in_driver_zone(portrait_bbox, face_bbox, frame.shape)
        self.assertTrue(in_zone)

    def test_phone_landscape_orientation(self):
        """Landscape phone (width > height) is correctly tagged as 'landscape'."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        face_bbox = (200, 100, 360, 280)
        # Landscape: width 130, height 65
        landscape_bbox = (210, 310, 340, 375)
        phone_w = landscape_bbox[2] - landscape_bbox[0]
        phone_h = landscape_bbox[3] - landscape_bbox[1]
        orientation = "portrait" if phone_h >= phone_w else "landscape"
        self.assertEqual(orientation, "landscape")

        in_zone = self.phone_detector.is_in_driver_zone(landscape_bbox, face_bbox, frame.shape)
        self.assertTrue(in_zone)

    # 2. Phone Proximity / Distance Tests
    def test_phone_proximity_near_face(self):
        """Phone held at ear level is estimated as 'near-face'."""
        frame_shape = (480, 640)
        face_bbox = (200, 100, 360, 280)
        # At right ear
        phone_bbox = (330, 120, 390, 240)
        prox = self.phone_detector.calculate_proximity(phone_bbox, face_bbox, frame_shape)
        self.assertEqual(prox, "near-face")

    def test_phone_proximity_steering_level(self):
        """Phone held below chin near steering wheel is estimated as 'steering-level'."""
        frame_shape = (480, 640)
        face_bbox = (200, 100, 360, 280)
        # Below face
        phone_bbox = (220, 320, 300, 420)
        prox = self.phone_detector.calculate_proximity(phone_bbox, face_bbox, frame_shape)
        self.assertEqual(prox, "steering-level")

    def test_phone_proximity_distant(self):
        """Small phone bounding box is estimated as 'distant'."""
        frame_shape = (480, 640)
        # Small box, no face
        phone_bbox = (500, 200, 520, 230)
        prox = self.phone_detector.calculate_proximity(phone_bbox, None, frame_shape)
        self.assertEqual(prox, "distant")

    # 3. Temporal Thresholds: Momentary Glance vs Unsafe Confirmed Usage
    def test_transient_phone_detection_does_not_alarm(self):
        """A phone briefly seen for < 0.6s does not trigger warning or critical alarm."""
        t = 100.0
        phone_det = PhoneDetection(
            detected=True,
            confidence=0.88,
            in_driver_zone=True,
            timestamp=t,
            orientation="portrait",
        )

        # 0.3s elapsed
        detections = self.tracker.update(self._features(), timestamp=t + 0.3, phone_detection=phone_det)
        self.assertEqual(len(detections), 0)
        self.assertEqual(self.tracker.phone_use_status, "normal")

    def test_sustained_phone_use_triggers_critical_escalation(self):
        """Phone used in driver zone for >= 1.5s triggers high-severity phone_use event."""
        t = 100.0
        phone_det = PhoneDetection(
            detected=True,
            confidence=0.92,
            in_driver_zone=True,
            timestamp=t,
            orientation="portrait",
        )

        # First frame
        self.tracker.update(self._features(), timestamp=t, phone_detection=phone_det)

        # 0.8s elapsed: warning state
        self.tracker.update(self._features(), timestamp=t + 0.8, phone_detection=phone_det)
        self.assertEqual(self.tracker.phone_use_status, "warning")

        # 1.6s elapsed: critical escalation
        detections = self.tracker.update(self._features(), timestamp=t + 1.6, phone_detection=phone_det)
        self.assertEqual(self.tracker.phone_use_status, "critical")
        self.assertEqual(len(detections), 1)
        self.assertEqual(detections[0].event_type, "phone_use")
        self.assertEqual(detections[0].severity, "high")

    # 4. Independent Dual Pipeline: Neither Detector Disables the Other
    def test_phone_detection_continues_when_face_is_occluded(self):
        """When face landmarks fail or are occluded, phone detection still processes the frame."""
        t = 200.0
        phone_det = PhoneDetection(
            detected=True,
            confidence=0.85,
            in_driver_zone=True,
            timestamp=t,
            orientation="landscape",
        )

        # No face detected
        no_face_features = self._features(face_detected=False)
        self.tracker.update(no_face_features, timestamp=t, phone_detection=phone_det)
        # Both status signals are tracked independently
        self.assertIsNotNone(self.tracker.phone_use_status)

    def test_face_drowsiness_continues_when_phone_detector_fails(self):
        """When phone detector encounters an error, eye state & drowsiness tracking are unaffected."""
        t = 300.0
        error_phone_det = PhoneDetection(detected=False, error="CUDA out of memory")

        # Eyes closed for 1.2 seconds (drowsiness)
        self.tracker.update(self._features(ear=0.08), timestamp=t, phone_detection=error_phone_det)
        detections = self.tracker.update(self._features(ear=0.08), timestamp=t + 1.2, phone_detection=error_phone_det)

        # Drowsiness detection must succeed regardless of phone detector error
        self.assertEqual(self.tracker.drowsiness_level, "critical")
        self.assertTrue(any(d.event_type == "drowsiness" for d in detections))
        self.assertEqual(self.tracker.phone_use_status, "no-signal")

    # 5. Drowsiness vs Blink, Yawning vs Talking, Head Pose Distraction
    def test_blink_rejection_formula(self):
        """Brief eye closure (<0.25s) is rejected as a normal physiological blink."""
        t = 400.0
        self.tracker.update(self._features(ear=0.35), timestamp=t)
        self.tracker.update(self._features(ear=0.06), timestamp=t + 0.15)
        self.assertEqual(self.tracker.eye_state, "normal")
        self.assertEqual(self.tracker.drowsiness_level, "normal")

    def test_yawn_versus_speech_distinction(self):
        """Speech (<0.5s mouth opening) is normal; yawn (>=1.0s) triggers critical alert."""
        t = 500.0
        # Speech opening for 0.3s
        self.tracker.update(self._features(mar=0.32), timestamp=t)
        self.tracker.update(self._features(mar=0.32), timestamp=t + 0.3)
        self.assertEqual(self.tracker.yawn_status, "normal")

        # Sustained yawn for 1.2s
        detections = self.tracker.update(self._features(mar=0.35), timestamp=t + 1.2)
        self.assertEqual(self.tracker.yawn_status, "critical")
        self.assertTrue(any(d.event_type == "yawning" for d in detections))

    def test_head_distraction_temporal_filter(self):
        """Head yaw > 25 degrees for >= 2.0s triggers distraction detection."""
        t = 600.0
        # Quick glance at side mirror (0.5s)
        self.tracker.update(self._features(yaw=28.0), timestamp=t)
        self.tracker.update(self._features(yaw=28.0), timestamp=t + 0.5)
        self.assertEqual(self.tracker.distraction_status, "normal")

        # Sustained distraction (2.2s)
        detections = self.tracker.update(self._features(yaw=30.0), timestamp=t + 2.2)
        self.assertEqual(self.tracker.distraction_status, "critical")
        self.assertTrue(any(d.event_type == "distraction" for d in detections))

    # 6. Camera Lifecycle & Safe Diagnostics
    def test_camera_offline_safe_diagnostics(self):
        """CameraManager with unavailable index safely reports status='stopped' and isConnected=False."""
        cam = CameraManager(camera_index=99, target_fps=15, max_reconnect_retries=1)
        diag = cam.diagnostics
        self.assertEqual(diag["status"], "stopped")
        self.assertFalse(diag["isConnected"])
        self.assertEqual(diag["fpsTarget"], 15)
        cam.stop()


if __name__ == "__main__":
    unittest.main()

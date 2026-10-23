"""Unit tests for DriverTemporalTracker and temporal debouncing logic.

Verifies:
1. Normal eye blinking vs eye closure warning vs critical drowsiness.
2. Normal speech vs sustained yawning.
3. Quick glance vs sustained distraction.
4. Temporary face loss vs sustained absence grace period and recovery.
"""

import unittest
from app.ai.analysis import FrameFeatures
from app.ai.live_monitor import DriverTemporalTracker, LiveMonitoringPipeline
from app.ai.phone_detector import PhoneDetection


class TestLiveMonitorTemporalLogic(unittest.TestCase):
    def setUp(self):
        self.tracker = DriverTemporalTracker("DRV-001")

    def _features(self, ear=0.35, mar=0.20, yaw=0.0, face_detected=True):
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

    def test_normal_alert_free_driving(self):
        """Standard driving produces no detections and normal statuses."""
        t = 1000.0
        detections = self.tracker.update(self._features(ear=0.35, mar=0.20, yaw=0.0), timestamp=t)
        self.assertEqual(len(detections), 0)
        self.assertEqual(self.tracker.eye_state, "normal")
        self.assertEqual(self.tracker.drowsiness_level, "normal")
        self.assertEqual(self.tracker.yawn_status, "normal")
        self.assertEqual(self.tracker.distraction_status, "normal")
        self.assertTrue(self.tracker.presence_detected)

    def test_blink_rejection(self):
        """A normal blink (< 0.4s) does not trigger warnings or drowsiness."""
        t = 1000.0
        # Normal driving
        self.tracker.update(self._features(ear=0.35), timestamp=t)

        # Eye closes during blink (0.2 seconds elapsed)
        detections = self.tracker.update(self._features(ear=0.06), timestamp=t + 0.20)
        self.assertEqual(len(detections), 0)
        self.assertEqual(self.tracker.eye_state, "normal")

        # Eye re-opens at 0.35s
        detections = self.tracker.update(self._features(ear=0.35), timestamp=t + 0.35)
        self.assertEqual(len(detections), 0)
        self.assertEqual(self.tracker.eye_state, "normal")

    def test_eye_closure_warning_and_critical_drowsiness(self):
        """Eyes closed for >= 0.6s triggers warning; >= 1.0s triggers high-severity drowsiness."""
        t = 1000.0
        self.tracker.update(self._features(ear=0.35), timestamp=t)

        # Eye closes at t + 0.1
        self.tracker.update(self._features(ear=0.06), timestamp=t + 0.1)

        # After 0.7s of closure (t + 0.8): warning triggered (warning >= 0.6s)
        detections = self.tracker.update(self._features(ear=0.06), timestamp=t + 0.8)
        warning_events = [d for d in detections if d.event_type == "eye_closure"]
        self.assertEqual(len(warning_events), 1)
        self.assertEqual(warning_events[0].severity, "medium")
        self.assertEqual(self.tracker.drowsiness_level, "warning")

        # After 1.1s of closure (t + 1.2): critical drowsiness triggered (>= 1.0s)
        detections = self.tracker.update(self._features(ear=0.06), timestamp=t + 1.2)
        drowsy_events = [d for d in detections if d.event_type == "drowsiness"]
        self.assertEqual(len(drowsy_events), 1)
        self.assertEqual(drowsy_events[0].severity, "high")
        self.assertEqual(self.tracker.drowsiness_level, "critical")

        # Eye re-opens: returns to normal
        self.tracker.update(self._features(ear=0.35), timestamp=t + 2.5)
        self.assertEqual(self.tracker.drowsiness_level, "normal")
        self.assertEqual(self.tracker.eye_state, "normal")

    def test_talking_vs_yawning(self):
        """Speech movements (< 0.5s) are ignored; sustained mouth opening (>= 1.0s) triggers yawn."""
        t = 1000.0
        # Speech: mouth opens for 0.3s
        self.tracker.update(self._features(mar=0.10), timestamp=t)
        self.tracker.update(self._features(mar=0.40), timestamp=t + 0.15)
        detections = self.tracker.update(self._features(mar=0.40), timestamp=t + 0.3)
        self.assertEqual(len(detections), 0)
        self.assertEqual(self.tracker.yawn_status, "normal")

        # Mouth closes back
        self.tracker.update(self._features(mar=0.10), timestamp=t + 0.5)

        # Real yawn starts at t + 1.0
        self.tracker.update(self._features(mar=0.45), timestamp=t + 1.0)
        # 0.6s in -> warning (>= 0.5s)
        self.tracker.update(self._features(mar=0.45), timestamp=t + 1.6)
        self.assertEqual(self.tracker.yawn_status, "warning")

        # 1.1s in -> yawning detection (>= 1.0s)
        detections = self.tracker.update(self._features(mar=0.45), timestamp=t + 2.1)
        yawns = [d for d in detections if d.event_type == "yawning"]
        self.assertEqual(len(yawns), 1)
        self.assertEqual(yawns[0].severity, "high")
        self.assertEqual(self.tracker.yawn_status, "critical")

    def test_glance_vs_distraction(self):
        """Looking at side mirror (< 1.0s) is ignored; sustained head turn (>= 2.0s) triggers distraction."""
        t = 1000.0
        self.tracker.update(self._features(yaw=0.0), timestamp=t)

        # Quick mirror glance (0.5s at 30 deg)
        self.tracker.update(self._features(yaw=30.0), timestamp=t + 0.2)
        detections = self.tracker.update(self._features(yaw=30.0), timestamp=t + 0.5)
        self.assertEqual(len(detections), 0)
        self.assertEqual(self.tracker.distraction_status, "normal")

        # Back to road
        self.tracker.update(self._features(yaw=0.0), timestamp=t + 0.7)

        # Sustained turn (starts at t + 1.0)
        self.tracker.update(self._features(yaw=-35.0), timestamp=t + 1.0)
        # 2.2s of looking left (at t + 3.2)
        detections = self.tracker.update(self._features(yaw=-35.0), timestamp=t + 3.2)
        distractions = [d for d in detections if d.event_type == "distraction"]
        self.assertEqual(len(distractions), 1)
        self.assertEqual(distractions[0].severity, "medium")
        self.assertEqual(self.tracker.distraction_status, "critical")

    def test_absence_grace_period_and_recovery(self):
        """Brief face loss (< 2.5s grace period) does not report absence; sustained loss reports high severity."""
        t = 1000.0
        # Driver present
        self.tracker.update(self._features(face_detected=True), timestamp=t)
        self.assertTrue(self.tracker.presence_detected)

        # Face temporarily occluded / turned for 1.5s
        detections = self.tracker.update(None, timestamp=t + 1.5)
        self.assertEqual(len(detections), 0)
        self.assertTrue(self.tracker.presence_detected)  # Grace period protects it

        # Face remains missing for 3.0s total (> 2.5s grace period)
        detections = self.tracker.update(None, timestamp=t + 3.0)
        absence = [d for d in detections if d.event_type == "no_presence"]
        self.assertEqual(len(absence), 1)
        self.assertEqual(absence[0].severity, "high")
        self.assertFalse(self.tracker.presence_detected)

        # Driver returns
        self.tracker.update(self._features(face_detected=True), timestamp=t + 4.0)
        self.assertTrue(self.tracker.presence_detected)

    def test_phone_use_temporal_progression(self):
        """Transient phone detection (< 0.6s) is normal; 0.6-1.5s warning; >= 1.5s triggers critical phone_use."""
        t = 1000.0
        phone_active = PhoneDetection(
            detected=True,
            confidence=0.88,
            bbox=(300, 150, 360, 250),
            in_driver_zone=True,
            timestamp=t,
        )

        # Initial frame with phone present
        detections = self.tracker.update(self._features(), timestamp=t, phone_detection=phone_active)
        self.assertEqual(len(detections), 0)
        self.assertEqual(self.tracker.phone_use_status, "normal")

        # 0.7s of sustained phone use (>= 0.6s warning threshold)
        detections = self.tracker.update(self._features(), timestamp=t + 0.7, phone_detection=phone_active)
        self.assertEqual(len(detections), 0)
        self.assertEqual(self.tracker.phone_use_status, "warning")

        # 1.6s of sustained phone use (>= 1.5s critical threshold)
        detections = self.tracker.update(self._features(), timestamp=t + 1.6, phone_detection=phone_active)
        phone_events = [d for d in detections if d.event_type == "phone_use"]
        self.assertEqual(len(phone_events), 1)
        self.assertEqual(phone_events[0].severity, "high")
        self.assertEqual(self.tracker.phone_use_status, "critical")

        # Phone put away (no phone detected) -> after 1.0s grace period resets to normal
        self.tracker.update(
            self._features(),
            timestamp=t + 3.0,
            phone_detection=PhoneDetection(detected=False, timestamp=t + 3.0),
        )
        self.assertEqual(self.tracker.phone_use_status, "normal")

    def test_phone_outside_driver_zone_ignored(self):
        """Phone detected in passenger area or away from driver hand/ear does not trigger driver distraction."""
        t = 1000.0
        passenger_phone = PhoneDetection(
            detected=True,
            confidence=0.90,
            bbox=(550, 100, 620, 220),
            in_driver_zone=False,
            timestamp=t,
        )
        # Even after 3 seconds of passenger phone visible, driver phoneUseStatus remains normal
        self.tracker.update(self._features(), timestamp=t, phone_detection=passenger_phone)
        detections = self.tracker.update(self._features(), timestamp=t + 3.0, phone_detection=passenger_phone)
        self.assertEqual(len(detections), 0)
        self.assertEqual(self.tracker.phone_use_status, "normal")

    def test_phone_detector_unavailable(self):
        """When phone detector is disabled or unavailable, status reports 'no-signal' with zero false alarms."""
        t = 1000.0
        # No detector passed
        self.tracker.update(self._features(), timestamp=t, phone_detection=None)
        self.assertEqual(self.tracker.phone_use_status, "no-signal")

        # Errored detector
        errored_phone = PhoneDetection(detected=False, error="YOLO failed to load")
        detections = self.tracker.update(self._features(), timestamp=t + 1.0, phone_detection=errored_phone)
        self.assertEqual(len(detections), 0)
        self.assertEqual(self.tracker.phone_use_status, "no-signal")


class TestLiveMonitoringPipelineMultiDriver(unittest.TestCase):
    def test_pipeline_isolates_different_drivers(self):
        """Pipeline maintains independent temporal states for DRV-001 and DRV-002."""
        pipeline = LiveMonitoringPipeline()
        t = 1000.0

        features_drowsy = FrameFeatures(
            ear=0.06, left_ear=0.06, right_ear=0.06, mar=0.20,
            head_yaw=0.0, head_pitch=0.0, head_roll=0.0, face_detected=True
        )
        features_awake = FrameFeatures(
            ear=0.35, left_ear=0.35, right_ear=0.35, mar=0.20,
            head_yaw=0.0, head_pitch=0.0, head_roll=0.0, face_detected=True
        )

        # DRV-001 has eyes closed for 2.2 seconds
        pipeline.process_frame_features("DRV-001", features_drowsy, t)
        det_1, status_1 = pipeline.process_frame_features("DRV-001", features_drowsy, t + 2.2)

        # DRV-002 has eyes wide open
        det_2, status_2 = pipeline.process_frame_features("DRV-002", features_awake, t + 2.2)

        self.assertEqual(status_1["drowsinessLevel"], "critical")
        self.assertEqual(status_2["drowsinessLevel"], "normal")
        self.assertFalse(status_2["presenceDetected"] is False)


if __name__ == "__main__":
    unittest.main()

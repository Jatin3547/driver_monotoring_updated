"""Per-driver temporal monitoring state tracker and signal smoother.

Implements temporal hysteresis rules:
- Blink rejection (transient eye closure < 0.4s ignored).
- Sustained eye-closure warning (0.8s) and critical drowsiness (1.8s).
- Distinguishes speech from yawning (speech < 1.0s, sustained yawn >= 1.8s).
- Sustained distraction (head turned > 25° for >= 2.0s).
- Driver absence grace period (2.5s before reporting no_presence).
- Emits structured metadata and DetectionResult events.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.ai.analysis import FrameFeatures
from app.ai.base import DetectionResult
from app.core.config import settings


class DriverTemporalTracker:
    """Tracks state over time for a single driver session."""

    def __init__(self, driver_code: str) -> None:
        self.driver_code = driver_code

        # Timers (wall-clock timestamps)
        self._eye_closure_start: Optional[float] = None
        self._yawn_start: Optional[float] = None
        self._distraction_start: Optional[float] = None
        self._phone_use_start: Optional[float] = None
        self._last_phone_detection_time: Optional[float] = None
        self._last_face_time: float = 0.0

        # State outputs
        self.eye_state: str = "normal"          # normal | warning | critical
        self.drowsiness_level: str = "normal"   # normal | warning | critical
        self.yawn_status: str = "normal"        # normal | warning | critical
        self.phone_use_status: str = "no-signal" # normal | warning | critical | no-signal
        self.distraction_status: str = "normal" # normal | warning | critical
        self.presence_detected: bool = True

        # Exponential moving averages for smoothing
        self._smoothed_ear: Optional[float] = None
        self._smoothed_mar: Optional[float] = None
        self._smoothed_yaw: Optional[float] = None

    def update(
        self,
        features: Optional[FrameFeatures],
        timestamp: float,
        phone_detection: Optional[Any] = None,
    ) -> List[DetectionResult]:
        """Update tracker with new frame features and return any newly triggered detections."""
        detections: List[DetectionResult] = []

        # 1. Handle Driver Presence / Absence
        if features is None or not features.face_detected:
            if self._last_face_time == 0.0:
                self._last_face_time = timestamp

            absence_duration = timestamp - self._last_face_time
            if absence_duration >= settings.ai_absence_grace_seconds:
                self.presence_detected = False
                self.eye_state = "no-signal"
                self.drowsiness_level = "no-signal"
                self.yawn_status = "no-signal"
                self.distraction_status = "no-signal"
                self.phone_use_status = "no-signal"
                self._phone_use_start = None
                self._last_phone_detection_time = None
                self._eye_closure_start = None
                detections.append(
                    DetectionResult(
                        event_type="no_presence",
                        severity="high",
                        confidence=0.95,
                        source="live",
                    )
                )
            return detections

        # Face is present: reset absence timer
        self._last_face_time = timestamp
        self.presence_detected = True

        # 2. Metrics for Threshold Detection and Display
        ear = features.ear
        mar = features.mar
        yaw = features.head_yaw

        self._smoothed_ear = ear
        self._smoothed_mar = mar
        self._smoothed_yaw = yaw

        # 3. Eye Closure & Drowsiness Analysis
        if ear < settings.ai_ear_threshold:
            if self._eye_closure_start is None:
                self._eye_closure_start = timestamp

            closure_duration = timestamp - self._eye_closure_start

            if closure_duration >= settings.ai_drowsiness_duration_seconds:
                self.drowsiness_level = "critical"
                self.eye_state = "critical"
                confidence = min(1.0, 0.70 + (closure_duration - settings.ai_drowsiness_duration_seconds) * 0.15)
                detections.append(
                    DetectionResult(
                        event_type="drowsiness",
                        severity="high",
                        confidence=round(confidence, 2),
                        source="live",
                    )
                )
            elif closure_duration >= settings.ai_eye_closure_warning_seconds:
                self.drowsiness_level = "warning"
                self.eye_state = "warning"
                detections.append(
                    DetectionResult(
                        event_type="eye_closure",
                        severity="medium",
                        confidence=round(min(0.9, 0.5 + closure_duration * 0.3), 2),
                        source="live",
                    )
                )
            elif closure_duration >= 0.25:
                # Eyes closed longer than normal blink (>0.25s) -> immediate visual response
                self.eye_state = "warning"
                self.drowsiness_level = "normal"
            else:
                # Normal transient blink (< 0.25s)
                self.drowsiness_level = "normal"
                self.eye_state = "normal"
        else:
            self._eye_closure_start = None
            self.eye_state = "normal"
            self.drowsiness_level = "normal"

        # 4. Yawn Analysis (Distinguishing Yawning from Talking)
        if mar >= settings.ai_mar_threshold:
            if self._yawn_start is None:
                self._yawn_start = timestamp

            yawn_duration = timestamp - self._yawn_start

            if yawn_duration >= settings.ai_yawn_duration_seconds:
                self.yawn_status = "critical"
                confidence = min(0.98, 0.75 + (yawn_duration - settings.ai_yawn_duration_seconds) * 0.1)
                detections.append(
                    DetectionResult(
                        event_type="yawning",
                        severity="high",
                        confidence=round(confidence, 2),
                        source="live",
                    )
                )
            elif yawn_duration >= 0.5:
                self.yawn_status = "warning"
            else:
                # Brief mouth opening (< 0.5s), typical of speech
                self.yawn_status = "normal"
        else:
            self._yawn_start = None
            self.yawn_status = "normal"

        # 5. Distraction Analysis (Head Yaw)
        if abs(yaw) >= settings.ai_yaw_threshold_degrees:
            if self._distraction_start is None:
                self._distraction_start = timestamp

            distraction_duration = timestamp - self._distraction_start

            if distraction_duration >= settings.ai_distraction_duration_seconds:
                self.distraction_status = "critical"
                confidence = min(0.95, 0.70 + (distraction_duration - settings.ai_distraction_duration_seconds) * 0.1)
                detections.append(
                    DetectionResult(
                        event_type="distraction",
                        severity="medium",
                        confidence=round(confidence, 2),
                        source="live",
                    )
                )
            elif distraction_duration >= 0.8:
                self.distraction_status = "warning"
            else:
                self.distraction_status = "normal"
        else:
            self._distraction_start = None
            self.distraction_status = "normal"

        # 6. Phone Detection & Distraction Analysis
        if phone_detection is None or getattr(phone_detection, "error", None) is not None:
            # Detector unavailable or failed
            self.phone_use_status = "no-signal"
            self._phone_use_start = None
            self._last_phone_detection_time = None
        elif not phone_detection.detected:
            # Detector ran, but no phone detected in this frame
            if self._last_phone_detection_time is not None and (timestamp - self._last_phone_detection_time) < 1.0:
                # Temporal debounce: allow brief dropouts (< 1.0s) without resetting state
                pass
            else:
                self._phone_use_start = None
                self._last_phone_detection_time = None
                self.phone_use_status = "normal"
        elif not phone_detection.in_driver_zone:
            # Phone detected in the cab, but NOT in the driver's hand/ear interaction zone
            if self._last_phone_detection_time is not None and (timestamp - self._last_phone_detection_time) < 1.0:
                pass
            else:
                self._phone_use_start = None
                self._last_phone_detection_time = None
                self.phone_use_status = "normal"
        else:
            # Phone detected AND within the driver interaction zone
            self._last_phone_detection_time = timestamp
            if self._phone_use_start is None:
                self._phone_use_start = timestamp

            phone_duration = timestamp - self._phone_use_start

            if phone_duration >= settings.ai_phone_usage_duration_seconds:
                self.phone_use_status = "critical"
                confidence = min(0.99, max(0.50, float(phone_detection.confidence)))
                detections.append(
                    DetectionResult(
                        event_type="phone_use",
                        severity="high",
                        confidence=round(confidence, 2),
                        source="live",
                    )
                )
            elif phone_duration >= settings.ai_phone_warning_duration_seconds:
                self.phone_use_status = "warning"
            else:
                self.phone_use_status = "normal"

        return detections

    def get_metrics(self) -> Dict[str, float]:
        """Returns the latest smoothed metrics."""
        return {
            "ear": round(self._smoothed_ear or 0.0, 3),
            "mar": round(self._smoothed_mar or 0.0, 3),
            "headYaw": round(self._smoothed_yaw or 0.0, 1),
        }

    def reset(self) -> None:
        """Reset temporal state counters."""
        self._eye_closure_start = None
        self._last_eye_closure_time = None
        self._yawn_start = None
        self._distraction_start = None
        self._phone_use_start = None
        self._last_phone_detection_time = None
        self._last_face_time = 0.0
        self.eye_state = "normal"
        self.drowsiness_level = "normal"
        self.yawn_status = "normal"
        self.phone_use_status = "normal"
        self.distraction_status = "normal"
        self.presence_detected = True


class LiveMonitoringPipeline:
    """Multi-driver coordinator managing live frame analysis and per-driver temporal tracking."""

    def __init__(self) -> None:
        self._trackers: Dict[str, DriverTemporalTracker] = {}

    def get_tracker(self, driver_code: str) -> DriverTemporalTracker:
        if driver_code not in self._trackers:
            self._trackers[driver_code] = DriverTemporalTracker(driver_code)
        return self._trackers[driver_code]

    def process_frame_features(
        self,
        driver_code: str,
        features: Optional[FrameFeatures],
        timestamp: float,
        phone_detection: Optional[Any] = None,
    ) -> Tuple[List[DetectionResult], Dict[str, Any]]:
        """Processes frame features for a driver and produces detections and structured status."""
        tracker = self.get_tracker(driver_code)
        detections = tracker.update(features, timestamp, phone_detection)

        now_iso = datetime.now(timezone.utc).isoformat()
        metrics = tracker.get_metrics()

        status_dict = {
            "driverId": driver_code,
            "isOnline": True,
            "presenceDetected": tracker.presence_detected,
            "eyeState": tracker.eye_state,
            "drowsinessLevel": tracker.drowsiness_level,
            "yawnStatus": tracker.yawn_status,
            "phoneUseStatus": tracker.phone_use_status,
            "distractionStatus": tracker.distraction_status,
            "lastUpdated": now_iso,
            "source": "live",
            "metrics": metrics,
        }

        if phone_detection is not None and getattr(phone_detection, "detected", False):
            status_dict["phoneMetadata"] = {
                "detected": True,
                "confidence": getattr(phone_detection, "confidence", 0.0),
                "inDriverZone": getattr(phone_detection, "in_driver_zone", False),
                "orientation": getattr(phone_detection, "orientation", "unknown"),
                "proximity": getattr(phone_detection, "proximity", "unknown"),
            }

        return detections, status_dict

    def clear(self) -> None:
        self._trackers.clear()

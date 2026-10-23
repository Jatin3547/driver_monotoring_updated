"""AI monitoring SIMULATION — not real computer vision.

Generates deterministic, smoothly time-varying "detections" per driver so
the Live Monitoring dashboard has something meaningful to show without a
camera, OpenCV, MediaPipe, or YOLO installed. Every event this module
produces is stored with `source="simulation"`; nothing here is ever
reported as a real inference result.

For the real pipeline (camera -> OpenCV/MediaPipe/YOLO -> classification),
see app/ai/vision.py and README "AI Driver Monitoring" section.
"""

import hashlib
import math
from datetime import datetime, timezone

from app.ai.base import BaseDetector, DetectionResult

SIGNAL_TYPES = ["eyeState", "drowsinessLevel", "yawnStatus", "phoneUseStatus", "distractionStatus"]
EVENT_TYPE_BY_SIGNAL = {
    "eyeState": "eye_closure",
    "drowsinessLevel": "drowsiness",
    "yawnStatus": "yawning",
    "phoneUseStatus": "phone_use",
    "distractionStatus": "distraction",
}


def _seed(driver_code: str, salt: str = "") -> float:
    digest = hashlib.sha256(f"{driver_code}{salt}".encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF  # -> [0, 1)


def compute_signal_level(driver_code: str, signal: str, now: datetime | None = None) -> str:
    """Returns 'normal' | 'warning' | 'critical', varying smoothly over
    real time so the dashboard visibly changes on repeated polls."""
    now = now or datetime.now(timezone.utc)
    phase = _seed(driver_code, signal) * 2 * math.pi
    t = now.timestamp() / 45.0  # full cycle roughly every ~4.7 minutes
    value = (math.sin(t + phase) + 1) / 2  # -> [0, 1]

    if value > 0.88:
        return "critical"
    if value > 0.68:
        return "warning"
    return "normal"


def compute_driver_status(driver_code: str, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    presence_value = (math.sin(now.timestamp() / 300.0 + _seed(driver_code, "presence") * 6) + 1) / 2
    presence = presence_value > 0.08  # mostly present, rare simulated dropout

    status = {signal: compute_signal_level(driver_code, signal, now) for signal in SIGNAL_TYPES}
    status["isOnline"] = True
    status["presenceDetected"] = presence
    status["lastUpdated"] = now.isoformat()
    status["source"] = "simulation"
    return status


class SimulatedDetector(BaseDetector):
    """Implements the shared detector interface using the deterministic
    signal functions above, for interchangeability with a real detector."""

    def analyze_frame(self, driver_code: str) -> list[DetectionResult]:
        now = datetime.now(timezone.utc)
        results = []
        for signal, event_type in EVENT_TYPE_BY_SIGNAL.items():
            level = compute_signal_level(driver_code, signal, now)
            if level == "normal":
                continue
            severity = "high" if level == "critical" else "medium"
            confidence = round(0.6 + _seed(driver_code, signal + "conf") * 0.35, 2)
            results.append(
                DetectionResult(
                    event_type=event_type,
                    severity=severity,
                    confidence=confidence,
                    source="simulation",
                )
            )
        return results

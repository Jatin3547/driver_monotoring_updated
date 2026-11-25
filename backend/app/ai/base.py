"""Detector interface.

Both the simulation backend (app/ai/simulator.py) and the optional live
backend (app/ai/vision.py) implement this interface, so route code never
needs to know which one is active — it just reads `settings.ai_mode`.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DetectionResult:
    event_type: str  # drowsiness|eye_closure|yawning|phone_use|distraction|no_presence
    severity: str  # low|medium|high
    confidence: float | None  # calibrated detector confidence only (e.g. YOLO)
    source: str  # "simulation" | "live" — never fabricated/mislabeled
    duration_seconds: float | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


class BaseDetector(ABC):
    @abstractmethod
    def analyze_frame(self, driver_code: str) -> list[DetectionResult]:
        """Return zero or more detections for the current frame/tick."""
        raise NotImplementedError


class UnavailableDetector(BaseDetector):
    """Honest no-op used when LIVE mode is unavailable; it never fabricates demo detections."""

    def analyze_frame(self, driver_code: str) -> list[DetectionResult]:
        return []

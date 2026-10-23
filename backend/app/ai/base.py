"""Detector interface.

Both the simulation backend (app/ai/simulator.py) and the optional live
backend (app/ai/vision.py) implement this interface, so route code never
needs to know which one is active — it just reads `settings.ai_mode`.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class DetectionResult:
    event_type: str  # drowsiness|eye_closure|yawning|phone_use|distraction|no_presence
    severity: str  # low|medium|high
    confidence: float
    source: str  # "simulation" | "live" — never fabricated/mislabeled


class BaseDetector(ABC):
    @abstractmethod
    def analyze_frame(self, driver_code: str) -> list[DetectionResult]:
        """Return zero or more detections for the current frame/tick."""
        raise NotImplementedError

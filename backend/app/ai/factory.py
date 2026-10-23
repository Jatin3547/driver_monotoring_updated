"""Chooses simulation vs. live detector based on AI_MODE, with a safe
fallback: if AI_MODE=live but the optional CV deps aren't installed, we
fall back to simulation rather than crashing the whole API — and the
route response always reports which source actually served the data via
each event/status object's "source" field.
"""

from app.ai.base import BaseDetector
from app.ai.simulator import SimulatedDetector
from app.core.config import settings

_detector: BaseDetector | None = None
_active_source = "simulation"


def get_detector() -> BaseDetector:
    global _detector, _active_source
    if _detector is not None:
        return _detector

    if settings.ai_mode == "live":
        try:
            from app.ai.vision import LiveVisionDetector

            _detector = LiveVisionDetector(camera_index=settings.ai_camera_index)
            _active_source = "live"
            return _detector
        except Exception as exc:
            # Missing deps / no camera — fall back rather than crash the API.
            import logging

            logging.getLogger("fleet.ai").warning(
                "AI_MODE=live requested but live detector could not start (%s). "
                "Falling back to simulation.",
                exc,
            )

    _detector = SimulatedDetector()
    _active_source = "simulation"
    return _detector


def active_source() -> str:
    get_detector()
    return _active_source


def ai_status() -> dict:
    """Reports what's actually active, for the Settings page — never
    claims 'live' unless a live detector genuinely constructed successfully."""
    from app.ai.vision import VISION_DEPENDENCIES_AVAILABLE

    detector = get_detector()  # ensures _active_source reflects a real attempt
    diag = {}
    if _active_source == "live" and hasattr(detector, "get_diagnostics"):
        diag = detector.get_diagnostics()

    return {
        "configuredMode": settings.ai_mode,
        "activeSource": _active_source,
        "visionDependenciesInstalled": VISION_DEPENDENCIES_AVAILABLE,
        "cameraIndex": settings.ai_camera_index,
        "diagnostics": diag,
    }


PRIMARY_LIVE_DRIVER_CODE = "DRV-001"


def get_driver_status(driver_code: str, vehicle_code: str | None = None) -> dict:
    """Returns real structured monitoring metrics for primary live driver, or independent simulated status for others."""
    detector = get_detector()
    if _active_source == "live" and driver_code == PRIMARY_LIVE_DRIVER_CODE and hasattr(detector, "get_monitoring_status"):
        return detector.get_monitoring_status(driver_code, vehicle_code)

    from app.ai.simulator import compute_driver_status
    base_status = compute_driver_status(driver_code)
    return {
        **base_status,
        "driverId": driver_code,
        "vehicleId": vehicle_code or "",
        "cameraStatus": "simulated",
        "aiHealth": "healthy",
        "metrics": {"ear": 0.28, "mar": 0.20, "headYaw": 0.0},
    }


def get_video_frame():
    """Returns latest JPEG frame bytes if live camera is active, or None."""
    detector = get_detector()
    if _active_source == "live" and hasattr(detector, "get_latest_jpeg_frame"):
        return detector.get_latest_jpeg_frame()
    return None


def shutdown_detector() -> None:
    """Cleanly releases any hardware or worker threads."""
    global _detector, _active_source
    if _detector is not None and hasattr(_detector, "shutdown"):
        try:
            _detector.shutdown()
        except Exception:
            pass
    _detector = None
    _active_source = "simulation"


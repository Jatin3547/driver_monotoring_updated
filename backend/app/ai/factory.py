"""Choose simulation or live detection from AI_MODE.

If live initialization fails, the API remains available but monitoring is
reported as unavailable; simulation values are never presented as live.
"""

from app.ai.base import BaseDetector, UnavailableDetector
from app.ai.simulator import SimulatedDetector
from app.core.config import settings
import threading
from datetime import datetime, timezone

_detector: BaseDetector | None = None
_active_source = "simulation"
_initialization_error: str | None = None
_browser_detector = None
_browser_detector_lock = threading.Lock()


def get_detector() -> BaseDetector:
    global _detector, _active_source, _initialization_error
    if _detector is not None:
        return _detector

    mode = settings.ai_mode.strip().lower()
    if mode in {"simulation", "demo"}:
        _detector = SimulatedDetector()
        _active_source = "simulation"
        _initialization_error = None
        return _detector

    if mode == "live":
        try:
            from app.ai.vision import LiveVisionDetector

            _detector = LiveVisionDetector(camera_index=settings.ai_camera_index)
            _active_source = "live"
            _initialization_error = None
            return _detector
        except Exception as exc:
            # Keep the API available but mark live AI unavailable. Do not
            # silently pass deterministic simulation values as live monitoring.
            import logging

            logging.getLogger("fleet.ai").warning(
                "AI_MODE=live requested but live detector could not start (%s).",
                exc,
            )
            _detector = UnavailableDetector()
            _active_source = "unavailable"
            _initialization_error = str(exc)
            return _detector

    _detector = UnavailableDetector()
    _active_source = "unavailable"
    _initialization_error = f"Unsupported AI_MODE '{settings.ai_mode}'. Use 'live' or 'simulation'."
    return _detector


def active_source() -> str:
    detector = get_detector()
    try:
        from app.ai.browser_sessions import browser_sessions
        if any(session["status"] == "active" for session in browser_sessions.list_active()):
            return "browser_live"
    except Exception:
        pass
    if _active_source == "live":
        camera = getattr(detector, "camera", None)
        has_face_model = getattr(detector, "_face_mesh", None) is not None or getattr(detector, "_face_landmarker", None) is not None
        if camera is None or not camera.is_connected or not has_face_model:
            return "unavailable"
    return _active_source


def ai_status() -> dict:
    """Report configured mode separately from actual camera/model availability."""
    from app.ai.vision import MEDIAPIPE_AVAILABLE, OPENCV_AVAILABLE

    detector = get_detector()
    source = active_source()
    browser_camera_sessions = []
    try:
        from app.ai.browser_sessions import browser_sessions
        browser_camera_sessions = browser_sessions.list_active()
    except Exception:
        pass

    diagnostics = {}
    if source == "browser_live" and _browser_detector is not None:
        diagnostics = _browser_detector.get_diagnostics()
    elif _active_source == "live" and hasattr(detector, "get_diagnostics"):
        diagnostics = detector.get_diagnostics()
    camera_diag = diagnostics.get("camera", {})
    if source == "browser_live":
        current_state = browser_camera_sessions[0].get("signals")
        camera_available = True
        camera_status = "browser_active"
        error = None
    elif source == "live":
        current_state = detector.get_monitoring_status("DRV-001") if hasattr(detector, "get_monitoring_status") else None
        camera_available = bool(camera_diag.get("isConnected"))
        camera_status = camera_diag.get("status", "active")
        error = None
    elif source == "simulation":
        current_state = None
        camera_available = False
        camera_status = "not_required"
        error = None
    else:
        current_state = None
        camera_available = bool(camera_diag.get("isConnected"))
        camera_status = camera_diag.get("status", "unavailable")
        if _active_source == "live" and getattr(detector, "_face_mesh", None) is None and getattr(detector, "_face_landmarker", None) is None:
            error = "MediaPipe face landmark model is unavailable."
        else:
            error = _initialization_error or camera_diag.get("lastError") or "Live camera is unavailable."

    phone_diagnostics = diagnostics.get("phoneDetector", {})
    return {
        "configuredMode": settings.ai_mode,
        "activeSource": source,
        "visionDependenciesInstalled": OPENCV_AVAILABLE and MEDIAPIPE_AVAILABLE,
        "openCvAvailable": OPENCV_AVAILABLE,
        "mediaPipeAvailable": MEDIAPIPE_AVAILABLE,
        "phoneDetectorAvailable": bool(phone_diagnostics.get("available", False)),
        "cameraIndex": settings.ai_camera_index,
        "cameraAvailable": camera_available,
        "cameraStatus": camera_status,
        "monitoringState": "active" if source in {"live", "browser_live", "simulation"} else "unavailable",
        "currentDriverState": current_state,
        "error": error,
        "browserSessions": browser_camera_sessions,
        "diagnostics": diagnostics,
    }


PRIMARY_LIVE_DRIVER_CODE = "DRV-001"


def get_driver_status(driver_code: str, vehicle_code: str | None = None) -> dict:
    """Return browser-session, server-live, demo, or explicit unavailable status."""
    try:
        from app.ai.browser_sessions import browser_sessions
        browser_session = browser_sessions.get_for_driver_code(driver_code)
        if browser_session and browser_session.get("lastStatus"):
            return browser_session["lastStatus"]
    except Exception:
        pass

    detector = get_detector()
    source = active_source()
    if source == "live" and driver_code == PRIMARY_LIVE_DRIVER_CODE and hasattr(detector, "get_monitoring_status"):
        return detector.get_monitoring_status(driver_code, vehicle_code)

    if source == "simulation":
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

    camera = getattr(detector, "camera", None)
    camera_status = camera.status if camera is not None else "unavailable"
    return {
        "driverId": driver_code,
        "vehicleId": vehicle_code or "",
        "isOnline": False,
        "presenceDetected": False,
        "eyeState": "no-signal",
        "drowsinessLevel": "no-signal",
        "yawnStatus": "no-signal",
        "phoneUseStatus": "no-signal",
        "distractionStatus": "no-signal",
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
        "source": "none",
        "cameraStatus": camera_status,
        "aiHealth": "degraded",
        "error": _initialization_error or getattr(camera, "diagnostics", {}).get("lastError"),
    }


def get_video_frame():
    """Returns latest JPEG frame bytes if live camera is active, or None."""
    detector = get_detector()
    if active_source() == "live" and hasattr(detector, "get_latest_jpeg_frame"):
        return detector.get_latest_jpeg_frame()
    return None


def shutdown_detector() -> None:
    """Cleanly releases any hardware or worker threads."""
    global _detector, _browser_detector, _active_source, _initialization_error
    if _detector is not None and hasattr(_detector, "shutdown"):
        try:
            _detector.shutdown()
        except Exception:
            pass
    if _browser_detector is not None:
        try:
            _browser_detector.shutdown()
        except Exception:
            pass
    _detector = None
    _browser_detector = None
    _active_source = "simulation"
    _initialization_error = None


def pause_fleet_camera_for_browser_session() -> None:
    """Release the backend webcam so the local browser can open it exclusively."""
    camera = getattr(_detector, "camera", None)
    if camera is not None:
        camera.stop()


def resume_fleet_camera_after_browser_session() -> None:
    """Resume a previously initialized server camera after browser monitoring stops."""
    camera = getattr(_detector, "camera", None)
    if camera is not None and settings.ai_mode.strip().lower() == "live":
        camera.start()


def clear_browser_driver_state(driver_code: str) -> None:
    detector = _browser_detector
    if detector is not None:
        with detector._inference_lock:
            detector.pipeline._trackers.pop(driver_code, None)


def browser_detector_if_ready():
    return _browser_detector


def get_browser_detector():
    """Lazy, server-side vision models for authenticated browser camera sessions."""
    global _browser_detector
    with _browser_detector_lock:
        if _browser_detector is None:
            from app.ai.vision import LiveVisionDetector, VISION_DEPENDENCIES_AVAILABLE

            if not VISION_DEPENDENCIES_AVAILABLE:
                raise RuntimeError("Live vision dependencies are not installed; install backend/requirements-ai.txt")
            _browser_detector = LiveVisionDetector(use_camera=False)
            if _browser_detector._face_mesh is None and _browser_detector._face_landmarker is None:
                _browser_detector.shutdown()
                _browser_detector = None
                raise RuntimeError("Face landmark model could not be initialized")
        return _browser_detector


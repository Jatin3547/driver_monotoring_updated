"""Real computer-vision driver-monitoring pipeline.

Coordinates:
- Threaded non-blocking camera capture (app.ai.camera.CameraManager)
- MediaPipe FaceMesh feature extraction (app.ai.analysis)
- Per-driver temporal state tracking & debouncing (app.ai.live_monitor)

Design Principles:
- Non-blocking frame access to prevent starvation of the FastAPI asyncio loop.
- Low-CPU operation suitable for laptops (configurable target FPS, latest-frame dropping).
- Honest failure paths: Never fabricates confidence scores or simulates detections under live mode.
- Clean resource reclamation on shutdown.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from app.ai.analysis import (
    extract_face_bbox,
    extract_features_from_landmarks,
    select_driver_face,
)
from app.ai.base import BaseDetector, DetectionResult
from app.ai.camera import CameraManager
from app.ai.live_monitor import LiveMonitoringPipeline
from app.core.config import settings

logger = logging.getLogger("fleet.ai.vision")

try:
    import cv2
    import mediapipe as mp

    VISION_DEPENDENCIES_AVAILABLE = True
except ImportError:
    VISION_DEPENDENCIES_AVAILABLE = False


class LiveVisionDetector(BaseDetector):
    """MediaPipe FaceMesh + background threaded camera driver detector."""

    def __init__(self, camera_index: Optional[int] = None) -> None:
        if not VISION_DEPENDENCIES_AVAILABLE:
            raise RuntimeError(
                "Live AI mode requires opencv-python and mediapipe. "
                "Install them with: pip install -r requirements-ai.txt"
            )

        self.camera_index = camera_index if camera_index is not None else settings.ai_camera_index

        # 1. Background Camera Capture Worker
        self.camera = CameraManager(
            camera_index=self.camera_index,
            target_fps=settings.ai_target_fps,
            max_reconnect_retries=settings.ai_camera_reconnect_max_retries,
        )
        self.camera.start()

        # 2. MediaPipe FaceMesh (refine_landmarks=False for low-CPU usage on laptops)
        self._face_mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=2,
            refine_landmarks=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        # 3. Multi-Driver Temporal State Tracker
        self.pipeline = LiveMonitoringPipeline()
        self._last_process_time: float = 0.0
        self._cached_detections: List[DetectionResult] = []
        self._cached_status: Dict[str, Any] = {}

        # 4. Pretrained YOLO Phone Detector (asynchronous background inference)
        self.phone_detector = None
        if settings.ai_phone_detection_enabled:
            try:
                from app.ai.phone_detector import PhoneDetector
                self.phone_detector = PhoneDetector(
                    model_name=settings.ai_phone_model,
                    conf_threshold=settings.ai_phone_confidence_threshold,
                )
            except Exception as exc:
                logger.warning("Could not initialize PhoneDetector: %s", exc)
                self.phone_detector = None

    def _process_live_driver(self, vehicle_code: Optional[str] = None) -> Tuple[List[DetectionResult], Dict[str, Any]]:
        """Processes the latest camera frame for the live driver with temporal caching."""
        now = time.time()
        # If analyzed within the last 200ms, reuse the result to prevent CPU lockup
        if (now - self._last_process_time) < 0.20 and self._cached_status:
            status_copy = dict(self._cached_status)
            if vehicle_code:
                status_copy["vehicleId"] = vehicle_code
            return list(self._cached_detections), status_copy

        ok, frame, _ = self.camera.get_latest_frame()
        features = None
        face_bbox = None
        phone_detection = None

        if ok and frame is not None:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mesh_result = self._face_mesh.process(rgb_frame)
            if mesh_result.multi_face_landmarks:
                h, w = frame.shape[:2]
                primary_face = select_driver_face(mesh_result.multi_face_landmarks, w, h)
                if primary_face is not None:
                    features = extract_features_from_landmarks(primary_face.landmark, w, h)
                    face_bbox = extract_face_bbox(primary_face.landmark, w, h)

            if self.phone_detector is not None:
                phone_detection = self.phone_detector.detect_non_blocking(frame, face_bbox)

        detections, status_dict = self.pipeline.process_frame_features(
            "DRV-001", features, now, phone_detection
        )
        if vehicle_code:
            status_dict["vehicleId"] = vehicle_code

        camera_diag = self.camera.diagnostics
        status_dict["cameraStatus"] = camera_diag["status"]
        status_dict["aiHealth"] = "healthy" if camera_diag["isConnected"] else "degraded"

        self._last_process_time = now
        self._cached_detections = detections
        self._cached_status = status_dict
        return detections, status_dict

    def analyze_frame(self, driver_code: str) -> List[DetectionResult]:
        """Analyzes camera frame for the live driver and returns safety detections."""
        if driver_code != "DRV-001":
            return []
        detections, _ = self._process_live_driver()
        return detections

    def get_monitoring_status(self, driver_code: str, vehicle_code: Optional[str] = None) -> Dict[str, Any]:
        """Returns structured real-time monitoring status and metrics for the frontend."""
        if driver_code != "DRV-001":
            from app.ai.simulator import compute_driver_status
            base_status = compute_driver_status(driver_code)
            return {
                **base_status,
                "driverId": driver_code,
                "vehicleId": vehicle_code or "",
                "cameraStatus": "simulated",
                "aiHealth": "healthy",
            }
        _, status_dict = self._process_live_driver(vehicle_code)
        return status_dict

    def get_latest_jpeg_frame(self) -> Optional[bytes]:
        """Encodes the latest camera frame into JPEG bytes for dashboard streaming."""
        ok, frame, _ = self.camera.get_latest_frame()
        if not ok or frame is None:
            return None

        display_frame = frame.copy()
        h, w = display_frame.shape[:2]
        if w > 640:
            scale = 640.0 / w
            display_frame = cv2.resize(display_frame, (640, int(h * scale)))

        # Draw phone detection bounding box overlay if phone detected
        if self.phone_detector is not None:
            curr_phone = self.phone_detector.detect_non_blocking(None)
            if curr_phone.detected and curr_phone.bbox is not None:
                bx1, by1, bx2, by2 = curr_phone.bbox
                orig_h, orig_w = frame.shape[:2]
                disp_h, disp_w = display_frame.shape[:2]
                sx = disp_w / orig_w
                sy = disp_h / orig_h
                dx1, dy1 = int(bx1 * sx), int(by1 * sy)
                dx2, dy2 = int(bx2 * sx), int(by2 * sy)
                # Red if in driver zone, Amber/Yellow if elsewhere in cab
                color = (0, 0, 255) if curr_phone.in_driver_zone else (0, 215, 255)
                cv2.rectangle(display_frame, (dx1, dy1), (dx2, dy2), color, 2)
                label = f"PHONE {int(curr_phone.confidence * 100)}%"
                cv2.putText(display_frame, label, (dx1, max(18, dy1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        ret, buffer = cv2.imencode('.jpg', display_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 65])
        if not ret:
            return None
        return buffer.tobytes()

    def get_diagnostics(self) -> Dict[str, Any]:
        """Reports hardware and inference health."""
        camera_diag = self.camera.diagnostics
        phone_diag = self.phone_detector.get_diagnostics() if self.phone_detector else {"available": False}
        return {
            "source": "live",
            "camera": camera_diag,
            "phoneDetector": phone_diag,
            "visionDependencies": VISION_DEPENDENCIES_AVAILABLE,
            "fpsTarget": settings.ai_target_fps,
            "status": "healthy" if camera_diag["isConnected"] else "degraded",
        }

    def shutdown(self) -> None:
        """Cleanly releases all resources on server shutdown."""
        logger.info("Shutting down LiveVisionDetector...")
        self.camera.stop()
        if self._face_mesh:
            try:
                self._face_mesh.close()
            except Exception:
                pass
        if self.phone_detector is not None:
            try:
                self.phone_detector.shutdown()
            except Exception:
                pass
        self.pipeline.clear()
        logger.info("LiveVisionDetector shutdown complete.")

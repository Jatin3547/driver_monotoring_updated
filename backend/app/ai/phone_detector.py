"""Lightweight Pretrained YOLO Phone Detector for Driver Monitoring.

Features:
- Uses official pretrained Ultralytics YOLOv8 nano (yolov8n.pt), class 67: cell phone.
- No custom model training; uses off-the-shelf COCO weights.
- Single initialization with lazy loading and explicit failure reporting.
- Background threaded execution to ensure inference does NOT starve
  the camera capture or the async FastAPI event loop.
- Spatial driver-interaction zone heuristic (distinguishes phone in driver hand/ear
  from phone elsewhere in cab or passenger seat).
- Structured output: bounding box, confidence, timestamp, interaction flag.
"""

import logging
import os
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("fleet.ai.phone")

try:
    import numpy as np
    import torch
    from ultralytics import YOLO

    YOLO_DEPENDENCIES_AVAILABLE = True
except ImportError:
    YOLO_DEPENDENCIES_AVAILABLE = False


@dataclass
class PhoneDetection:
    detected: bool = False
    confidence: float = 0.0
    bbox: Optional[Tuple[int, int, int, int]] = None  # (x1, y1, x2, y2)
    timestamp: float = 0.0
    in_driver_zone: bool = False
    orientation: str = "unknown"  # portrait | landscape | unknown
    proximity: str = "unknown"    # near-face | steering-level | distant | unknown
    error: Optional[str] = None



class PhoneDetector:
    """Non-blocking pretrained YOLOv8 phone detector for cab monitoring."""

    CELL_PHONE_CLASS_ID = 67  # Standard COCO dataset index for "cell phone"

    def __init__(
        self,
        model_name: str = "yolov8n.pt",
        conf_threshold: float = 0.35,
        input_size: int = 320,
    ) -> None:
        self.model_name = model_name
        self.conf_threshold = conf_threshold
        self.input_size = input_size

        self.model: Optional[Any] = None
        self.available: bool = False
        self.last_error: Optional[str] = None

        self._lock = threading.Lock()
        self._latest_detection = PhoneDetection(timestamp=time.time())
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="YOLOPhoneWorker")
        self._current_future: Optional[Future] = None
        self._inference_count: int = 0
        self._avg_inference_ms: float = 0.0

        self._initialize_model()

    def _initialize_model(self) -> bool:
        if not YOLO_DEPENDENCIES_AVAILABLE:
            self.available = False
            self.last_error = (
                "YOLO dependencies not installed. Install with: pip install ultralytics torch"
            )
            logger.warning(self.last_error)
            return False

        try:
            torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
            model_target = self.model_name
            if not os.path.isabs(model_target):
                backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                candidate = os.path.join(backend_dir, self.model_name)
                if os.path.exists(candidate):
                    model_target = candidate

            logger.info("Loading pretrained YOLO model %s...", model_target)
            self.model = YOLO(model_target)

            # Validate that class 67 corresponds to cell phone
            class_name = self.model.names.get(self.CELL_PHONE_CLASS_ID, "")
            if "phone" not in class_name.lower():
                logger.warning(
                    "Model class %d is '%s' (expected 'cell phone')",
                    self.CELL_PHONE_CLASS_ID,
                    class_name,
                )

            self.available = True
            self.last_error = None
            logger.info("Pretrained YOLO phone detector initialized successfully (%s).", class_name)
            return True
        except Exception as exc:
            self.available = False
            self.last_error = f"Failed to load YOLO model: {exc}"
            logger.error(self.last_error)
            return False

    def is_in_driver_zone(
        self,
        phone_bbox: Tuple[int, int, int, int],
        face_bbox: Optional[Tuple[int, int, int, int]],
        frame_shape: Tuple[int, int],
    ) -> bool:
        """Determines if a detected phone is in the driver's hand/ear interaction zone.

        Heuristic:
        - If face_bbox is available, expand it horizontally and downwards to cover
          the driver's ears, jaw, neck, and upper chest where a hand-held phone sits.
        - If face_bbox is not available, check if the phone is within the central 70% of the frame.
        """
        px1, py1, px2, py2 = phone_bbox
        phone_center_x = (px1 + px2) / 2.0
        phone_center_y = (py1 + py2) / 2.0

        if face_bbox is None:
            # Fallback when face landmark detector is momentarily occluded:
            # accept phone if within standard driver viewing area
            h, w = frame_shape[:2]
            return (0.15 * w <= phone_center_x <= 0.85 * w) and (0.10 * h <= phone_center_y <= 0.90 * h)

        fx1, fy1, fx2, fy2 = face_bbox
        fw = fx2 - fx1
        fh = fy2 - fy1

        # Interaction zone around driver's head & hands
        zone_x1 = fx1 - int(fw * 0.9)
        zone_x2 = fx2 + int(fw * 0.9)
        zone_y1 = max(0, fy1 - int(fh * 0.2))
        zone_y2 = fy2 + int(fh * 1.6)

        return (zone_x1 <= phone_center_x <= zone_x2) and (zone_y1 <= phone_center_y <= zone_y2)

    def calculate_proximity(
        self,
        phone_bbox: Tuple[int, int, int, int],
        face_bbox: Optional[Tuple[int, int, int, int]],
        frame_shape: Tuple[int, int],
    ) -> str:
        """Estimates phone proximity/distance from driver head/body."""
        px1, py1, px2, py2 = phone_bbox
        phone_area = (px2 - px1) * (py2 - py1)
        h, w = frame_shape[:2]
        frame_area = h * w

        if face_bbox is not None:
            fx1, fy1, fx2, fy2 = face_bbox
            phone_center_y = (py1 + py2) / 2.0
            # Near head/ear level
            if py1 <= fy2 and phone_center_y >= fy1 - int((fy2 - fy1) * 0.4):
                return "near-face"
            elif py1 > fy2:
                return "steering-level"

        ratio = phone_area / float(frame_area)
        if ratio > 0.05:
            return "near-face"
        elif ratio > 0.012:
            return "steering-level"
        return "distant"

    def _sync_predict(
        self, frame: Any, face_bbox: Optional[Tuple[int, int, int, int]]
    ) -> PhoneDetection:
        """Runs inference on a single frame synchronously."""
        now = time.time()
        if not self.available or self.model is None or frame is None:
            return PhoneDetection(
                detected=False,
                timestamp=now,
                error=self.last_error or "Detector unavailable",
            )

        t0 = time.time()
        try:
            results = self.model.predict(
                frame,
                imgsz=self.input_size,
                classes=[self.CELL_PHONE_CLASS_ID],
                conf=self.conf_threshold,
                verbose=False,
            )
            elapsed_ms = (time.time() - t0) * 1000.0

            best_conf = 0.0
            best_bbox = None

            if results and len(results) > 0 and results[0].boxes is not None:
                boxes = results[0].boxes
                for box in boxes:
                    conf = float(box.conf[0].item())
                    if conf > best_conf:
                        best_conf = conf
                        coords = box.xyxy[0].cpu().numpy().astype(int)
                        best_bbox = (int(coords[0]), int(coords[1]), int(coords[2]), int(coords[3]))

            in_zone = False
            orientation = "unknown"
            proximity = "unknown"
            detected = best_bbox is not None and best_conf >= self.conf_threshold
            if detected and best_bbox is not None:
                px1, py1, px2, py2 = best_bbox
                phone_w = px2 - px1
                phone_h = py2 - py1
                orientation = "portrait" if phone_h >= phone_w else "landscape"
                proximity = self.calculate_proximity(best_bbox, face_bbox, frame.shape)
                in_zone = self.is_in_driver_zone(best_bbox, face_bbox, frame.shape)

            detection = PhoneDetection(
                detected=detected,
                confidence=round(best_conf, 2),
                bbox=best_bbox,
                timestamp=now,
                in_driver_zone=in_zone,
                orientation=orientation,
                proximity=proximity,
            )

            with self._lock:
                self._latest_detection = detection
                self._inference_count += 1
                self._avg_inference_ms = (
                    0.8 * self._avg_inference_ms + 0.2 * elapsed_ms
                    if self._inference_count > 1
                    else elapsed_ms
                )

            return detection

        except Exception as exc:
            logger.warning("Error running YOLO phone inference: %s", exc)
            return PhoneDetection(detected=False, timestamp=now, error=str(exc))

    def detect_non_blocking(
        self, frame: Any, face_bbox: Optional[Tuple[int, int, int, int]] = None
    ) -> PhoneDetection:
        """Schedules inference on a background worker thread without blocking caller."""
        if not self.available:
            return PhoneDetection(
                detected=False,
                timestamp=time.time(),
                error=self.last_error or "YOLO detector not available",
            )

        # If previous inference finished, schedule a fresh one on the newest frame
        if self._current_future is None or self._current_future.done():
            if frame is not None:
                # Copy frame slice to avoid race conditions with camera worker
                frame_copy = frame.copy()
                self._current_future = self._executor.submit(
                    self._sync_predict, frame_copy, face_bbox
                )

        with self._lock:
            return self._latest_detection

    def get_diagnostics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "available": self.available,
                "model": self.model_name,
                "confidenceThreshold": self.conf_threshold,
                "inputSize": self.input_size,
                "inferenceCount": self._inference_count,
                "avgInferenceMs": round(self._avg_inference_ms, 1),
                "lastError": self.last_error,
            }

    def shutdown(self) -> None:
        """Safely releases thread pool and model resources."""
        logger.info("Shutting down PhoneDetector...")
        self._executor.shutdown(wait=False, cancel_futures=True)
        self.model = None
        self.available = False
        logger.info("PhoneDetector shutdown complete.")

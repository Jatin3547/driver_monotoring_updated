"""Threaded camera capture manager with auto-reconnection and non-blocking frame retrieval.

Features:
- Dedicated background thread continuously captures frames to prevent blocking the async FastAPI event loop.
- Single-frame buffer pattern (always yields the freshest frame, zero latency accumulation).
- Bounded auto-reconnect with exponential backoff on frame read failures or disconnections.
- Resource cleanup on shutdown (guaranteed cv2.VideoCapture release).
- Low-CPU throttling conforming to target FPS.
"""

import logging
import threading
import time
from typing import Optional, Tuple

logger = logging.getLogger("fleet.ai.camera")

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False


class CameraManager:
    """Thread-safe camera manager handling lifecycle, retries, and latest-frame retrieval."""

    @staticmethod
    def _parse_sources(camera_index) -> list:
        if isinstance(camera_index, (list, tuple)):
            raw_list = list(camera_index)
        elif isinstance(camera_index, str) and "," in camera_index:
            raw_list = [s.strip() for s in camera_index.split(",") if s.strip()]
        else:
            raw_list = [camera_index]

        parsed = []
        for s in raw_list:
            if isinstance(s, str) and s.strip().isdigit():
                parsed.append(int(s.strip()))
            else:
                parsed.append(s)
        return parsed

    def __init__(
        self,
        camera_index: int = 0,
        target_fps: int = 15,
        max_reconnect_retries: int = 5,
        initial_backoff_seconds: float = 1.0,
    ) -> None:
        self.camera_index = camera_index
        self.candidate_sources = self._parse_sources(camera_index)
        self.active_source = None
        self.target_fps = max(1, target_fps)
        self.max_reconnect_retries = max_reconnect_retries
        self.initial_backoff_seconds = initial_backoff_seconds

        self._cap: Optional[object] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.RLock()

        # Frame storage
        self._latest_frame = None
        self._latest_timestamp: float = 0.0
        self._frame_count: int = 0
        self._last_injected_time: float = 0.0

        # Health & diagnostics
        self._status: str = "stopped"  # "active" | "disconnected" | "reconnecting" | "error" | "stopped"
        self._last_error: Optional[str] = None
        self._fps_actual: float = 0.0
        self._frame_width: int = 0
        self._frame_height: int = 0
        self._reconnect_attempts: int = 0

    @property
    def is_connected(self) -> bool:
        with self._lock:
            return self._status == "active" and (self._cap is not None or (time.time() - self._last_injected_time) < 2.5)

    @property
    def status(self) -> str:
        with self._lock:
            return self._status

    @property
    def diagnostics(self) -> dict:
        with self._lock:
            display_index = self.active_source or (
                self.candidate_sources[0] if self.candidate_sources else self.camera_index
            )
            is_conn = self._status == "active" and (self._cap is not None or (time.time() - self._last_injected_time) < 2.5)
            return {
                "cameraIndex": display_index,
                "activeSource": str(self.active_source) if self.active_source else None,
                "candidateSources": self.candidate_sources,
                "status": self._status,
                "isConnected": is_conn,
                "fpsTarget": self.target_fps,
                "fpsActual": round(self._fps_actual, 1),
                "frameWidth": self._frame_width,
                "frameHeight": self._frame_height,
                "frameCount": self._frame_count,
                "lastError": self._last_error,
                "reconnectAttempts": self._reconnect_attempts,
            }

    def inject_frame(self, frame, source_name: str = "usb_camera") -> None:
        """Injects an external frame (e.g. from browser webcam or USB bridge)."""
        now = time.time()
        with self._lock:
            self._latest_frame = frame
            self._latest_timestamp = now
            self._frame_count += 1
            self._status = "active"
            self._last_error = None
            self.active_source = source_name
            self._frame_width = frame.shape[1] if hasattr(frame, "shape") else 640
            self._frame_height = frame.shape[0] if hasattr(frame, "shape") else 480
            self._last_injected_time = now

    def start(self) -> bool:
        """Start the background capture worker."""
        if not OPENCV_AVAILABLE:
            self._status = "error"
            self._last_error = "OpenCV (cv2) is not installed."
            logger.error("Cannot start camera: OpenCV not available.")
            return False

        with self._lock:
            if self._running:
                return True
            self._running = True
            self._status = "reconnecting"

        self._thread = threading.Thread(target=self._capture_worker, name="CameraCaptureWorker", daemon=True)
        self._thread.start()
        logger.info("Camera capture worker started for source %s", self.camera_index)
        return True

    def stop(self, timeout: float = 2.0) -> None:
        """Gracefully stop the background capture worker and release camera hardware."""
        with self._lock:
            if not self._running:
                return
            self._running = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

        self._release_capture()
        with self._lock:
            self._status = "stopped"
            self._latest_frame = None
        logger.info("Camera capture worker stopped and hardware released.")

    def get_latest_frame(self) -> Tuple[bool, Optional[object], float]:
        """Returns (success, frame, timestamp). Frame is a BGR numpy ndarray or None."""
        with self._lock:
            if self._latest_frame is None or self._status != "active":
                return False, None, self._latest_timestamp
            return True, self._latest_frame.copy(), self._latest_timestamp

    @staticmethod
    def _is_network_reachable(url: str, timeout: float = 0.6) -> bool:
        """Quick TCP probe to avoid 30s ffmpeg connect hangs on offline network cameras."""
        try:
            import socket
            from urllib.parse import urlparse
            parsed = urlparse(url)
            host = parsed.hostname
            if not host:
                return True
            port = parsed.port or (4747 if "4747" in url else (80 if parsed.scheme == "http" else 443))
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                s.connect((host, port))
                return True
        except Exception:
            return False

    def _open_single_source(self, raw_source: object) -> bool:
        """Attempts to open a specific camera source."""
        try:
            source = raw_source
            if isinstance(source, str) and source.strip().isdigit():
                source = int(source.strip())

            if isinstance(source, int):
                import sys
                import os
                if sys.platform.startswith("linux") and not os.path.exists(f"/dev/video{source}"):
                    return False

                cap = None
                if sys.platform == "win32":
                    for backend in [cv2.CAP_MSMF, cv2.CAP_DSHOW, cv2.CAP_ANY]:
                        try:
                            temp_cap = cv2.VideoCapture(source, backend)
                            if temp_cap.isOpened():
                                cap = temp_cap
                                break
                            temp_cap.release()
                        except Exception:
                            continue
                else:
                    cap = cv2.VideoCapture(source)

                if cap is None or not cap.isOpened():
                    if cap is not None:
                        cap.release()
                    return False
            else:
                source_str = str(source).strip()
                if "://" in source_str:
                    if not self._is_network_reachable(source_str, timeout=0.6):
                        return False
                cap = cv2.VideoCapture(source_str)

            if not cap.isOpened():
                cap.release()
                return False

            # Configure resolution and FPS hints
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, self.target_fps)
            try:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:
                pass

            # Probe reading one frame to confirm hardware stream is healthy
            ok, test_frame = cap.read()
            if not ok or test_frame is None:
                cap.release()
                return False

            # Check if this frame is a static placeholder / DroidCam splash screen
            import numpy as np
            is_splash = (np.mean(test_frame <= 15) > 0.99) and (np.std(test_frame) < 8.0)
            if is_splash:
                logger.warning("Camera source %s outputs DroidCam splash screen placeholder.", raw_source)
                if len(self.candidate_sources) > 1 and raw_source != self.candidate_sources[-1]:
                    logger.info("Skipping splash screen source %s to try next candidate.", raw_source)
                    cap.release()
                    return False

            self._cap = cap
            self.active_source = raw_source
            self._frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or test_frame.shape[1]
            self._frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or test_frame.shape[0]
            return True
        except Exception as exc:
            logger.debug("Exception opening camera source %s: %s", raw_source, exc)
            return False

    def _open_capture(self) -> bool:
        """Attempts to open any of the candidate video capture devices."""
        if not OPENCV_AVAILABLE:
            return False

        for source in self.candidate_sources:
            if self._open_single_source(source):
                return True
        return False

    def _release_capture(self) -> None:
        """Release underlying cv2 VideoCapture."""
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None

    def _capture_worker(self) -> None:
        """Worker loop running in a dedicated background thread."""
        target_interval = 1.0 / self.target_fps
        fps_timer = time.time()
        fps_frames = 0

        while self._running:
            now = time.time()
            # If external frames (USB browser/bridge) are active, do not clash with cv2 capture
            if self._last_injected_time and (now - self._last_injected_time) < 2.5:
                time.sleep(target_interval)
                continue

            # 1. Connect / Reconnect if needed
            if self._cap is None or not self._cap.isOpened():
                with self._lock:
                    self._status = "reconnecting"

                reconnected = False
                backoff = self.initial_backoff_seconds

                for attempt in range(1, self.max_reconnect_retries + 1):
                    if not self._running:
                        break

                    with self._lock:
                        self._reconnect_attempts = attempt

                    logger.info("Attempting camera connection (attempt %d/%d)...", attempt, self.max_reconnect_retries)
                    if self._open_capture():
                        reconnected = True
                        with self._lock:
                            self._status = "active"
                            self._last_error = None
                            self._reconnect_attempts = 0
                        logger.info("Camera connected successfully on source %s (%dx%d)",
                                    self.active_source, self._frame_width, self._frame_height)
                        break

                    time.sleep(backoff)
                    backoff = min(backoff * 1.5, 5.0)

                if not reconnected:
                    with self._lock:
                        self._status = "error"
                        self._last_error = f"Failed to connect to camera {self.candidate_sources} after {self.max_reconnect_retries} attempts."
                    logger.error(self._last_error)
                    # Idle sleep before next retry cycle
                    time.sleep(3.0)
                    continue

            # 2. Acquire frame
            start_time = time.time()
            try:
                ok, frame = self._cap.read()
            except Exception as exc:
                ok, frame = False, None
                logger.warning("Error reading frame: %s", exc)

            if not ok or frame is None:
                logger.warning("Camera dropped stream. Reconnecting...")
                self._release_capture()
                with self._lock:
                    self._status = "disconnected"
                    self._last_error = "Frame acquisition failed."
                time.sleep(0.5)
                continue

            # 3. Store frame atomically
            now = time.time()
            with self._lock:
                self._latest_frame = frame
                self._latest_timestamp = now
                self._frame_count += 1
                fps_frames += 1

            # 4. Update rolling FPS every 2 seconds
            if now - fps_timer >= 2.0:
                with self._lock:
                    self._fps_actual = fps_frames / (now - fps_timer)
                fps_frames = 0
                fps_timer = now

            # 5. Sleep pacing:
            # Network streams (e.g. DroidCam HTTP/RTSP) are already naturally paced by the phone's network transmission clock.
            # Adding artificial sleep causes network frames to queue up in the socket buffer, causing seconds of lag!
            # We only sleep for local webcam or video file replay.
            is_network_stream = isinstance(self.camera_index, str) and ("://" in self.camera_index or "http" in self.camera_index)
            if not is_network_stream:
                elapsed = time.time() - start_time
                sleep_time = target_interval - elapsed
                if sleep_time > 0.002:
                    time.sleep(sleep_time)

        self._release_capture()

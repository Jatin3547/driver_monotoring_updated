"""Tests for camera switching, crash-proof HTTP MJPEG reader, and monitoring source endpoints."""

import io
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
import numpy as np

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

from app.ai.camera import CameraManager, HTTPMJPEGVideoCapture
from app.api.routes.monitoring import router
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _manager_headers():
    response = client.post(
        "/api/auth/login",
        data={"username": "admin@fleetguard.demo", "password": "admin123"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


class MockMJPEGHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/video":
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=--frame")
            self.end_headers()

            # Generate 3 test frames
            for color in [(255, 0, 0), (0, 255, 0), (0, 0, 255)]:
                f = np.zeros((240, 320, 3), dtype=np.uint8)
                f[:] = color
                _, enc = cv2.imencode(".jpg", f)
                b = enc.tobytes()
                try:
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + b + b"\r\n")
                    time.sleep(0.02)
                except Exception:
                    break
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


class TestCameraSourceSwitch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start ephemeral mock HTTP MJPEG server
        cls.server = HTTPServer(("127.0.0.1", 0), MockMJPEGHandler)
        cls.port = cls.server.server_port
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_http_mjpeg_reader_parses_frames_without_crash(self):
        url = f"http://127.0.0.1:{self.port}/video"
        cap = HTTPMJPEGVideoCapture(url, timeout=2.0)
        self.assertTrue(cap.isOpened())

        ok, frame = cap.read()
        self.assertTrue(ok)
        self.assertIsNotNone(frame)
        self.assertEqual(frame.shape, (240, 320, 3))

        cap.release()
        self.assertFalse(cap.isOpened())

    def test_camera_manager_switch_source(self):
        cam = CameraManager(camera_index=0)
        self.assertEqual(cam.candidate_sources, [0])

        # Switch to network stream
        net_url = f"http://127.0.0.1:{self.port}/video"
        cam.switch_source(net_url)
        self.assertEqual(cam.active_source, net_url)
        self.assertEqual(cam.candidate_sources, [net_url])

        # Release hardware for browser
        cam.release_hardware()
        self.assertIsNone(cam._cap)
        self.assertEqual(cam.status, "active")

        # Switch back to local webcam
        cam.switch_source(1)
        self.assertEqual(cam.active_source, 1)

        cam.stop()

    def test_api_select_source_endpoint(self):
        # Select webcam
        headers = _manager_headers()
        res = client.post("/api/monitoring/select-source", json={"sourceType": "webcam"}, headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("ok"))
        self.assertEqual(data.get("sourceType"), "webcam")

        # Select DroidCam
        res = client.post(
            "/api/monitoring/select-source",
            json={"sourceType": "droidcam", "url": "http://192.168.0.4:4747/video"},
            headers=headers,
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("ok"))
        self.assertEqual(data.get("sourceType"), "droidcam")

    def test_api_probe_network_camera_endpoint(self):
        # Probe our local mock server
        headers = _manager_headers()
        res = client.get(f"/api/monitoring/probe-network-camera?url=http://127.0.0.1:{self.port}/video", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("reachable"))

        # Probe unreachable host
        res = client.get("/api/monitoring/probe-network-camera?url=http://192.0.2.1:4747/video", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data.get("reachable"))


if __name__ == "__main__":
    unittest.main()

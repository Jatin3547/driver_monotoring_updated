"""Integration tests for Evidence API endpoints and Streaming."""

import io
import os
import shutil
import subprocess
import tempfile
import unittest
from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.db.session import Base
from app.main import app
from app.models import Driver, Evidence, Incident, User, Vehicle
from app.services.storage import LocalStorageProvider
from app.services.video_service import get_ffmpeg_binary
import app.services.storage as storage_module


class TestEvidenceAPI(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.old_storage_dir = settings.evidence_storage_dir
        settings.evidence_storage_dir = self.temp_dir
        self.provider = LocalStorageProvider(self.temp_dir)
        storage_module._local_provider = self.provider

        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)
        self.engine = create_engine(f"sqlite:///{self.db_path}", poolclass=NullPool)
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)

        def override_get_db():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = lambda: User(id="u-admin", email="admin@fleetguard.demo", role="fleet_admin", full_name="Admin")
        self.client = TestClient(app)

        # Seed initial Driver, Vehicle, Incident
        with self.Session() as db:
            driver = Driver(code="DRV-TEST", name="Test Driver", license_number="L1", phone="123", email="t@d.com", joined_date=date(2026, 1, 1))
            vehicle = Vehicle(code="VEH-TEST", plate_number="KA-01-9999", make="Tata", model="Truck", year=2022, type="truck")
            db.add_all([driver, vehicle])
            db.flush()

            incident = Incident(
                driver_id=driver.id,
                vehicle_id=vehicle.id,
                type="drowsiness",
                severity="high",
                description="Test drowsy event",
            )
            db.add(incident)
            db.commit()
            self.incident_id = incident.id
            self.driver_id = driver.id
            self.vehicle_id = vehicle.id

        # Generate a small valid test WebM file for uploads using FFmpeg testsrc
        self.sample_webm_bytes = self._create_sample_webm()

    def _create_sample_webm(self) -> bytes:
        tmp_webm = os.path.join(self.temp_dir, "sample.webm")
        ffmpeg_exe = get_ffmpeg_binary()
        cmd = [
            ffmpeg_exe,
            "-y",
            "-f", "lavfi",
            "-i", "testsrc=duration=1:size=160x120:rate=10",
            "-c:v", "libvpx",
            tmp_webm,
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        with open(tmp_webm, "rb") as f:
            return f.read()

    def _create_splash_webm(self) -> bytes:
        tmp_webm = os.path.join(self.temp_dir, "splash.webm")
        ffmpeg_exe = get_ffmpeg_binary()
        cmd = [
            ffmpeg_exe,
            "-y",
            "-f", "lavfi",
            "-i", "color=c=black:duration=1:size=160x120:rate=10",
            "-c:v", "libvpx",
            tmp_webm,
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        with open(tmp_webm, "rb") as f:
            return f.read()

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()
        settings.evidence_storage_dir = self.old_storage_dir
        storage_module._local_provider = None
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except OSError:
                pass

    def test_upload_and_stream_evidence(self):
        # Upload valid WebM
        files = {
            "video": ("recording.webm", io.BytesIO(self.sample_webm_bytes), "video/webm"),
        }
        data = {
            "pre_event_seconds": "5.0",
            "post_event_seconds": "10.0",
        }
        res = self.client.post(f"/api/evidence/upload/{self.incident_id}", files=files, data=data)
        self.assertEqual(res.status_code, 201)
        body = res.json()
        self.assertEqual(body["incidentId"], self.incident_id)
        self.assertEqual(body["status"], "available")
        self.assertIsNotNone(body["sha256Hash"])
        self.assertGreater(len(body["sha256Hash"]), 50)
        self.assertIn("/download", body["downloadUrl"])
        self.assertEqual(body["fileType"], "video/mp4")

        evidence_id = body["id"]

        # Test metadata retrieval
        meta_res = self.client.get(f"/api/evidence/{evidence_id}")
        self.assertEqual(meta_res.status_code, 200)
        self.assertEqual(meta_res.json()["id"], evidence_id)

        # Test video streaming range request (HTTP 206 Partial Content)
        stream_res = self.client.get(
            f"/api/evidence/{evidence_id}/stream",
            headers={"Range": "bytes=0-1023"},
        )
        self.assertEqual(stream_res.status_code, 206)
        self.assertIn("bytes 0-1023/", stream_res.headers.get("content-range", ""))
        self.assertEqual(stream_res.headers.get("content-type"), "video/mp4")

        # Test SHA-256 integrity verification endpoint
        verify_res = self.client.get(f"/api/evidence/{evidence_id}/verify-hash")
        self.assertEqual(verify_res.status_code, 200)
        verify_body = verify_res.json()
        self.assertTrue(verify_body["matches"])
        self.assertEqual(verify_body["storedHash"], verify_body["computedHash"])

        # Test protection toggle
        protect_res = self.client.patch(
            f"/api/evidence/{evidence_id}/protect",
            json={"isProtected": True},
        )
        self.assertEqual(protect_res.status_code, 200)
        self.assertTrue(protect_res.json()["isProtected"])

    def test_storage_stats_endpoint(self):
        res = self.client.get("/api/evidence/storage-stats")
        self.assertEqual(res.status_code, 200)
        stats = res.json()
        self.assertIn("usedMb", stats)
        self.assertIn("maxMb", stats)
        self.assertIn("quotaPercentage", stats)

    def test_upload_rejected_for_splash_screen(self):
        splash_bytes = self._create_splash_webm()
        files = {
            "video": ("recording.webm", io.BytesIO(splash_bytes), "video/webm"),
        }
        res = self.client.post(f"/api/evidence/upload/{self.incident_id}", files=files)
        self.assertEqual(res.status_code, 201)
        body = res.json()
        self.assertEqual(body["incidentId"], self.incident_id)
        self.assertEqual(body["status"], "failed")
        self.assertIn("Evidence rejected", body.get("errorMessage", ""))
        self.assertIn("splash screen detected", body.get("errorMessage", ""))


if __name__ == "__main__":
    unittest.main()

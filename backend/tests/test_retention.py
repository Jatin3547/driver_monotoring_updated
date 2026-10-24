"""Tests for Phase 3 7-Day Retention Cleanup Policy."""

import os
import shutil
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.session import Base
from app.models import Driver, Evidence, Incident, Vehicle
from app.services.evidence_manager import run_retention_cleanup
from app.services.storage import LocalStorageProvider
import app.services.storage as storage_module


class TestRetentionCleanup(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.old_dir = settings.evidence_storage_dir
        self.old_days = settings.evidence_retention_days

        settings.evidence_storage_dir = self.temp_dir
        settings.evidence_retention_days = 7

        self.provider = LocalStorageProvider(self.temp_dir)
        storage_module._local_provider = self.provider

        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)
        self.engine = create_engine(f"sqlite:///{self.db_path}", poolclass=NullPool)
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        # Seed minimal Driver and Vehicle
        driver = Driver(code="DRV-TEST", name="Test Driver", license_number="LIC-1", phone="123", email="t@d.com", joined_date=date(2026, 1, 1))
        vehicle = Vehicle(code="VEH-TEST", plate_number="KA-01-1234", make="Tata", model="Truck", year=2022, type="truck")
        self.db.add_all([driver, vehicle])
        self.db.flush()

        self.driver_id = driver.id
        self.vehicle_id = vehicle.id

    def tearDown(self):
        self.db.close()
        self.engine.dispose()
        settings.evidence_storage_dir = self.old_dir
        settings.evidence_retention_days = self.old_days
        storage_module._local_provider = None
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except OSError:
                pass

    def test_purge_expired_unprotected_evidence(self):
        # Create an expired incident & evidence (10 days old, unprotected)
        inc_old = Incident(driver_id=self.driver_id, vehicle_id=self.vehicle_id, type="drowsiness", severity="high")
        self.db.add(inc_old)
        self.db.flush()

        video_path = os.path.join(self.temp_dir, "old_clip.mp4")
        with open(video_path, "wb") as f:
            f.write(b"sample mp4 video data")

        snap_path = os.path.join(self.temp_dir, "old_snap.jpg")
        with open(snap_path, "wb") as f:
            f.write(b"sample jpeg data")

        old_date = datetime.now(timezone.utc) - timedelta(days=10)
        ev_old = Evidence(
            incident_id=inc_old.id,
            driver_id=self.driver_id,
            vehicle_id=self.vehicle_id,
            file_path=video_path,
            snapshot_path=snap_path,
            file_size_bytes=len(b"sample mp4 video data"),
            is_protected=False,
            status="available",
            created_at=old_date,
        )
        self.db.add(ev_old)
        self.db.commit()

        # Create a recent incident & evidence (2 days old, unprotected)
        inc_recent = Incident(driver_id=self.driver_id, vehicle_id=self.vehicle_id, type="phone_use", severity="high")
        self.db.add(inc_recent)
        self.db.flush()

        recent_video = os.path.join(self.temp_dir, "recent_clip.mp4")
        with open(recent_video, "wb") as f:
            f.write(b"recent video bytes")

        recent_date = datetime.now(timezone.utc) - timedelta(days=2)
        ev_recent = Evidence(
            incident_id=inc_recent.id,
            driver_id=self.driver_id,
            vehicle_id=self.vehicle_id,
            file_path=recent_video,
            file_size_bytes=len(b"recent video bytes"),
            is_protected=False,
            status="available",
            created_at=recent_date,
        )
        self.db.add(ev_recent)
        self.db.commit()

        # Run retention cleanup
        res = run_retention_cleanup(self.db)
        self.assertEqual(res["expiredCount"], 1)

        # Old file should be deleted from disk and status updated to expired
        self.assertFalse(os.path.exists(video_path))
        self.assertFalse(os.path.exists(snap_path))
        self.db.refresh(ev_old)
        self.assertEqual(ev_old.status, "expired")

        # Recent file must be kept intact
        self.assertTrue(os.path.exists(recent_video))
        self.db.refresh(ev_recent)
        self.assertEqual(ev_recent.status, "available")

    def test_protected_old_evidence_is_preserved(self):
        # Create an expired incident (15 days old) but marked is_protected=True
        inc = Incident(driver_id=self.driver_id, vehicle_id=self.vehicle_id, type="distraction", severity="high")
        self.db.add(inc)
        self.db.flush()

        protected_path = os.path.join(self.temp_dir, "critical_evidence.mp4")
        with open(protected_path, "wb") as f:
            f.write(b"protected video content")

        old_date = datetime.now(timezone.utc) - timedelta(days=15)
        ev = Evidence(
            incident_id=inc.id,
            driver_id=self.driver_id,
            vehicle_id=self.vehicle_id,
            file_path=protected_path,
            is_protected=True,
            status="available",
            created_at=old_date,
        )
        self.db.add(ev)
        self.db.commit()

        res = run_retention_cleanup(self.db)
        self.assertEqual(res["expiredCount"], 0)
        self.assertTrue(os.path.exists(protected_path))
        self.db.refresh(ev)
        self.assertEqual(ev.status, "available")


if __name__ == "__main__":
    unittest.main()

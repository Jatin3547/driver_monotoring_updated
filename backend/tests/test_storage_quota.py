"""Tests for Phase 3 Evidence Storage Quota Enforcement and Reservations."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from app.core.config import settings
from app.services.evidence_manager import (
    check_storage_quota_available,
    get_storage_stats,
    release_recording_slot,
    reserve_recording_slot,
)
from app.services.storage import LocalStorageProvider
import app.services.storage as storage_module


class TestStorageQuota(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.old_dir = settings.evidence_storage_dir
        self.old_max = settings.evidence_max_storage_mb
        self.old_reserved = settings.evidence_reserved_recording_mb

        settings.evidence_storage_dir = self.temp_dir
        settings.evidence_max_storage_mb = 10  # 10 MB for testing
        settings.evidence_reserved_recording_mb = 3  # 3 MB per slot

        self.provider = LocalStorageProvider(self.temp_dir)
        storage_module._local_provider = self.provider

    def tearDown(self):
        # Clean up reservations
        while release_recording_slot():
            pass
        settings.evidence_storage_dir = self.old_dir
        settings.evidence_max_storage_mb = self.old_max
        settings.evidence_reserved_recording_mb = self.old_reserved
        storage_module._local_provider = None
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_empty_storage_stats(self):
        stats = get_storage_stats()
        self.assertEqual(stats["usedBytes"], 0)
        self.assertEqual(stats["maxMb"], 10)
        self.assertEqual(stats["activeRecordings"], 0)
        self.assertFalse(stats["isQuotaExceeded"])

    def test_reservation_slots_and_exhaustion(self):
        # 10 MB quota / 3 MB per slot -> can reserve at most 3 slots (3*3 = 9 MB <= 10 MB)
        self.assertTrue(reserve_recording_slot())
        self.assertTrue(reserve_recording_slot())
        self.assertTrue(reserve_recording_slot())
        # 4th slot would exceed 10 MB (4*3 = 12 MB > 10 MB)
        self.assertFalse(reserve_recording_slot())

        stats = get_storage_stats()
        self.assertEqual(stats["activeRecordings"], 3)
        self.assertEqual(stats["reservedMb"], 9.0)

        # Release one slot
        release_recording_slot()
        stats_after = get_storage_stats()
        self.assertEqual(stats_after["activeRecordings"], 2)

        # Now 1 slot can be reserved again
        self.assertTrue(reserve_recording_slot())
        release_recording_slot()
        release_recording_slot()
        release_recording_slot()

    def test_quota_check_with_existing_files(self):
        # Create a 6 MB dummy file
        dummy_file = Path(self.temp_dir) / "test_6mb.bin"
        with open(dummy_file, "wb") as f:
            f.write(b"0" * (6 * 1024 * 1024))

        stats = get_storage_stats()
        self.assertEqual(stats["usedMb"], 6.0)

        # 6 MB used + 3 MB slot = 9 MB <= 10 MB -> 1 slot works
        self.assertTrue(reserve_recording_slot())
        # 6 MB used + 2 * 3 MB = 12 MB > 10 MB -> 2nd slot fails
        self.assertFalse(reserve_recording_slot())

        release_recording_slot()


if __name__ == "__main__":
    unittest.main()

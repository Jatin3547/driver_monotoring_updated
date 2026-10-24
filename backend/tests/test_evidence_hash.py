"""Tests for SHA-256 Calculation, Verification, and Tamper Detection."""

import os
import tempfile
import unittest
from pathlib import Path

from app.services.video_service import compute_sha256, verify_sha256


class TestEvidenceHash(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test_media.mp4"
        with open(self.test_file, "wb") as f:
            f.write(b"FLEETGUARD Incident Video Content - Phase 3 Verification Payload")

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

    def test_compute_sha256_reproducible(self):
        hash1 = compute_sha256(self.test_file)
        hash2 = compute_sha256(self.test_file)
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)

    def test_verify_sha256_matches(self):
        expected_hash = compute_sha256(self.test_file)
        self.assertTrue(verify_sha256(self.test_file, expected_hash))

    def test_tamper_detection(self):
        original_hash = compute_sha256(self.test_file)
        # Modify one byte in the file
        with open(self.test_file, "ab") as f:
            f.write(b"tampered")

        # Now verification must fail
        self.assertFalse(verify_sha256(self.test_file, original_hash))

    def test_non_existent_file(self):
        missing_path = Path(self.temp_dir) / "non_existent.mp4"
        self.assertFalse(verify_sha256(missing_path, "a" * 64))


if __name__ == "__main__":
    unittest.main()

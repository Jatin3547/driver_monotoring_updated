"""Tests for FFmpeg Transcoding and MP4 Playability Validation."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from app.services.video_service import (
    convert_webm_to_mp4,
    extract_snapshot_from_video,
    get_ffmpeg_binary,
    validate_mp4_playable,
)


class TestVideoConversion(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.input_video = Path(self.temp_dir) / "test_input.webm"
        self.output_mp4 = Path(self.temp_dir) / "test_output.mp4"
        self.snapshot_jpg = Path(self.temp_dir) / "test_snapshot.jpg"

        # Generate a small 1-second synthetic video using FFmpeg lavfi testsrc
        ffmpeg_exe = get_ffmpeg_binary()
        cmd = [
            ffmpeg_exe,
            "-y",
            "-f", "lavfi",
            "-i", "testsrc=duration=1.5:size=320x240:rate=15",
            "-c:v", "libvpx",
            str(self.input_video),
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_ffmpeg_binary_discovery(self):
        ffmpeg_exe = get_ffmpeg_binary()
        self.assertTrue(os.path.exists(ffmpeg_exe))
        self.assertTrue(os.path.isfile(ffmpeg_exe))

    def test_transcode_and_playability_validation(self):
        success, details = convert_webm_to_mp4(self.input_video, self.output_mp4)
        self.assertTrue(success, f"Transcoding failed: {details}")
        self.assertTrue(self.output_mp4.exists())
        self.assertGreater(self.output_mp4.stat().st_size, 0)

        # Validate playability
        is_playable, frame_count, duration, details = validate_mp4_playable(self.output_mp4)
        self.assertTrue(is_playable, f"Playability validation failed: {details}")
        self.assertGreaterEqual(frame_count, 15)
        self.assertGreater(duration, 0.5)

    def test_snapshot_extraction(self):
        # Transcode to MP4 first
        convert_webm_to_mp4(self.input_video, self.output_mp4)
        # Extract snapshot at t=0.5s
        ok = extract_snapshot_from_video(self.output_mp4, self.snapshot_jpg, timestamp_seconds=0.5)
        self.assertTrue(ok)
        self.assertTrue(self.snapshot_jpg.exists())
        self.assertGreater(self.snapshot_jpg.stat().st_size, 100)

    def test_invalid_corrupted_input_handling(self):
        corrupted_file = Path(self.temp_dir) / "corrupt.webm"
        with open(corrupted_file, "wb") as f:
            f.write(b"not a valid webm file at all")

        bad_output = Path(self.temp_dir) / "bad_output.mp4"
        success, error_msg = convert_webm_to_mp4(corrupted_file, bad_output)
        self.assertFalse(success)
        self.assertIn("failed", error_msg.lower())


if __name__ == "__main__":
    unittest.main()

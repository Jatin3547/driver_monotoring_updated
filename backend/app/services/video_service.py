"""Video processing, transcoding, validation, and SHA-256 integrity service for FLEETGUARD evidence.

Converts browser-recorded WebM footage into genuine H.264/AAC MP4 files,
extracts still snapshots, verifies video playability, and calculates
cryptographic SHA-256 digests.
"""

import hashlib
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Tuple

from app.core.config import settings

logger = logging.getLogger("fleet.video_service")


def get_ffmpeg_binary() -> str:
    """Discovers available FFmpeg binary: custom config, system PATH, or bundled imageio-ffmpeg."""
    if settings.ffmpeg_path and os.path.exists(settings.ffmpeg_path):
        return settings.ffmpeg_path

    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:
        logger.warning("imageio-ffmpeg unavailable: %s", e)

    raise RuntimeError(
        "FFmpeg binary not found. Please install imageio-ffmpeg or configure FFMPEG_PATH in .env"
    )


def compute_sha256(file_path: Path | str) -> str:
    """Calculates SHA-256 digest across a file on disk."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_sha256(file_path: Path | str, expected_hash: str) -> bool:
    """Verifies whether the on-disk file matches its expected SHA-256 digest."""
    if not os.path.exists(file_path):
        return False
    actual_hash = compute_sha256(file_path)
    return actual_hash.lower() == expected_hash.lower()


def validate_mp4_playable(mp4_path: Path | str) -> Tuple[bool, int, float, str]:
    """Validates that the file is a genuine, playable MP4 with valid video streams.
    
    Returns (is_playable, frame_count, duration_seconds, details).
    """
    path_str = str(mp4_path)
    if not os.path.exists(path_str) or os.path.getsize(path_str) == 0:
        return False, 0, 0.0, "File is empty or does not exist"

    try:
        import cv2

        cap = cv2.VideoCapture(path_str)
        if not cap.isOpened():
            return False, 0, 0.0, "OpenCV failed to open MP4 container"

        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        if frame_count <= 0 or width <= 0 or height <= 0:
            return False, frame_count, 0.0, f"Invalid stream geometry: {width}x{height}, frames={frame_count}"

        duration = frame_count / fps if fps > 0 else 0.0
        return True, frame_count, duration, f"Valid MP4 ({width}x{height}, {fps:.1f} fps, {frame_count} frames, {duration:.1f}s)"
    except Exception as exc:
        return False, 0, 0.0, f"Validation exception: {str(exc)}"


def convert_webm_to_mp4(
    input_webm_path: Path | str,
    output_mp4_path: Path | str,
) -> Tuple[bool, str]:
    """Converts a WebM recording to a genuine, web-optimized H.264/AAC MP4.
    
    Uses -movflags +faststart to ensure the moov atom is placed at the front
    for fast seekable streaming in web browsers.
    """
    try:
        ffmpeg_exe = get_ffmpeg_binary()
    except RuntimeError as re:
        return False, str(re)

    input_str = str(input_webm_path)
    output_str = str(output_mp4_path)

    cmd = [
        ffmpeg_exe,
        "-y",  # Overwrite output if present
        "-fflags", "+genpts",
        "-i", input_str,
        "-vf", "setpts=PTS-STARTPTS",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output_str,
    ]

    logger.info("Executing FFmpeg transcode: %s -> %s", input_str, output_str)
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if result.returncode != 0:
        logger.error("FFmpeg transcode failed (code %d): %s", result.returncode, result.stderr)
        return False, f"FFmpeg failed with exit code {result.returncode}: {result.stderr[-300:] if result.stderr else 'unknown error'}"

    # Verify playability
    is_valid, frames, duration, details = validate_mp4_playable(output_str)
    if not is_valid:
        logger.error("Generated MP4 failed playability validation: %s", details)
        return False, f"Playability check failed: {details}"

    logger.info("Successfully converted WebM to MP4: %s (%s)", output_str, details)
    return True, details


def extract_snapshot_from_video(
    video_path: Path | str,
    output_jpeg_path: Path | str,
    timestamp_seconds: float = 5.0,
) -> bool:
    """Extracts a still JPEG frame from the video at a given timestamp (e.g. t=5s event trigger)."""
    try:
        ffmpeg_exe = get_ffmpeg_binary()
        cmd = [
            ffmpeg_exe,
            "-y",
            "-ss", str(timestamp_seconds),
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", "2",
            str(output_jpeg_path),
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode == 0 and os.path.exists(str(output_jpeg_path))
    except Exception as exc:
        logger.warning("Failed to extract snapshot via FFmpeg: %s", exc)

    # Fallback to OpenCV frame extraction
    try:
        import cv2
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS) or 15.0
        target_frame = int(timestamp_seconds * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ret, frame = cap.read()
        cap.release()
        if ret and frame is not None:
            cv2.imwrite(str(output_jpeg_path), frame)
            return True
    except Exception as cv_exc:
        logger.warning("OpenCV fallback snapshot extraction failed: %s", cv_exc)

    return False

def check_is_splash_or_static(video_path: Path | str) -> Tuple[bool, str]:
    """Inspects video frames to detect if the recorded footage is a static placeholder,
    disconnected camera screen, or the DroidCam splash screen ("Start DroidCam") instead of real driver footage.

    Returns (is_splash_or_static: bool, details: str).
    """
    path_str = str(video_path)
    if not os.path.exists(path_str) or os.path.getsize(path_str) == 0:
        return False, "File does not exist or is empty"

    try:
        import cv2
        import numpy as np

        cap = cv2.VideoCapture(path_str)
        if not cap.isOpened():
            return False, "Could not open video file with OpenCV"

        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_count <= 0:
            cap.release()
            return False, "Video contains zero frames"

        sample_indices = [
            int(frame_count * 0.1),
            int(frame_count * 0.3),
            int(frame_count * 0.5),
            int(frame_count * 0.7),
            int(frame_count * 0.9),
        ]
        sample_indices = sorted(list(set(max(0, min(idx, frame_count - 1)) for idx in sample_indices)))

        sampled_frames = []
        for idx in sample_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret and frame is not None:
                sampled_frames.append(frame)

        cap.release()

        if not sampled_frames:
            return False, "No valid frames could be read from video"

        black_ratios = [float(np.mean(f <= 15)) for f in sampled_frames]
        std_devs = [float(np.std(f)) for f in sampled_frames]
        mean_vals = [float(np.mean(f)) for f in sampled_frames]

        avg_black_ratio = sum(black_ratios) / len(black_ratios)
        avg_std = sum(std_devs) / len(std_devs)
        avg_mean = sum(mean_vals) / len(mean_vals)

        if avg_black_ratio > 0.985 and avg_std < 10.0 and avg_mean < 2.0:
            return True, f"DroidCam splash screen detected ({avg_black_ratio * 100:.1f}% black pixels, std={avg_std:.1f})"

        if len(sampled_frames) >= 2:
            diffs = []
            for i in range(len(sampled_frames) - 1):
                f_a = sampled_frames[i].astype(float)
                f_b = sampled_frames[i + 1].astype(float)
                diffs.append(float(np.mean(np.abs(f_a - f_b))))
            avg_diff = sum(diffs) / len(diffs)
            if avg_diff < 0.05 and avg_std < 15.0:
                return True, f"Static placeholder image detected (temporal variance = {avg_diff:.4f})"

        return False, "Live driver video verified"
    except Exception as exc:
        logger.warning("Error inspecting video for splash screen: %s", exc)
        return False, f"Inspection error: {exc}"

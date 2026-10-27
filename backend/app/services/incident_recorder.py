"""Automatic evidence recorder for incident events.

Responsibilities
----------------
- Accepts pre-event frames already captured in the camera rolling buffer
  (approx. 5 s before trigger) together with the post-event duration requested
  (approx. 10 s after trigger).
- Assembles pre-event frames + post-event frames into a genuine MP4 file
  via OpenCV VideoWriter (no FFmpeg dependency at record time).
- Saves a JPEG snapshot at the event trigger frame.
- Validates that the resulting MP4 is playable (non-zero frames/dimensions).
- Computes a SHA-256 integrity hash.
- Creates an Evidence database row linked to the incident, sets status to
  "available" on success or "failed" on error.
- Checks and enforces storage quota before writing.
- Runs inside a daemon thread so it never blocks the asyncio event loop.

Design decisions
----------------
- Pure stdlib + OpenCV for frame assembly; does NOT invoke FFmpeg
  (avoiding subprocess + extra deps just for recording from raw frames).
- Thread-safe: each call spawns an isolated daemon thread; no shared state
  beyond the DB session (which is freshly opened inside the thread).
- Idempotent guard: if an Evidence row already exists for the incident,
  the recorder exits early without creating a duplicate.
- Stale Evidence safety: always checks evidence.status before touching
  files; never deletes or overwrites records with status "available"/"pending".
"""

import logging
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.evidence_manager import (
    release_recording_slot,
    reserve_recording_slot,
)

logger = logging.getLogger("fleet.incident_recorder")

# How long to poll for post-event frames before giving up
_POST_EVENT_POLL_INTERVAL: float = 0.1   # seconds between polls
_MAX_POST_EVENT_WAIT: float = 15.0       # hard ceiling — never block longer


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def schedule_evidence_recording(
    incident_id: str,
    driver_id: str,
    vehicle_id: str,
    trip_id: Optional[str],
    safety_event_id: Optional[str],
    pre_event_frames: List[Tuple[float, object]],
    camera_manager,  # CameraManager instance, or None in simulation mode
    pre_event_seconds: float = 5.0,
    post_event_seconds: float = 10.0,
) -> None:
    """Schedules evidence recording for the given incident in a daemon thread.

    Returns immediately; actual I/O runs in the background.
    Safe to call from within the asyncio event loop or any sync thread.

    Parameters
    ----------
    incident_id       : Evidence will be linked to this Incident row.
    driver_id         : FK for Evidence.driver_id.
    vehicle_id        : FK for Evidence.vehicle_id.
    trip_id           : Optional FK for Evidence.trip_id.
    safety_event_id   : Optional FK for the triggering SafetyEvent.
    pre_event_frames  : List[(timestamp_float, BGR_ndarray)] from camera buffer.
    camera_manager    : Live CameraManager, or None (simulation / no camera).
                        When None, only a snapshot from the last pre-event frame
                        is attempted; no post-event footage is collected.
    pre_event_seconds : Informational — stored on Evidence row.
    post_event_seconds: How long to wait for post-event footage (capped at
                        _MAX_POST_EVENT_WAIT for safety).
    """
    t = threading.Thread(
        target=_record_evidence,
        args=(
            incident_id,
            driver_id,
            vehicle_id,
            trip_id,
            safety_event_id,
            list(pre_event_frames),   # defensive copy before the list goes stale
            camera_manager,
            pre_event_seconds,
            post_event_seconds,
        ),
        daemon=True,
        name=f"IncidentRecorder-{incident_id[:8]}",
    )
    t.start()
    logger.info(
        "Evidence recording scheduled for incident %s "
        "(pre=%.1fs post=%.1fs, %d pre-event frames buffered)",
        incident_id,
        pre_event_seconds,
        post_event_seconds,
        len(pre_event_frames),
    )


# ---------------------------------------------------------------------------
# Internal implementation
# ---------------------------------------------------------------------------

def _record_evidence(
    incident_id: str,
    driver_id: str,
    vehicle_id: str,
    trip_id: Optional[str],
    safety_event_id: Optional[str],
    pre_event_frames: List[Tuple[float, object]],
    camera_manager,
    pre_event_seconds: float,
    post_event_seconds: float,
) -> None:
    """Runs entirely in a daemon thread — never touches the asyncio loop."""
    from app.models import Evidence
    from app.services.video_service import compute_sha256, validate_mp4_playable
    from app.services.storage import get_storage_provider

    event_ts = datetime.now(timezone.utc)
    recording_start_ts = event_ts

    db = SessionLocal()
    try:
        # ── Idempotent guard ──────────────────────────────────────────────
        existing = db.query(Evidence).filter(Evidence.incident_id == incident_id).first()
        if existing is not None:
            logger.info(
                "Evidence already exists for incident %s (status=%s) — skipping.",
                incident_id,
                existing.status,
            )
            return

        # ── Storage quota check ───────────────────────────────────────────
        if not reserve_recording_slot():
            _create_failed_evidence(
                db,
                incident_id=incident_id,
                driver_id=driver_id,
                vehicle_id=vehicle_id,
                trip_id=trip_id,
                safety_event_id=safety_event_id,
                pre_event_seconds=pre_event_seconds,
                post_event_seconds=post_event_seconds,
                event_ts=event_ts,
                recording_start_ts=recording_start_ts,
                error_message="Storage quota exceeded — evidence recording skipped.",
            )
            return

        # ── Prepare output paths ──────────────────────────────────────────
        evidence_dir = Path(settings.evidence_storage_dir) / "videos"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        snap_dir = Path(settings.evidence_storage_dir) / "snapshots"
        snap_dir.mkdir(parents=True, exist_ok=True)

        ts_slug = event_ts.strftime("%Y%m%d_%H%M%S")
        mp4_path = evidence_dir / f"inc_{incident_id[:8]}_{ts_slug}.mp4"
        snap_path = snap_dir / f"snap_{incident_id[:8]}_{ts_slug}.jpg"

        # ── Create 'pending' Evidence row immediately ─────────────────────
        ev_id = str(uuid.uuid4())
        pending_ev = Evidence(
            id=ev_id,
            incident_id=incident_id,
            safety_event_id=safety_event_id,
            driver_id=driver_id,
            vehicle_id=vehicle_id,
            trip_id=trip_id,
            file_path=str(mp4_path),
            file_type="video/mp4",
            file_size_bytes=0,
            duration_seconds=pre_event_seconds + post_event_seconds,
            pre_event_seconds=pre_event_seconds,
            post_event_seconds=post_event_seconds,
            retention_days=settings.evidence_retention_days,
            is_protected=False,
            status="pending",
            event_timestamp=event_ts,
            recording_start_timestamp=recording_start_ts,
            expires_at=event_ts + timedelta(days=settings.evidence_retention_days),
        )
        db.add(pending_ev)
        db.commit()
        db.refresh(pending_ev)

        try:
            # ── Collect post-event frames ─────────────────────────────────
            trigger_time = time.time()
            post_event_frames: List[Tuple[float, object]] = []

            if camera_manager is not None:
                wait_seconds = min(post_event_seconds, _MAX_POST_EVENT_WAIT)
                time.sleep(wait_seconds)
                post_event_frames = _collect_post_event_frames(
                    camera_manager, trigger_time, post_event_seconds
                )

            all_frames = pre_event_frames + post_event_frames

            if not all_frames:
                raise RuntimeError(
                    "No frames available for evidence recording — camera may be inactive "
                    "or the rolling buffer was empty at trigger time."
                )

            # ── Save snapshot from the trigger frame (last pre-event) ─────
            snapshot_saved = False
            if pre_event_frames:
                trigger_frame = pre_event_frames[-1][1]
                snapshot_saved = _write_snapshot(trigger_frame, snap_path)

            # ── Assemble MP4 ──────────────────────────────────────────────
            actual_fps, write_ok, write_error = _write_mp4(all_frames, mp4_path)
            if not write_ok:
                raise RuntimeError(f"MP4 write failed: {write_error}")

            # ── Validate MP4 playability ──────────────────────────────────
            is_playable, frame_count, duration_secs, details = validate_mp4_playable(mp4_path)
            if not is_playable:
                raise RuntimeError(f"MP4 playability validation failed: {details}")

            if frame_count == 0 or mp4_path.stat().st_size == 0:
                raise RuntimeError(
                    "MP4 written but reports zero frames or zero file size — aborting."
                )

            # ── SHA-256 integrity hash ────────────────────────────────────
            sha256 = compute_sha256(mp4_path)
            file_size = mp4_path.stat().st_size
            recording_end_ts = datetime.now(timezone.utc)

            # ── Mark Evidence as available ────────────────────────────────
            ev = db.query(Evidence).filter(Evidence.id == ev_id).first()
            if ev is None:
                logger.error(
                    "Evidence row %s vanished during recording for incident %s.",
                    ev_id,
                    incident_id,
                )
                return

            ev.status = "available"
            ev.file_size_bytes = file_size
            ev.duration_seconds = duration_secs
            ev.sha256_hash = sha256
            ev.snapshot_path = str(snap_path) if snapshot_saved else None
            ev.recording_end_timestamp = recording_end_ts
            ev.error_message = None
            db.commit()

            logger.info(
                "Evidence recorded for incident %s: %s "
                "(%.1fs, %d frames, %d bytes, sha256=%s...)",
                incident_id,
                mp4_path.name,
                duration_secs,
                frame_count,
                file_size,
                sha256[:16],
            )

        except Exception as exc:
            logger.error(
                "Evidence recording failed for incident %s: %s",
                incident_id,
                exc,
                exc_info=True,
            )
            # Update pending row to 'failed' — preserve for audit trail
            try:
                ev = db.query(Evidence).filter(Evidence.id == ev_id).first()
                if ev is not None and ev.status == "pending":
                    ev.status = "failed"
                    ev.error_message = str(exc)[:500]
                    ev.recording_end_timestamp = datetime.now(timezone.utc)
                    db.commit()
            except Exception as db_exc:
                logger.error(
                    "Could not update evidence failure status for %s: %s", ev_id, db_exc
                )

            # Clean up any partial output files
            _safe_delete(mp4_path)
            _safe_delete(snap_path)

        finally:
            release_recording_slot()

    except Exception as outer_exc:
        logger.error(
            "Outer exception in evidence recorder thread for incident %s: %s",
            incident_id,
            outer_exc,
            exc_info=True,
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collect_post_event_frames(
    camera_manager,
    trigger_time: float,
    post_event_seconds: float,
) -> List[Tuple[float, object]]:
    """Queries the camera rolling buffer for frames captured after the trigger."""
    post_frames: List[Tuple[float, object]] = []
    deadline = trigger_time + post_event_seconds
    try:
        # Request a slightly wider window to capture all frames since trigger
        frames = camera_manager.get_pre_event_frames(seconds=post_event_seconds + 2.0)
        for ts, frm in frames:
            if trigger_time <= ts <= deadline:
                post_frames.append((ts, frm))
    except Exception as exc:
        logger.warning("Error collecting post-event frames from camera buffer: %s", exc)
    return post_frames


def _write_snapshot(frame, snap_path: Path) -> bool:
    """Encodes a BGR numpy array as a JPEG at the given path.
    Returns True if the file was written with non-zero bytes.
    """
    try:
        import cv2
        cv2.imwrite(str(snap_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return snap_path.exists() and snap_path.stat().st_size > 0
    except Exception as exc:
        logger.warning("Failed to write snapshot to %s: %s", snap_path, exc)
        return False


def _write_mp4(
    frames: List[Tuple[float, object]],
    output_path: Path,
    fallback_fps: float = 15.0,
) -> Tuple[float, bool, str]:
    """Assembles a (timestamp, bgr_frame) list into an MP4 via cv2.VideoWriter.

    Returns
    -------
    (actual_fps, success, error_message)
    """
    try:
        import cv2
    except ImportError:
        return 0.0, False, "OpenCV not available — cannot write evidence MP4."

    if not frames:
        return 0.0, False, "No frames provided."

    # Derive FPS from real timestamps when possible
    fps = fallback_fps
    if len(frames) >= 2:
        total_duration = frames[-1][0] - frames[0][0]
        if total_duration > 0:
            derived = len(frames) / total_duration
            fps = max(1.0, min(round(derived), 120.0))

    # Infer frame dimensions from first valid frame
    width, height = 640, 480
    for _, frm in frames:
        try:
            if hasattr(frm, "shape") and frm.shape[0] > 0 and frm.shape[1] > 0:
                height, width = frm.shape[:2]
                break
        except Exception:
            continue

    output_path.parent.mkdir(parents=True, exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    if not writer.isOpened():
        return 0.0, False, f"cv2.VideoWriter failed to open: {output_path}"

    written = 0
    try:
        for _, frm in frames:
            try:
                if not hasattr(frm, "shape"):
                    continue
                if frm.shape[0] != height or frm.shape[1] != width:
                    frm = cv2.resize(frm, (width, height))
                writer.write(frm)
                written += 1
            except Exception as frame_exc:
                logger.debug("Skipping bad frame during MP4 assembly: %s", frame_exc)
    finally:
        writer.release()

    if written == 0:
        return 0.0, False, "No valid frames were written to the MP4."

    if not output_path.exists() or output_path.stat().st_size == 0:
        return 0.0, False, "MP4 file missing or empty after write."

    return float(fps), True, ""


def _create_failed_evidence(
    db,
    incident_id: str,
    driver_id: str,
    vehicle_id: str,
    trip_id: Optional[str],
    safety_event_id: Optional[str],
    pre_event_seconds: float,
    post_event_seconds: float,
    event_ts: datetime,
    recording_start_ts: datetime,
    error_message: str,
) -> None:
    """Persists a 'failed' Evidence stub so the incident always has an audit trail."""
    from app.models import Evidence
    try:
        ev = Evidence(
            id=str(uuid.uuid4()),
            incident_id=incident_id,
            safety_event_id=safety_event_id,
            driver_id=driver_id,
            vehicle_id=vehicle_id,
            trip_id=trip_id,
            file_path="",
            file_type="video/mp4",
            file_size_bytes=0,
            duration_seconds=pre_event_seconds + post_event_seconds,
            pre_event_seconds=pre_event_seconds,
            post_event_seconds=post_event_seconds,
            retention_days=settings.evidence_retention_days,
            is_protected=False,
            status="failed",
            error_message=error_message[:500],
            event_timestamp=event_ts,
            recording_start_timestamp=recording_start_ts,
            recording_end_timestamp=datetime.now(timezone.utc),
            expires_at=event_ts + timedelta(days=settings.evidence_retention_days),
        )
        db.add(ev)
        db.commit()
        logger.warning(
            "Created failed Evidence stub for incident %s: %s", incident_id, error_message
        )
    except Exception as exc:
        logger.error(
            "Could not persist failed Evidence stub for incident %s: %s", incident_id, exc
        )


def _safe_delete(path: Optional[Path]) -> None:
    """Silently deletes a file, ignoring all errors."""
    if path is None:
        return
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass

"""Evidence lifecycle, quota enforcement, and retention management service.

Enforces configurable 500 MB evidence storage quota with active-recording
reservations, and handles automated 7-day retention cleanup.
"""

import logging
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Evidence
from app.services.storage import get_storage_provider

logger = logging.getLogger("fleet.evidence_manager")

# In-memory reservation tracker for concurrent active recordings
_active_reservations_lock = threading.Lock()
_active_reservations_count: int = 0


def reserve_recording_slot() -> bool:
    """Attempts to reserve storage space for an incoming in-progress recording.
    
    Returns True if quota permits reservation, False if storage quota is exhausted.
    """
    global _active_reservations_count
    provider = get_storage_provider()
    used_bytes = provider.get_total_usage_bytes()
    max_bytes = settings.evidence_max_storage_mb * 1024 * 1024
    slot_bytes = settings.evidence_reserved_recording_mb * 1024 * 1024

    with _active_reservations_lock:
        projected_bytes = used_bytes + ((_active_reservations_count + 1) * slot_bytes)
        if projected_bytes > max_bytes:
            logger.warning(
                "Storage quota exceeded: current=%d MB, reserved=%d MB, limit=%d MB",
                used_bytes // (1024 * 1024),
                (_active_reservations_count * slot_bytes) // (1024 * 1024),
                settings.evidence_max_storage_mb,
            )
            return False
        _active_reservations_count += 1
        return True


def release_recording_slot() -> None:
    """Releases an active recording reservation."""
    global _active_reservations_count
    with _active_reservations_lock:
        if _active_reservations_count > 0:
            _active_reservations_count -= 1


def check_storage_quota_available(additional_bytes: int = 0) -> bool:
    """Checks whether storage quota allows adding the requested byte amount."""
    provider = get_storage_provider()
    used_bytes = provider.get_total_usage_bytes()
    max_bytes = settings.evidence_max_storage_mb * 1024 * 1024
    with _active_reservations_lock:
        reserved_bytes = _active_reservations_count * (settings.evidence_reserved_recording_mb * 1024 * 1024)
    return (used_bytes + reserved_bytes + additional_bytes) <= max_bytes


def get_storage_stats() -> Dict[str, Any]:
    """Returns current evidence storage metrics and quota consumption."""
    provider = get_storage_provider()
    used_bytes = provider.get_total_usage_bytes()
    max_bytes = settings.evidence_max_storage_mb * 1024 * 1024
    with _active_reservations_lock:
        reserved_bytes = _active_reservations_count * (settings.evidence_reserved_recording_mb * 1024 * 1024)

    quota_pct = round(((used_bytes + reserved_bytes) / max_bytes) * 100, 1) if max_bytes > 0 else 0.0

    return {
        "usedBytes": used_bytes,
        "maxBytes": max_bytes,
        "usedMb": round(used_bytes / (1024 * 1024), 2),
        "maxMb": settings.evidence_max_storage_mb,
        "reservedMb": round(reserved_bytes / (1024 * 1024), 2),
        "activeRecordings": _active_reservations_count,
        "quotaPercentage": min(100.0, quota_pct),
        "isQuotaExceeded": (used_bytes + reserved_bytes) >= max_bytes,
        "retentionDays": settings.evidence_retention_days,
    }


def run_retention_cleanup(db: Session) -> Dict[str, Any]:
    """Purges unprotected evidence files older than the retention threshold (default 7 days).
    
    Safe, recoverable, and idempotent:
    - Never deletes records marked 'pending' or currently being processed.
    - Never deletes records marked is_protected=True.
    - Updates database evidence status to 'expired'.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.evidence_retention_days)
    provider = get_storage_provider()

    candidates = (
        db.query(Evidence)
        .filter(
            Evidence.is_protected == False,
            Evidence.status.in_(["available", "failed"]),
            Evidence.created_at < cutoff,
        )
        .all()
    )

    deleted_count = 0
    freed_bytes = 0

    for ev in candidates:
        # Delete video file
        if ev.file_path:
            file_path = provider.get_file_path(ev.file_path)
            if file_path and file_path.exists():
                try:
                    freed_bytes += file_path.stat().st_size
                except OSError:
                    pass
                provider.delete_file(ev.file_path)

        # Delete snapshot file if present
        if ev.snapshot_path:
            snap_path = provider.get_file_path(ev.snapshot_path)
            if snap_path and snap_path.exists():
                try:
                    freed_bytes += snap_path.stat().st_size
                except OSError:
                    pass
                provider.delete_file(ev.snapshot_path)

        ev.status = "expired"
        ev.file_size_bytes = 0
        deleted_count += 1

    db.commit()

    logger.info(
        "Retention cleanup finished: %d expired evidence records cleaned, %d MB freed",
        deleted_count,
        freed_bytes // (1024 * 1024),
    )

    return {
        "expiredCount": deleted_count,
        "freedBytes": freed_bytes,
        "freedMb": round(freed_bytes / (1024 * 1024), 2),
        "cutoffDate": cutoff.isoformat(),
    }

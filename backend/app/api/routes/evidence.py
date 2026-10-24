"""Evidence metadata, video streaming, upload, and integrity endpoints.

Stores genuine MP4 files and snapshots on the filesystem outside SQLite,
enforces 500 MB quota and 7-day retention, verifies SHA-256 hashes,
and streams MP4 video with HTTP 206 Partial Content range seeking.
"""

import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.security import decode_access_token
from app.models import Driver, Evidence, Incident, User, Vehicle
from app.schemas.evidence import (
    EvidenceCreate,
    EvidenceHashVerifyOut,
    EvidenceOut,
    EvidenceProtectUpdate,
)
from app.services.evidence_manager import (
    check_storage_quota_available,
    get_storage_stats,
    release_recording_slot,
    reserve_recording_slot,
    run_retention_cleanup,
)
from app.services.serializers import evidence_to_dict
from app.services.storage import get_storage_provider
from app.services.video_service import (
    compute_sha256,
    convert_webm_to_mp4,
    extract_snapshot_from_video,
    validate_mp4_playable,
    verify_sha256,
)

router = APIRouter()


def _get_user_or_token(
    token: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Helper to authenticate user via either Authorization header or ?token query param (for <video> / <img> tags)."""
    raw_token = None
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split(" ")[1]
    elif token:
        raw_token = token

    if not raw_token:
        return None

    email = decode_access_token(raw_token)
    if not email:
        return None
    return db.query(User).filter(User.email == email).first()


@router.get("/storage-stats")
def storage_stats(current_user: Optional[User] = Depends(_get_user_or_token)):
    return get_storage_stats()


@router.post("/cleanup")
def trigger_retention_cleanup(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(_get_user_or_token),
):
    return run_retention_cleanup(db)


@router.get("/{evidence_id}", response_model=EvidenceOut)
def get_evidence_metadata(
    evidence_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(_get_user_or_token),
):
    ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail=f"Evidence '{evidence_id}' not found")

    driver = db.query(Driver).filter(Driver.id == ev.driver_id).first()
    vehicle = db.query(Vehicle).filter(Vehicle.id == ev.vehicle_id).first()

    return evidence_to_dict(
        ev,
        driver_code=driver.code if driver else None,
        vehicle_code=vehicle.code if vehicle else None,
    )


@router.get("/incident/{incident_id}", response_model=EvidenceOut)
def get_incident_evidence(
    incident_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(_get_user_or_token),
):
    ev = db.query(Evidence).filter(Evidence.incident_id == incident_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail=f"No evidence record for incident '{incident_id}'")

    driver = db.query(Driver).filter(Driver.id == ev.driver_id).first()
    vehicle = db.query(Vehicle).filter(Vehicle.id == ev.vehicle_id).first()

    return evidence_to_dict(
        ev,
        driver_code=driver.code if driver else None,
        vehicle_code=vehicle.code if vehicle else None,
    )


@router.post("", response_model=EvidenceOut, status_code=status.HTTP_201_CREATED)
def create_evidence_record(payload: EvidenceCreate, db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == payload.incidentId).first()
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{payload.incidentId}' not found")

    driver = db.query(Driver).filter(Driver.id == payload.driverId).first()
    if not driver:
        driver = db.query(Driver).filter(Driver.code == payload.driverId).first()
    if not driver:
        raise HTTPException(status_code=404, detail=f"Driver '{payload.driverId}' not found")

    vehicle = db.query(Vehicle).filter(Vehicle.id == payload.vehicleId).first()
    if not vehicle:
        vehicle = db.query(Vehicle).filter(Vehicle.code == payload.vehicleId).first()

    ev = Evidence(
        incident_id=incident.id,
        safety_event_id=payload.safetyEventId,
        driver_id=driver.id,
        vehicle_id=vehicle.id if vehicle else incident.vehicle_id,
        trip_id=payload.tripId,
        file_path=payload.filePath,
        file_type=payload.fileType,
        file_size_bytes=payload.fileSizeBytes,
        duration_seconds=payload.durationSeconds,
        pre_event_seconds=payload.preEventSeconds,
        post_event_seconds=payload.postEventSeconds,
        is_protected=payload.isProtected,
        status=getattr(payload, "status", "available") or "available",
        sha256_hash=payload.sha256Hash,
        snapshot_path=payload.snapshotPath,
        cloud_upload_status=payload.cloudUploadStatus,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    return evidence_to_dict(ev, driver_code=driver.code, vehicle_code=vehicle.code if vehicle else None)


@router.post("/upload/{incident_id}", response_model=EvidenceOut, status_code=status.HTTP_201_CREATED)
async def upload_incident_evidence(
    incident_id: str,
    video: UploadFile = File(...),
    snapshot: Optional[UploadFile] = File(None),
    pre_event_seconds: float = Form(5.0),
    post_event_seconds: float = Form(10.0),
    event_timestamp: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Receives browser-recorded WebM footage, enforces storage quota, transcodes
    to genuine playable MP4 via FFmpeg, extracts/validates snapshot, computes SHA-256 digest,
    and links evidence to the incident.
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")

    # Reserve quota slot for in-progress processing
    if not reserve_recording_slot():
        # Record failed evidence row so incident has permanent record of failure
        existing_ev = db.query(Evidence).filter(Evidence.incident_id == incident_id).first()
        if not existing_ev:
            existing_ev = Evidence(
                incident_id=incident.id,
                driver_id=incident.driver_id,
                vehicle_id=incident.vehicle_id or "",
                file_path="",
                status="failed",
                error_message=f"Storage quota exceeded ({settings.evidence_max_storage_mb} MB limit reached)",
            )
            db.add(existing_ev)
            db.commit()
            db.refresh(existing_ev)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Storage quota of {settings.evidence_max_storage_mb} MB is exhausted. Evidence recording rejected.",
        )

    provider = get_storage_provider()
    staging_dir = provider.base_dir / "staging"
    staging_dir.mkdir(parents=True, exist_ok=True)

    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    temp_webm_path = staging_dir / f"{incident_id}_{timestamp_str}_raw.webm"
    final_mp4_name = f"{incident_id}_{timestamp_str}.mp4"
    final_mp4_path = provider.base_dir / final_mp4_name
    final_snap_name = f"{incident_id}_{timestamp_str}_snapshot.jpg"
    final_snap_path = provider.base_dir / final_snap_name

    try:
        # Write incoming WebM bytes to staging
        with open(temp_webm_path, "wb") as f_out:
            while chunk := await video.read(65536):
                f_out.write(chunk)

        # Transcode WebM to genuine playable MP4 using FFmpeg
        transcode_ok, transcode_details = convert_webm_to_mp4(temp_webm_path, final_mp4_path)

        if not transcode_ok:
            # Transcoding failed
            ev = db.query(Evidence).filter(Evidence.incident_id == incident_id).first()
            if not ev:
                ev = Evidence(
                    incident_id=incident.id,
                    driver_id=incident.driver_id,
                    vehicle_id=incident.vehicle_id or "",
                    file_path="",
                    status="failed",
                    error_message=f"FFmpeg transcode failed: {transcode_details}",
                )
                db.add(ev)
            else:
                ev.status = "failed"
                ev.error_message = f"FFmpeg transcode failed: {transcode_details}"
            db.commit()
            db.refresh(ev)
            driver = db.query(Driver).filter(Driver.id == incident.driver_id).first()
            vehicle = db.query(Vehicle).filter(Vehicle.id == incident.vehicle_id).first() if incident.vehicle_id else None
            return evidence_to_dict(ev, driver_code=driver.code if driver else None, vehicle_code=vehicle.code if vehicle else None)

        # Validate playability & duration
        is_playable, frame_count, duration, play_details = validate_mp4_playable(final_mp4_path)
        if not is_playable:
            ev = db.query(Evidence).filter(Evidence.incident_id == incident_id).first()
            if not ev:
                ev = Evidence(
                    incident_id=incident.id,
                    driver_id=incident.driver_id,
                    vehicle_id=incident.vehicle_id or "",
                    file_path=str(final_mp4_path),
                    status="failed",
                    error_message=f"Playability validation failed: {play_details}",
                )
                db.add(ev)
            else:
                ev.status = "failed"
                ev.error_message = f"Playability validation failed: {play_details}"
            db.commit()
            db.refresh(ev)
            driver = db.query(Driver).filter(Driver.id == incident.driver_id).first()
            vehicle = db.query(Vehicle).filter(Vehicle.id == incident.vehicle_id).first() if incident.vehicle_id else None
            return evidence_to_dict(ev, driver_code=driver.code if driver else None, vehicle_code=vehicle.code if vehicle else None)

        # Compute SHA-256 digest of the finalized MP4
        file_sha256 = compute_sha256(final_mp4_path)
        file_size = final_mp4_path.stat().st_size

        # Handle Snapshot (use provided JPEG or extract from MP4 at pre_event timestamp)
        has_snapshot = False
        if snapshot is not None:
            with open(final_snap_path, "wb") as snap_out:
                while snap_chunk := await snapshot.read(65536):
                    snap_out.write(snap_chunk)
            if final_snap_path.exists() and final_snap_path.stat().st_size > 0:
                has_snapshot = True

        if not has_snapshot:
            # Auto-extract snapshot at trigger point (pre_event_seconds)
            has_snapshot = extract_snapshot_from_video(
                final_mp4_path,
                final_snap_path,
                timestamp_seconds=pre_event_seconds,
            )

        # Parse event timestamp
        parsed_event_ts = None
        if event_timestamp:
            try:
                parsed_event_ts = datetime.fromisoformat(event_timestamp.replace("Z", "+00:00"))
            except Exception:
                parsed_event_ts = incident.timestamp
        else:
            parsed_event_ts = incident.timestamp

        now_utc = datetime.now(timezone.utc)
        expires_at = now_utc + timedelta(days=settings.evidence_retention_days)

        ev = db.query(Evidence).filter(Evidence.incident_id == incident_id).first()
        if not ev:
            ev = Evidence(
                incident_id=incident.id,
                safety_event_id=incident.safety_event_id,
                driver_id=incident.driver_id,
                vehicle_id=incident.vehicle_id or "",
                trip_id=incident.trip_id,
                file_path=str(final_mp4_path),
                file_type="video/mp4",
                file_size_bytes=file_size,
                duration_seconds=duration,
                pre_event_seconds=pre_event_seconds,
                post_event_seconds=post_event_seconds,
                retention_days=settings.evidence_retention_days,
                is_protected=False,
                snapshot_path=str(final_snap_path) if has_snapshot else None,
                sha256_hash=file_sha256,
                status="available",
                cloud_upload_status="pending",
                event_timestamp=parsed_event_ts,
                recording_start_timestamp=now_utc - timedelta(seconds=duration),
                recording_end_timestamp=now_utc,
                expires_at=expires_at,
            )
            db.add(ev)
        else:
            ev.file_path = str(final_mp4_path)
            ev.file_type = "video/mp4"
            ev.file_size_bytes = file_size
            ev.duration_seconds = duration
            ev.pre_event_seconds = pre_event_seconds
            ev.post_event_seconds = post_event_seconds
            ev.sha256_hash = file_sha256
            ev.snapshot_path = str(final_snap_path) if has_snapshot else None
            ev.status = "available"
            ev.error_message = None
            ev.event_timestamp = parsed_event_ts
            ev.expires_at = expires_at

        db.commit()
        db.refresh(ev)

        # Broadcast evidence upload completion over WebSocket so dashboard reloads in real-time
        try:
            from app.websocket.manager import manager
            await manager.broadcast("evidence_uploaded", {
                "incidentId": incident_id,
                "evidenceId": ev.id,
                "status": ev.status,
            })
        except Exception:
            pass

        driver = db.query(Driver).filter(Driver.id == incident.driver_id).first()
        vehicle = db.query(Vehicle).filter(Vehicle.id == incident.vehicle_id).first() if incident.vehicle_id else None

        return evidence_to_dict(
            ev,
            driver_code=driver.code if driver else None,
            vehicle_code=vehicle.code if vehicle else None,
        )

    finally:
        release_recording_slot()
        # Clean up temporary staging webm
        if temp_webm_path.exists():
            try:
                temp_webm_path.unlink()
            except OSError:
                pass


@router.get("/{evidence_id}/stream")
def stream_evidence_video(
    evidence_id: str,
    request: Request,
    token: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Streams MP4 video with HTTP 206 Partial Content range requests for smooth seeking."""
    ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    provider = get_storage_provider()
    file_path = provider.get_file_path(ev.file_path)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="Evidence video file not found on disk")

    file_size = file_path.stat().st_size
    range_header = request.headers.get("range")

    if not range_header:
        # Full content response
        return FileResponse(
            path=str(file_path),
            media_type="video/mp4",
            headers={"Accept-Ranges": "bytes", "Content-Length": str(file_size)},
        )

    # Parse HTTP Byte Range (e.g. 'bytes=1024-2048')
    try:
        range_spec = range_header.strip().replace("bytes=", "")
        parts = range_spec.split("-")
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1
        end = min(end, file_size - 1)
        content_length = end - start + 1
    except Exception:
        raise HTTPException(status_code=416, detail="Requested Range Not Satisfiable")

    def iter_bytes():
        with open(file_path, "rb") as f:
            f.seek(start)
            remaining = content_length
            chunk_size = 65536
            while remaining > 0:
                read_size = min(chunk_size, remaining)
                data = f.read(read_size)
                if not data:
                    break
                remaining -= len(data)
                yield data

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Type": "video/mp4",
    }

    return StreamingResponse(
        iter_bytes(),
        status_code=status.HTTP_206_PARTIAL_CONTENT,
        headers=headers,
    )


@router.get("/{evidence_id}/snapshot")
def get_evidence_snapshot(
    evidence_id: str,
    token: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    provider = get_storage_provider()
    if ev.snapshot_path:
        snap_path = provider.get_file_path(ev.snapshot_path)
        if snap_path and snap_path.exists():
            return FileResponse(path=str(snap_path), media_type="image/jpeg")

    # If no snapshot file on disk, return 1x1 placeholder
    placeholder_jpeg = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00"
        b"\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f"
        b"\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00"
        b"\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01"
        b"\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08"
        b"\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
    )
    return Response(content=placeholder_jpeg, media_type="image/jpeg")


@router.get("/{evidence_id}/download")
def download_evidence_file(
    evidence_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(_get_user_or_token),
):
    ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail=f"Evidence '{evidence_id}' not found")

    provider = get_storage_provider()
    file_path = provider.get_file_path(ev.file_path)
    if file_path and file_path.exists():
        return FileResponse(
            path=str(file_path),
            media_type="video/mp4",
            filename=file_path.name,
        )

    raise HTTPException(status_code=404, detail="Evidence file missing or expired")


@router.get("/{evidence_id}/verify-hash", response_model=EvidenceHashVerifyOut)
def verify_evidence_hash(
    evidence_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(_get_user_or_token),
):
    """Calculates SHA-256 digest directly from file on disk and verifies integrity."""
    ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    provider = get_storage_provider()
    file_path = provider.get_file_path(ev.file_path)
    if not file_path or not file_path.exists():
        return EvidenceHashVerifyOut(
            evidenceId=evidence_id,
            matches=False,
            storedHash=ev.sha256_hash,
            computedHash=None,
            details="Evidence file is not present on disk",
        )

    computed = compute_sha256(file_path)
    matches = (computed.lower() == (ev.sha256_hash or "").lower())

    return EvidenceHashVerifyOut(
        evidenceId=evidence_id,
        matches=matches,
        storedHash=ev.sha256_hash,
        computedHash=computed,
        details="SHA-256 integrity verified" if matches else "Hash mismatch: file has been modified or corrupted",
    )


@router.patch("/{evidence_id}/protect", response_model=EvidenceOut)
def toggle_evidence_protection(
    evidence_id: str,
    payload: EvidenceProtectUpdate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(_get_user_or_token),
):
    ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail=f"Evidence '{evidence_id}' not found")

    ev.is_protected = payload.isProtected
    db.commit()
    db.refresh(ev)

    driver = db.query(Driver).filter(Driver.id == ev.driver_id).first()
    vehicle = db.query(Vehicle).filter(Vehicle.id == ev.vehicle_id).first()

    return evidence_to_dict(
        ev,
        driver_code=driver.code if driver else None,
        vehicle_code=vehicle.code if vehicle else None,
    )

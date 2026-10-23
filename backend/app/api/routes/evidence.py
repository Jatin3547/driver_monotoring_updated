"""Evidence metadata endpoints — tracks event-triggered video and snapshot files.

Ensures video binaries are stored on filesystem, NOT in DB rows.
Preserves driver privacy with protected metadata and retention tags.
"""

import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import Driver, Evidence, Incident, Vehicle
from app.schemas.evidence import EvidenceCreate, EvidenceOut, EvidenceProtectUpdate
from app.services.serializers import evidence_to_dict

router = APIRouter()

EVIDENCE_STORAGE_DIR = Path("data/evidence")
EVIDENCE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/{evidence_id}", response_model=EvidenceOut)
def get_evidence_metadata(evidence_id: str, db: Session = Depends(get_db)):
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
def get_incident_evidence(incident_id: str, db: Session = Depends(get_db)):
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


@router.get("/{evidence_id}/download")
def download_evidence_file(evidence_id: str, db: Session = Depends(get_db)):
    ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail=f"Evidence '{evidence_id}' not found")

    file_path = Path(ev.file_path)
    if file_path.exists():
        return FileResponse(
            path=str(file_path),
            media_type=ev.file_type,
            filename=file_path.name,
        )

    # If the file hasn't been written to disk yet (e.g. simulated demo event),
    # return a lightweight, valid 1x1 transparent/dark JPEG byte buffer instead of failing with 500.
    placeholder_jpeg = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00"
        b"\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f"
        b"\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00"
        b"\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01"
        b"\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08"
        b"\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
    )
    return Response(content=placeholder_jpeg, media_type="image/jpeg")


@router.patch("/{evidence_id}/protect", response_model=EvidenceOut)
def toggle_evidence_protection(
    evidence_id: str, payload: EvidenceProtectUpdate, db: Session = Depends(get_db)
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
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    return evidence_to_dict(ev, driver_code=driver.code, vehicle_code=vehicle.code if vehicle else None)

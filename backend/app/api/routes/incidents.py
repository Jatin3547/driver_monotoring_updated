"""Incidents endpoints — fleet manager access required for all operations.

Drivers cannot list, create, modify, or delete incidents via the API.
The AI monitoring pipeline creates incidents internally; fleet managers
review and manage them here.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_driver, get_current_user_optional, get_db, require_fleet_admin
from app.models import Driver, Evidence, Incident, SafetyEvent, Trip, User, Vehicle
from app.schemas.incident import IncidentCreate, IncidentUpdate
from app.services.serializers import incident_to_dict
from app.services.storage import get_storage_provider
from app.websocket.manager import manager

logger = logging.getLogger("fleet.incidents")
router = APIRouter()


def _lookup(db: Session, driver_code: str, vehicle_code: str | None):
    driver = db.query(Driver).filter(Driver.code == driver_code).first()
    vehicle = db.query(Vehicle).filter(Vehicle.code == vehicle_code).first() if vehicle_code else None
    return driver, vehicle


@router.get("")
def list_incidents(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    has_video: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_fleet_admin),
):
    """List incidents — fleet managers only."""
    query = db.query(Incident).order_by(Incident.timestamp.desc())
    if has_video is not None:
        if has_video:
            query = query.filter(Incident.evidence.has())
        else:
            query = query.filter(~Incident.evidence.has())

    incidents = query.offset(offset).limit(limit).all()
    driver_map = {d.id: d for d in db.query(Driver).all()}
    vehicle_map = {v.id: v for v in db.query(Vehicle).all()}
    return [
        incident_to_dict(i, driver_map.get(i.driver_id), vehicle_map.get(i.vehicle_id))
        for i in incidents
    ]


@router.get("/mine")
def list_my_incidents(
    db: Session = Depends(get_db),
    driver: Driver = Depends(get_current_driver),
):
    """Driver-accessible incidents for the authenticated driver only."""
    incidents = (
        db.query(Incident)
        .filter(Incident.driver_id == driver.id)
        .order_by(Incident.timestamp.desc())
        .all()
    )
    vehicle_map = {v.id: v for v in db.query(Vehicle).all()}
    return [
        incident_to_dict(i, driver, vehicle_map.get(i.vehicle_id))
        for i in incidents
    ]


@router.post("", status_code=201)
def create_incident(
    payload: IncidentCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_fleet_admin),
):
    """Create an incident — fleet managers only."""
    driver, vehicle = _lookup(db, payload.driverId, payload.vehicleId)
    if not driver:
        raise HTTPException(status_code=404, detail=f"Driver '{payload.driverId}' not found")

    trip = None
    if payload.tripId:
        trip = db.query(Trip).filter(Trip.id == payload.tripId).first()
    if not trip:
        trip = db.query(Trip).filter(Trip.driver_id == driver.id, Trip.status == "in-progress").first()

    incident = Incident(
        driver_id=driver.id,
        vehicle_id=vehicle.id if vehicle else None,
        trip_id=trip.id if trip else None,
        type=payload.type,
        severity=payload.severity,
        status="open",
        location=payload.location,
        description=payload.description,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(incident)
    driver.incident_count += 1
    db.commit()
    db.refresh(incident)
    return incident_to_dict(incident, driver, vehicle)


@router.patch("/{incident_id}")
def update_incident(
    incident_id: str,
    payload: IncidentUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_fleet_admin),
):
    """Update incident status/acknowledgement — fleet managers only."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")

    if payload.status is not None:
        incident.status = payload.status
    if payload.acknowledgedBy is not None:
        incident.acknowledged_by = payload.acknowledgedBy

    db.commit()
    db.refresh(incident)
    driver = db.query(Driver).filter(Driver.id == incident.driver_id).first()
    vehicle = db.query(Vehicle).filter(Vehicle.id == incident.vehicle_id).first() if incident.vehicle_id else None
    return incident_to_dict(incident, driver, vehicle)


@router.delete("/{incident_id}")
async def delete_incident(
    incident_id: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to delete incidents",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if current_user.role not in ("fleet_admin", "admin", "manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only fleet managers and admins can delete incidents",
        )

    # 1. Clean up linked evidence and physical files
    storage = get_storage_provider()
    evidence_records = db.query(Evidence).filter(Evidence.incident_id == incident_id).all()
    for ev in evidence_records:
        if ev.file_path:
            storage.delete_file(ev.file_path)
        if ev.snapshot_path:
            storage.delete_file(ev.snapshot_path)
        db.delete(ev)

    # 2. Clean up linked safety event if present
    if incident.safety_event_id:
        se = db.query(SafetyEvent).filter(SafetyEvent.id == incident.safety_event_id).first()
        if se:
            db.delete(se)

    # 3. Decrement driver incident_count
    if incident.driver_id:
        driver = db.query(Driver).filter(Driver.id == incident.driver_id).first()
        if driver and driver.incident_count > 0:
            driver.incident_count -= 1

    # 4. Delete the incident
    db.delete(incident)
    db.commit()
    logger.info("Deleted incident %s and all associated evidence/safety events.", incident_id)

    # 5. Broadcast deletion over WebSocket
    try:
        await manager.broadcast("incident_deleted", {"id": incident_id})
    except Exception as ws_err:
        logger.debug("WebSocket broadcast error on incident deletion: %s", ws_err)

    return {"ok": True, "id": incident_id, "message": "Incident deleted successfully"}

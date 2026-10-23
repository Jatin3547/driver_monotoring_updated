from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import Driver, Incident, Trip, Vehicle
from app.schemas.incident import IncidentCreate, IncidentUpdate
from app.services.serializers import incident_to_dict

router = APIRouter()


def _lookup(db: Session, driver_code: str, vehicle_code: str | None):
    driver = db.query(Driver).filter(Driver.code == driver_code).first()
    vehicle = db.query(Vehicle).filter(Vehicle.code == vehicle_code).first() if vehicle_code else None
    return driver, vehicle


@router.get("")
def list_incidents(db: Session = Depends(get_db)):
    incidents = db.query(Incident).order_by(Incident.timestamp.desc()).all()
    driver_map = {d.id: d for d in db.query(Driver).all()}
    vehicle_map = {v.id: v for v in db.query(Vehicle).all()}
    return [
        incident_to_dict(i, driver_map.get(i.driver_id), vehicle_map.get(i.vehicle_id))
        for i in incidents
    ]


@router.post("", status_code=201)
def create_incident(payload: IncidentCreate, db: Session = Depends(get_db)):
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
def update_incident(incident_id: str, payload: IncidentUpdate, db: Session = Depends(get_db)):
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

"""Trips endpoints — tracks active and historical fleet trips.

Associates trips with drivers and vehicles, and connects with incidents
that happen during the trip.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import Driver, Incident, Trip, Vehicle
from app.schemas.trip import TripCreate, TripOut, TripUpdate
from app.services.serializers import trip_to_dict

router = APIRouter()


@router.get("", response_model=list[TripOut])
def list_trips(
    status_filter: str | None = None,
    driver_code: str | None = None,
    vehicle_code: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Trip).order_by(Trip.start_time.desc())

    if status_filter:
        query = query.filter(Trip.status == status_filter)

    if driver_code:
        driver = db.query(Driver).filter(Driver.code == driver_code).first()
        if driver:
            query = query.filter(Trip.driver_id == driver.id)
        else:
            return []

    if vehicle_code:
        vehicle = db.query(Vehicle).filter(Vehicle.code == vehicle_code).first()
        if vehicle:
            query = query.filter(Trip.vehicle_id == vehicle.id)
        else:
            return []

    trips = query.all()
    driver_map = {d.id: d for d in db.query(Driver).all()}
    vehicle_map = {v.id: v for v in db.query(Vehicle).all()}

    # Count incidents per trip
    incident_counts: dict[str, int] = {}
    for inc in db.query(Incident).filter(Incident.trip_id.isnot(None)).all():
        if inc.trip_id:
            incident_counts[inc.trip_id] = incident_counts.get(inc.trip_id, 0) + 1

    return [
        trip_to_dict(
            t,
            driver=driver_map.get(t.driver_id),
            vehicle=vehicle_map.get(t.vehicle_id),
            incident_count=incident_counts.get(t.id, 0),
        )
        for t in trips
    ]


@router.get("/active", response_model=list[TripOut])
def list_active_trips(db: Session = Depends(get_db)):
    """Returns currently in-progress trips with live status."""
    return list_trips(status_filter="in-progress", db=db)


@router.get("/{trip_id}", response_model=TripOut)
def get_trip(trip_id: str, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail=f"Trip '{trip_id}' not found")

    driver = db.query(Driver).filter(Driver.id == trip.driver_id).first()
    vehicle = db.query(Vehicle).filter(Vehicle.id == trip.vehicle_id).first()
    incident_count = db.query(Incident).filter(Incident.trip_id == trip.id).count()

    return trip_to_dict(trip, driver, vehicle, incident_count)


@router.post("", response_model=TripOut, status_code=status.HTTP_201_CREATED)
def start_trip(payload: TripCreate, db: Session = Depends(get_db)):
    driver = db.query(Driver).filter(Driver.code == payload.driverCode).first()
    if not driver:
        raise HTTPException(status_code=404, detail=f"Driver '{payload.driverCode}' not found")

    vehicle = db.query(Vehicle).filter(Vehicle.code == payload.vehicleCode).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail=f"Vehicle '{payload.vehicleCode}' not found")

    # Mark driver on-trip and vehicle active
    driver.status = "on-trip"
    driver.assigned_vehicle_id = vehicle.id
    vehicle.status = "active"

    now = datetime.now(timezone.utc)
    trip = Trip(
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        start_time=now,
        start_location=payload.startLocation,
        end_location=payload.endLocation,
        status="in-progress",
        distance_km=0.0,
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)

    return trip_to_dict(trip, driver, vehicle, incident_count=0)


@router.patch("/{trip_id}", response_model=TripOut)
def update_trip(trip_id: str, payload: TripUpdate, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail=f"Trip '{trip_id}' not found")

    driver = db.query(Driver).filter(Driver.id == trip.driver_id).first()
    vehicle = db.query(Vehicle).filter(Vehicle.id == trip.vehicle_id).first()

    if payload.status is not None:
        trip.status = payload.status
        if payload.status in {"completed", "cancelled"}:
            trip.end_time = datetime.now(timezone.utc)
            if driver and driver.status == "on-trip":
                driver.status = "active"
                driver.total_trips += 1
                if payload.distanceKm:
                    driver.total_distance_km += payload.distanceKm

    if payload.endLocation is not None:
        trip.end_location = payload.endLocation

    if payload.distanceKm is not None:
        trip.distance_km = payload.distanceKm
        if vehicle:
            vehicle.odometer_km += payload.distanceKm

    db.commit()
    db.refresh(trip)

    incident_count = db.query(Incident).filter(Incident.trip_id == trip.id).count()
    return trip_to_dict(trip, driver, vehicle, incident_count)

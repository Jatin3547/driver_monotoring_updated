"""Trips endpoints — tracks active and historical fleet trips.

Associates trips with drivers and vehicles, and connects with incidents
that happen during the trip.

Access control
--------------
Fleet managers (fleet_admin/admin/manager): full access to all trips.
Driver-role users: can view only their own trips via GET /my-trips.
                   Cannot list all trips, start trips, or update trips.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import MANAGER_ROLES, get_current_driver, get_current_user, get_db, require_fleet_admin
from app.models import Driver, Incident, Trip, User, Vehicle
from app.schemas.trip import TripCreate, TripOut, TripUpdate
from app.services.serializers import trip_to_dict

router = APIRouter()


def _build_trip_list(trips, db: Session) -> list:
    driver_map = {d.id: d for d in db.query(Driver).all()}
    vehicle_map = {v.id: v for v in db.query(Vehicle).all()}

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


@router.get("", response_model=list[TripOut])
def list_trips(
    status_filter: str | None = None,
    driver_code: str | None = None,
    vehicle_code: str | None = None,
    db: Session = Depends(get_db),
    _admin=Depends(require_fleet_admin),
):
    """List all trips — fleet managers only."""
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

    return _build_trip_list(query.all(), db)


@router.get("/active", response_model=list[TripOut])
def list_active_trips(db: Session = Depends(get_db), _admin=Depends(require_fleet_admin)):
    """Returns currently in-progress trips — fleet managers only."""
    trips = db.query(Trip).filter(Trip.status == "in-progress").order_by(Trip.start_time.desc()).all()
    return _build_trip_list(trips, db)


@router.get("/my-trips", response_model=list[TripOut])
def list_my_trips(
    db: Session = Depends(get_db),
    driver: Driver = Depends(get_current_driver),
):
    """Driver-accessible endpoint — returns only the authenticated driver's own trips."""
    trips = db.query(Trip).filter(Trip.driver_id == driver.id).order_by(Trip.start_time.desc()).all()
    vehicle_map = {v.id: v for v in db.query(Vehicle).all()}
    incident_counts: dict[str, int] = {}
    for inc in db.query(Incident).filter(Incident.driver_id == driver.id, Incident.trip_id.isnot(None)).all():
        if inc.trip_id:
            incident_counts[inc.trip_id] = incident_counts.get(inc.trip_id, 0) + 1
    return [
        trip_to_dict(t, driver=driver, vehicle=vehicle_map.get(t.vehicle_id),
                     incident_count=incident_counts.get(t.id, 0))
        for t in trips
    ]


@router.get("/{trip_id}", response_model=TripOut)
def get_trip(
    trip_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail=f"Trip '{trip_id}' not found")

    driver = db.query(Driver).filter(Driver.id == trip.driver_id).first()
    vehicle = db.query(Vehicle).filter(Vehicle.id == trip.vehicle_id).first()
    incident_count = db.query(Incident).filter(Incident.trip_id == trip.id).count()

    if current_user.role in MANAGER_ROLES:
        return trip_to_dict(trip, driver, vehicle, incident_count)

    if current_user.role == "driver":
        own = db.query(Driver).filter(Driver.user_id == current_user.id).first()
        if own is None or trip.driver_id != own.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You may only access your own trips.",
            )
        return trip_to_dict(trip, driver, vehicle, incident_count)

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")


@router.post("", response_model=TripOut, status_code=status.HTTP_201_CREATED)
def start_trip(payload: TripCreate, db: Session = Depends(get_db), _admin=Depends(require_fleet_admin)):
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
def update_trip(trip_id: str, payload: TripUpdate, db: Session = Depends(get_db), _admin=Depends(require_fleet_admin)):
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

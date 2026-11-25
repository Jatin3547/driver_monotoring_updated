import math
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_driver, get_db, require_fleet_admin
from app.core.config import settings
from app.gps.simulator import record_position
from app.models import Driver, GPSLocation, User, Vehicle
from app.schemas.gps import DriverGPSUpdateIn
from app.services.serializers import gps_to_dict
from app.websocket.manager import manager

router = APIRouter()

# Vehicles with no live signal in the seed data (mirrors the frontend mock:
# offline vehicles report no position).
_NO_SIGNAL_STATUSES = {"offline"}


@router.get("/config")
def gps_driver_config(_driver: Driver = Depends(get_current_driver)):
    """Return update policy to a signed-in driver without requesting location permission."""
    return {
        "updateIntervalSeconds": settings.gps_update_interval_seconds,
        "minimumIntervalSeconds": settings.gps_min_server_interval_seconds,
        "minMovementMeters": settings.gps_min_update_distance_meters,
        "staleAfterSeconds": settings.gps_stale_after_seconds,
        "maxAccuracyMeters": settings.gps_max_accuracy_meters,
    }


def _trackable_vehicles(db: Session) -> list[Vehicle]:
    return [v for v in db.query(Vehicle).all() if v.status not in _NO_SIGNAL_STATUSES]


def _latest_location(db: Session, vehicle: Vehicle, source: str | None = None) -> GPSLocation | None:
    query = db.query(GPSLocation).filter(GPSLocation.vehicle_id == vehicle.id)
    if source:
        query = query.filter(GPSLocation.source == source)
    return query.order_by(GPSLocation.timestamp.desc()).first()


def _visible_location(db: Session, vehicle: Vehicle) -> GPSLocation | None:
    latest = _latest_location(db, vehicle)
    if latest and latest.source == "live":
        return latest  # Keep disconnected devices visible as stale, never replace with a simulated point.
    if settings.gps_mode.strip().lower() == "simulation":
        return record_position(db, vehicle)
    return None


def _distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_m = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi, d_lam = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    return 2 * radius_m * math.asin(math.sqrt(min(1.0, a)))


@router.post("/my-location")
async def gps_update_my_location(
    payload: DriverGPSUpdateIn,
    db: Session = Depends(get_db),
    driver: Driver = Depends(get_current_driver),
):
    """Persist a location only for this authenticated driver's current vehicle."""
    if not driver.assigned_vehicle_id:
        raise HTTPException(status_code=409, detail="No vehicle is assigned to this driver")
    vehicle = db.query(Vehicle).filter(Vehicle.id == driver.assigned_vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=409, detail="Assigned vehicle was not found")
    if payload.accuracy > settings.gps_max_accuracy_meters:
        raise HTTPException(status_code=422, detail="GPS accuracy exceeds the configured maximum")

    now = datetime.now(timezone.utc)
    client_timestamp = payload.timestamp.astimezone(timezone.utc)
    if client_timestamp < now - timedelta(minutes=2) or client_timestamp > now + timedelta(seconds=30):
        raise HTTPException(status_code=422, detail="GPS timestamp is outside the allowed time window")

    previous = _latest_location(db, vehicle, source="live")
    if previous:
        previous_ts = previous.timestamp if previous.timestamp.tzinfo else previous.timestamp.replace(tzinfo=timezone.utc)
        age = (now - previous_ts).total_seconds()
        moved = _distance_meters(previous.latitude, previous.longitude, payload.latitude, payload.longitude)
        if age < settings.gps_min_server_interval_seconds:
            return {"accepted": False, "reason": "minimum update interval", "retryAfterSeconds": round(settings.gps_min_server_interval_seconds - age, 2)}
        uncertainty_distance = max(previous.accuracy_m or 0.0, payload.accuracy)
        movement_threshold = max(settings.gps_min_update_distance_meters, uncertainty_distance)
        if age < settings.gps_update_interval_seconds and moved < movement_threshold:
            return {"accepted": False, "reason": "below movement threshold", "retryAfterSeconds": round(settings.gps_update_interval_seconds - age, 2)}
        if client_timestamp <= previous_ts:
            raise HTTPException(status_code=422, detail="GPS timestamp must be newer than the last accepted update")

    location = GPSLocation(
        vehicle_id=vehicle.id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy_m=payload.accuracy,
        speed_kmh=round(payload.speed * 3.6, 2) if payload.speed is not None else 0.0,
        heading=payload.heading if payload.heading is not None else 0.0,
        reported_speed_kmh=round(payload.speed * 3.6, 2) if payload.speed is not None else None,
        reported_heading=payload.heading,
        acceleration_ms2=0.0,
        source="live",
        timestamp=client_timestamp,
    )
    db.add(location)
    db.commit()
    db.refresh(location)

    event = gps_to_dict(location, vehicle.code, driver.code)
    await manager.broadcast("gps_update", event)
    return {"accepted": True, "location": event}


@router.get("/my-vehicle")
def gps_my_vehicle(
    db: Session = Depends(get_db),
    driver: Driver = Depends(get_current_driver),
):
    """Current position for the authenticated driver's assigned vehicle only."""
    if not driver.assigned_vehicle_id:
        raise HTTPException(status_code=404, detail="No vehicle is assigned to this driver")
    vehicle = db.query(Vehicle).filter(Vehicle.id == driver.assigned_vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Assigned vehicle was not found")
    if vehicle.status in _NO_SIGNAL_STATUSES:
        raise HTTPException(status_code=404, detail="Assigned vehicle has no live GPS signal")
    loc = _visible_location(db, vehicle)
    if not loc:
        raise HTTPException(status_code=404, detail="No GPS position is available")
    return gps_to_dict(loc, vehicle.code, driver.code if loc.source == "live" else None)


@router.get("/vehicles")
def gps_all_vehicles(db: Session = Depends(get_db), _admin: User = Depends(require_fleet_admin)):
    """Current live position when available, else labeled simulation per GPS_MODE."""
    result = []
    for vehicle in _trackable_vehicles(db):
        loc = _visible_location(db, vehicle)
        if loc:
            assigned_driver = vehicle.assigned_driver.code if vehicle.assigned_driver else None
            result.append(gps_to_dict(loc, vehicle.code, assigned_driver if loc.source == "live" else None))
    return result


@router.get("/vehicles/{vehicle_code}")
def gps_one_vehicle(vehicle_code: str, db: Session = Depends(get_db), _admin: User = Depends(require_fleet_admin)):
    vehicle = db.query(Vehicle).filter(Vehicle.code == vehicle_code).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail=f"Vehicle '{vehicle_code}' not found")
    if vehicle.status in _NO_SIGNAL_STATUSES:
        raise HTTPException(status_code=404, detail=f"Vehicle '{vehicle_code}' has no live GPS signal")
    loc = _visible_location(db, vehicle)
    if not loc:
        raise HTTPException(status_code=404, detail=f"Vehicle '{vehicle_code}' has no GPS position")
    return gps_to_dict(loc, vehicle.code)


@router.get("/history/{vehicle_code}")
def gps_history(vehicle_code: str, limit: int = 50, db: Session = Depends(get_db), _admin: User = Depends(require_fleet_admin)):
    vehicle = db.query(Vehicle).filter(Vehicle.code == vehicle_code).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail=f"Vehicle '{vehicle_code}' not found")

    rows = (
        db.query(GPSLocation)
        .filter(GPSLocation.vehicle_id == vehicle.id)
        .order_by(GPSLocation.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [gps_to_dict(r, vehicle.code) for r in rows]


@router.get("/locations")
def gps_locations_alias(db: Session = Depends(get_db), _admin: User = Depends(require_fleet_admin)):
    """Alias matching the existing frontend gpsService.getVehicleLocations()
    call path (`/gps/locations`). Same data as GET /gps/vehicles."""
    return gps_all_vehicles(db)

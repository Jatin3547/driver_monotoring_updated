from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.gps.simulator import record_position
from app.models import GPSLocation, Vehicle
from app.services.serializers import gps_to_dict

router = APIRouter()

# Vehicles with no live signal in the seed data (mirrors the frontend mock:
# offline vehicles report no position).
_NO_SIGNAL_STATUSES = {"offline"}


def _trackable_vehicles(db: Session) -> list[Vehicle]:
    return [v for v in db.query(Vehicle).all() if v.status not in _NO_SIGNAL_STATUSES]


@router.get("/vehicles")
def gps_all_vehicles(db: Session = Depends(get_db)):
    """Current simulated position for every trackable vehicle."""
    result = []
    for vehicle in _trackable_vehicles(db):
        loc = record_position(db, vehicle)
        result.append(gps_to_dict(loc, vehicle.code))
    return result


@router.get("/vehicles/{vehicle_code}")
def gps_one_vehicle(vehicle_code: str, db: Session = Depends(get_db)):
    vehicle = db.query(Vehicle).filter(Vehicle.code == vehicle_code).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail=f"Vehicle '{vehicle_code}' not found")
    if vehicle.status in _NO_SIGNAL_STATUSES:
        raise HTTPException(status_code=404, detail=f"Vehicle '{vehicle_code}' has no live GPS signal")
    loc = record_position(db, vehicle)
    return gps_to_dict(loc, vehicle.code)


@router.get("/history/{vehicle_code}")
def gps_history(vehicle_code: str, limit: int = 50, db: Session = Depends(get_db)):
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
def gps_locations_alias(db: Session = Depends(get_db)):
    """Alias matching the existing frontend gpsService.getVehicleLocations()
    call path (`/gps/locations`). Same data as GET /gps/vehicles."""
    return gps_all_vehicles(db)

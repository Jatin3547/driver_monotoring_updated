"""Vehicle endpoints — fleet managers only, plus a driver-owned assigned vehicle."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_driver, get_db, require_fleet_admin
from app.models import Driver, User, Vehicle
from app.services.serializers import vehicle_to_dict

router = APIRouter()


@router.get("")
def list_vehicles(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_fleet_admin),
):
    vehicles = db.query(Vehicle).all()
    return [vehicle_to_dict(v) for v in vehicles]


@router.get("/assigned")
def get_assigned_vehicle(
    db: Session = Depends(get_db),
    driver: Driver = Depends(get_current_driver),
):
    """Return the authenticated driver's assigned vehicle, if any."""
    if not driver.assigned_vehicle_id:
        raise HTTPException(status_code=404, detail="No vehicle is assigned to this driver")
    vehicle = db.query(Vehicle).filter(Vehicle.id == driver.assigned_vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Assigned vehicle was not found")
    return vehicle_to_dict(vehicle)


@router.get("/{vehicle_code}")
def get_vehicle(
    vehicle_code: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_fleet_admin),
):
    vehicle = db.query(Vehicle).filter(Vehicle.code == vehicle_code).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail=f"Vehicle '{vehicle_code}' not found")
    return vehicle_to_dict(vehicle)

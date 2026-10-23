from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import Vehicle
from app.services.serializers import vehicle_to_dict

router = APIRouter()


@router.get("")
def list_vehicles(db: Session = Depends(get_db)):
    vehicles = db.query(Vehicle).all()
    return [vehicle_to_dict(v) for v in vehicles]


@router.get("/{vehicle_code}")
def get_vehicle(vehicle_code: str, db: Session = Depends(get_db)):
    vehicle = db.query(Vehicle).filter(Vehicle.code == vehicle_code).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail=f"Vehicle '{vehicle_code}' not found")
    return vehicle_to_dict(vehicle)

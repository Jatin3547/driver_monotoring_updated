from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import Driver
from app.services.serializers import driver_to_dict

router = APIRouter()


@router.get("")
def list_drivers(db: Session = Depends(get_db)):
    drivers = db.query(Driver).all()
    return [driver_to_dict(d) for d in drivers]


@router.get("/{driver_code}")
def get_driver(driver_code: str, db: Session = Depends(get_db)):
    driver = db.query(Driver).filter(Driver.code == driver_code).first()
    if not driver:
        raise HTTPException(status_code=404, detail=f"Driver '{driver_code}' not found")
    return driver_to_dict(driver)

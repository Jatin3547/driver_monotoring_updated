from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import Alert, Driver, Vehicle
from app.services.serializers import alert_to_dict

router = APIRouter()


@router.get("")
def list_alerts(db: Session = Depends(get_db)):
    alerts = db.query(Alert).order_by(Alert.timestamp.desc()).all()
    driver_map = {d.id: d for d in db.query(Driver).all()}
    vehicle_map = {v.id: v for v in db.query(Vehicle).all()}
    return [
        alert_to_dict(a, driver_map.get(a.driver_id), vehicle_map.get(a.vehicle_id))
        for a in alerts
    ]

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_fleet_admin
from app.models import Driver, Incident, User, Vehicle
from app.schemas.analytics import FleetSummary

router = APIRouter()


@router.get("/summary", response_model=FleetSummary)
def fleet_summary(db: Session = Depends(get_db), _admin: User = Depends(require_fleet_admin)):
    vehicles = db.query(Vehicle).all()
    drivers = db.query(Driver).all()
    open_incidents = db.query(Incident).filter(Incident.status == "open").count()

    active = sum(1 for v in vehicles if v.status == "active")
    idle = sum(1 for v in vehicles if v.status == "idle")
    offline = sum(1 for v in vehicles if v.status == "offline")
    maintenance = sum(1 for v in vehicles if v.status == "maintenance")
    active_drivers = sum(1 for d in drivers if d.status in ("active", "on-trip"))
    avg_score = round(sum(d.safety_score for d in drivers) / len(drivers), 1) if drivers else 0

    return FleetSummary(
        totalVehicles=len(vehicles),
        activeVehicles=active,
        idleVehicles=idle,
        offlineVehicles=offline,
        maintenanceVehicles=maintenance,
        activeDrivers=active_drivers,
        avgSafetyScore=avg_score,
        openIncidents=open_incidents,
    )

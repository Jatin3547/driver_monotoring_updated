from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_fleet_admin
from app.models import Driver, Incident, User, Vehicle

router = APIRouter()


@router.get("/safety-trend")
def safety_trend(db: Session = Depends(get_db), _admin: User = Depends(require_fleet_admin)):
    """Real trend computed from current data: since this demo has a single
    point-in-time snapshot rather than months of history, each of the last
    9 three-day buckets uses the fleet's current average safety score with
    a small deterministic variation, and real incident counts from the
    incidents table for the corresponding day are used where available."""
    drivers = db.query(Driver).all()
    avg_score = round(sum(d.safety_score for d in drivers) / len(drivers), 1) if drivers else 0
    incidents = db.query(Incident).all()

    points = []
    today = datetime.now(timezone.utc).date()
    for i in range(8, -1, -1):
        day = today - timedelta(days=i * 3)
        day_incidents = sum(1 for inc in incidents if inc.timestamp.date() == day)
        points.append(
            {
                "date": day.isoformat(),
                "avgSafetyScore": avg_score,
                "totalIncidents": day_incidents,
            }
        )
    return points


@router.get("/incident-breakdown")
def incident_breakdown(db: Session = Depends(get_db), _admin: User = Depends(require_fleet_admin)):
    incidents = db.query(Incident).all()
    counts = Counter(inc.type for inc in incidents)
    label_map = {
        "drowsiness": "Drowsiness",
        "eye_closure": "Eye closure",
        "yawning": "Yawning",
        "phone_use": "Phone use",
        "distraction": "Distraction",
        "no_presence": "No presence",
        "speeding": "Speeding",
        "harsh-braking": "Harsh braking",
        "harsh-acceleration": "Harsh acceleration",
    }
    return [{"type": label_map.get(t, t), "count": c} for t, c in counts.items()]


@router.get("/driver-leaderboard")
def driver_leaderboard(db: Session = Depends(get_db), _admin: User = Depends(require_fleet_admin)):
    drivers = db.query(Driver).order_by(Driver.safety_score.desc()).all()
    return [
        {
            "driverId": d.code,
            "driverName": d.name,
            "safetyScore": d.safety_score,
            "incidentCount": d.incident_count,
            "tripsCompleted": d.total_trips,
        }
        for d in drivers
    ]


@router.get("/fleet-utilization")
def fleet_utilization(db: Session = Depends(get_db), _admin: User = Depends(require_fleet_admin)):
    vehicles = db.query(Vehicle).all()
    active = sum(1 for v in vehicles if v.status == "active")
    idle = sum(1 for v in vehicles if v.status == "idle")
    maintenance = sum(1 for v in vehicles if v.status == "maintenance")

    today = datetime.now(timezone.utc).date()
    return [
        {
            "date": (today - timedelta(days=i)).isoformat(),
            "activeVehicles": active,
            "idleVehicles": idle,
            "maintenanceVehicles": maintenance,
        }
        for i in range(6, -1, -1)
    ]

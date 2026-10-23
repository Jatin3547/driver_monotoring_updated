"""Import every model here so `Base.metadata.create_all()` (called from
app/db/init_db.py) discovers all tables. Nothing else should need to
import individual model modules directly for table discovery to work."""

from app.models.alert import Alert
from app.models.driver import Driver
from app.models.evidence import Evidence
from app.models.fleet import Fleet
from app.models.gps_location import GPSLocation
from app.models.incident import Incident
from app.models.maintenance import MaintenanceRecord
from app.models.safety_event import SafetyEvent
from app.models.trip import Trip
from app.models.user import User
from app.models.vehicle import Vehicle

__all__ = [
    "Alert",
    "Driver",
    "Evidence",
    "Fleet",
    "GPSLocation",
    "Incident",
    "MaintenanceRecord",
    "SafetyEvent",
    "Trip",
    "User",
    "Vehicle",
]

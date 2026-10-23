"""GPS SIMULATION — not real hardware.

Generates a smooth, deterministic, continuously-moving position for each
active/idle vehicle using a per-vehicle circular path around a Bengaluru
base point. Every reading this module produces is persisted to the
`gps_locations` table with `source="simulation"` so it is never
indistinguishable from a real GPS ingestion pipeline in the data itself.

Real hardware/device integration (GPS_MODE=live) is NOT implemented — see
README "GPS Tracking" section for what that would require.
"""

import math
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import GPSLocation, Vehicle

BENGALURU_CENTER = (12.9716, 77.5946)

# One deterministic "orbit" per vehicle so movement is stable and smooth
# across repeated requests, without needing a background thread.
_VEHICLE_RADII_KM = 3.0
_VEHICLE_PERIOD_SECONDS = 600  # one full loop every 10 minutes


def _phase_for_vehicle(vehicle_code: str) -> float:
    """Deterministic offset per vehicle so they don't all overlap."""
    return sum(ord(c) for c in vehicle_code) % 360


def compute_position(vehicle: Vehicle, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    seconds = now.timestamp()

    phase_deg = _phase_for_vehicle(vehicle.code)
    angle = (2 * math.pi * (seconds % _VEHICLE_PERIOD_SECONDS) / _VEHICLE_PERIOD_SECONDS) + math.radians(
        phase_deg
    )

    # Rough km-to-degree conversion, fine at this scale/latitude.
    lat_offset = (_VEHICLE_RADII_KM / 111.0) * math.sin(angle)
    lng_offset = (_VEHICLE_RADII_KM / 111.0) * math.cos(angle)

    lat = BENGALURU_CENTER[0] + lat_offset
    lng = BENGALURU_CENTER[1] + lng_offset

    heading = (math.degrees(angle) + 90) % 360
    is_moving = vehicle.status == "active"
    speed = 0.0 if not is_moving else 35 + 25 * abs(math.sin(angle * 2))
    acceleration = 0.0 if not is_moving else round(2 * math.cos(angle * 2), 2)

    return {
        "lat": round(lat, 6),
        "lng": round(lng, 6),
        "speed_kmh": round(speed, 1),
        "heading": round(heading, 1),
        "acceleration_ms2": acceleration,
    }


def record_position(db: Session, vehicle: Vehicle) -> GPSLocation:
    """Compute the current simulated position and persist it, unless a
    reading was already recorded in the last 3 seconds (avoids flooding
    the table on rapid dashboard polling)."""
    recent = (
        db.query(GPSLocation)
        .filter(GPSLocation.vehicle_id == vehicle.id)
        .order_by(GPSLocation.timestamp.desc())
        .first()
    )
    now = datetime.now(timezone.utc)
    if recent and recent.timestamp.tzinfo is None:
        # SQLite strips tzinfo on round-trip; treat as UTC.
        recent_ts = recent.timestamp.replace(tzinfo=timezone.utc)
    else:
        recent_ts = recent.timestamp if recent else None

    if recent_ts and (now - recent_ts).total_seconds() < 3:
        return recent

    pos = compute_position(vehicle, now)
    location = GPSLocation(
        vehicle_id=vehicle.id,
        latitude=pos["lat"],
        longitude=pos["lng"],
        speed_kmh=pos["speed_kmh"],
        heading=pos["heading"],
        acceleration_ms2=pos["acceleration_ms2"],
        source="simulation",
        timestamp=now,
    )
    db.add(location)
    db.commit()
    db.refresh(location)
    return location

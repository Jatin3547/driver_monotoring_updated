"""Safety event -> incident -> alert escalation pipeline, with cooldown
based deduplication so one continuous violation (e.g. eyes closed for 30
straight seconds, produced as one detection per periodic tick) creates
ONE incident, not one per tick.

Pipeline:
  DetectionResult (from app/ai/simulator.py or app/ai/vision.py)
    -> SafetyEvent row (always persisted, full history)
    -> if severity == "high" AND no incident of the same type for the
       same driver was created within the cooldown window
       -> Incident row + Alert row (escalation)
       -> Evidence recording scheduled in background daemon thread

Every event/incident/alert produced here carries the detector's own
"source" field ("simulation" or "live") — this module never relabels it.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.ai.base import DetectionResult
from app.core.config import settings
from app.models import Alert, Driver, Incident, SafetyEvent, Trip, Vehicle

logger = logging.getLogger("fleet.safety_engine")

EVENT_LABELS = {
    "drowsiness": "Drowsiness",
    "eye_closure": "Eye closure",
    "yawning": "Yawning",
    "phone_use": "Phone use",
    "distraction": "Distraction",
    "no_presence": "No presence",
}


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def process_detection(
    db: Session, driver: Driver, vehicle: Vehicle, detection: DetectionResult
) -> dict:
    """Persists a SafetyEvent for every detection, and escalates to an
    Incident + Alert only when severity is "high" and the cooldown window
    for this driver+event_type has elapsed. Returns what was created so
    the caller can broadcast it over WebSocket."""

    event = SafetyEvent(
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        event_type=detection.event_type,
        severity=detection.severity,
        confidence=detection.confidence,
        source=detection.source,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(event)
    db.flush()

    result = {"event": event, "incident": None, "alert": None}

    # Only qualifying critical safety events escalate to Incident records requiring evidence
    QUALIFYING_INCIDENT_TYPES = {"drowsiness", "eye_closure", "phone_use", "distraction"}
    if detection.severity != "high" or detection.event_type not in QUALIFYING_INCIDENT_TYPES:
        db.commit()
        return result

    cooldown = timedelta(seconds=settings.ai_event_cooldown_seconds)
    cutoff = datetime.now(timezone.utc) - cooldown

    recent_incident = (
        db.query(Incident)
        .filter(
            Incident.driver_id == driver.id,
            Incident.type == detection.event_type,
        )
        .order_by(Incident.timestamp.desc())
        .first()
    )
    if recent_incident and _aware(recent_incident.timestamp) > cutoff:
        # Still within cooldown for this driver+event_type — don't spam.
        db.commit()
        return result

    label = EVENT_LABELS.get(detection.event_type, detection.event_type)
    active_trip = (
        db.query(Trip)
        .filter(Trip.driver_id == driver.id, Trip.status == "in-progress")
        .first()
    )
    incident = Incident(
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        trip_id=active_trip.id if active_trip else None,
        safety_event_id=event.id,
        type=detection.event_type,
        severity=detection.severity,
        status="open",
        location=f"{vehicle.plate_number} (live GPS not attached to this event)",
        description=f"{label} detected ({detection.source}) at {round(detection.confidence * 100)}% confidence.",
        timestamp=datetime.now(timezone.utc),
    )
    db.add(incident)
    driver.incident_count += 1
    db.flush()

    alert = Alert(
        type=detection.event_type,
        severity=detection.severity,
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        message=f"{label} detected — {driver.name} ({vehicle.plate_number})",
    )
    db.add(alert)
    db.commit()
    db.refresh(incident)
    db.refresh(alert)

    result["incident"] = incident
    result["alert"] = alert

    # ── Automatic evidence recording (fire-and-forget daemon thread) ──────
    # Only attempt for live detections — simulation mode has no real camera buffer.
    if detection.source == "live":
        _schedule_evidence_for_incident(incident, driver, vehicle)

    return result


def _schedule_evidence_for_incident(incident: Incident, driver: Driver, vehicle: Vehicle) -> None:
    """Gathers the camera's rolling pre-event buffer and starts evidence recording.

    Designed to be called synchronously inside process_detection() right after
    the incident is committed.  Evidence collection itself runs in a daemon thread.
    Returns immediately — never blocks the event loop or this call site.
    """
    try:
        # Get the live camera manager (only available when AI_MODE=live)
        from app.ai.factory import get_detector
        detector = get_detector()
        camera_manager = getattr(detector, "camera", None)

        # Collect the rolling pre-event buffer snapshot (5 s)
        pre_event_frames = []
        if camera_manager is not None:
            try:
                pre_event_frames = camera_manager.get_pre_event_frames(seconds=5.0)
            except Exception as buf_exc:
                logger.warning("Could not retrieve pre-event frames: %s", buf_exc)

        from app.services.incident_recorder import schedule_evidence_recording
        schedule_evidence_recording(
            incident_id=incident.id,
            driver_id=driver.id,
            vehicle_id=vehicle.id,
            trip_id=incident.trip_id,
            safety_event_id=incident.safety_event_id,
            pre_event_frames=pre_event_frames,
            camera_manager=camera_manager,
            pre_event_seconds=5.0,
            post_event_seconds=10.0,
        )
    except Exception as exc:
        logger.warning(
            "Failed to schedule evidence recording for incident %s: %s",
            incident.id,
            exc,
        )

"""AI Fleet Management API — application entrypoint.

Endpoints are added by creating a new module under `app/api/routes/` and
registering it inside `app/api/routes/__init__.py`; this file does not
need to change when new domains are added.

On startup this module:
  1. Creates database tables and seeds demo data if the DB is empty
     (app.db.init_db.init_db) — real SQLAlchemy + real SQLite/PostgreSQL.
  2. Starts a background asyncio task that, every 5 seconds while at
     least one WebSocket client is connected:
       - advances the GPS simulation and broadcasts "gps_update"
       - advances the driver-monitoring simulation and broadcasts
         "monitoring_update"
       - runs the active AI detector (simulation by default, or live if
         AI_MODE=live and a camera + optional CV deps are available) for
         a few online drivers, persists SafetyEvents, escalates to
         Incident/Alert via app.services.safety_engine (with cooldown
         deduplication), and broadcasts "safety_event" /
         "incident_created" / "alert_created" accordingly.

Every broadcast payload carries a "source" field ("simulation" or
"live") so simulated data is never indistinguishable from real data.
"""

import asyncio
import contextlib
import logging
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai.factory import (
    active_source,
    get_detector,
    get_driver_status,
    shutdown_detector,
)
from app.api.routes import api_router
from app.core.config import settings
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.gps.simulator import record_position
from app.models import Driver, SafetyEvent, Vehicle
from app.services.evidence_manager import run_retention_cleanup
from app.services.safety_engine import process_detection
from app.services.serializers import (
    alert_to_dict,
    gps_to_dict,
    incident_to_dict,
    safety_event_to_dict,
)
from app.websocket.manager import manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fleet.main")

_ONLINE_STATUSES = {"active", "on-trip"}
_TRACKABLE_STATUSES_EXCLUDE = {"offline"}
_AI_DRIVERS_PER_TICK = 3
_AI_MIN_GAP_SECONDS = 15


async def _broadcast_loop() -> None:
    tick = 0
    while True:
        await asyncio.sleep(0.5)
        tick += 1
        if manager.connection_count == 0:
            continue
        db = SessionLocal()
        try:
            # Retention cleanup every ~5 minutes (600 ticks of 0.5s)
            if tick % 600 == 0:
                try:
                    run_retention_cleanup(db)
                except Exception as cleanup_exc:
                    logger.warning("Periodic retention cleanup: %s", cleanup_exc)

            # --- GPS (runs every 5s = every 10 ticks of 0.5s) ---
            if tick % 10 == 0:
                vehicles = [v for v in db.query(Vehicle).all() if v.status not in _TRACKABLE_STATUSES_EXCLUDE]
                for vehicle in vehicles:
                    loc = record_position(db, vehicle)
                    await manager.broadcast("gps_update", gps_to_dict(loc, vehicle.code))

            online_drivers = [
                d for d in db.query(Driver).all() if d.status in _ONLINE_STATUSES and d.assigned_vehicle_id
            ]

            # --- Monitoring status snapshot ---
            for driver in online_drivers:
                vehicle = db.query(Vehicle).filter(Vehicle.id == driver.assigned_vehicle_id).first()
                if not vehicle:
                    continue
                status = get_driver_status(driver.code, vehicle.code)
                await manager.broadcast("monitoring_update", status)

            # --- AI detection -> safety event -> incident/alert escalation ---
            detector = get_detector()
            target_drivers = (
                [d for d in online_drivers if d.code == "DRV-001"]
                if active_source() == "live"
                else online_drivers[:_AI_DRIVERS_PER_TICK]
            )
            for driver in target_drivers:
                recent = (
                    db.query(SafetyEvent)
                    .filter(SafetyEvent.driver_id == driver.id)
                    .order_by(SafetyEvent.timestamp.desc())
                    .first()
                )
                if recent:
                    recent_ts = recent.timestamp if recent.timestamp.tzinfo else recent.timestamp.replace(
                        tzinfo=timezone.utc
                    )
                    if (datetime.now(timezone.utc) - recent_ts).total_seconds() < _AI_MIN_GAP_SECONDS:
                        continue

                vehicle = db.query(Vehicle).filter(Vehicle.id == driver.assigned_vehicle_id).first()
                if not vehicle:
                    continue

                try:
                    detections = detector.analyze_frame(driver.code)
                except Exception:
                    logger.debug("AI detector unavailable this tick (expected in demo/no-camera mode)")
                    continue

                for detection in detections:
                    result = process_detection(db, driver, vehicle, detection)
                    await manager.broadcast(
                        "safety_event",
                        safety_event_to_dict(result["event"], driver.code, vehicle.code),
                    )
                    if result["incident"] is not None:
                        await manager.broadcast(
                            "incident_created",
                            incident_to_dict(result["incident"], driver, vehicle),
                        )
                    if result["alert"] is not None:
                        await manager.broadcast(
                            "alert_created",
                            alert_to_dict(result["alert"], driver, vehicle),
                        )
        except Exception:
            logger.exception("Broadcast loop tick failed")
        finally:
            db.close()


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database (%s)...", settings.database_url)
    init_db()
    with SessionLocal() as db_cleanup:
        try:
            run_retention_cleanup(db_cleanup)
        except Exception as e:
            logger.warning("Startup retention cleanup: %s", e)

    logger.info("Database ready. AI_MODE=%s GPS_MODE=%s", settings.ai_mode, settings.gps_mode)
    task = asyncio.create_task(_broadcast_loop())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        shutdown_detector()


app = FastAPI(
    title="AI Fleet Management API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

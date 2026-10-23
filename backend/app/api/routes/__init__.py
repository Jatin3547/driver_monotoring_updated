"""Aggregates all versioned API route modules into a single router.

`main.py` only ever imports `api_router` from this package. Adding a new
domain means creating `app/api/routes/<domain>.py` with its own
`APIRouter` and registering it below — `main.py` itself never changes.
"""

from fastapi import APIRouter

from app.api.routes import (
    alerts,
    analytics,
    auth,
    drivers,
    evidence,
    fleet,
    gps,
    health,
    incidents,
    monitoring,
    trips,
    vehicles,
    ws,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(drivers.router, prefix="/drivers", tags=["drivers"])
api_router.include_router(vehicles.router, prefix="/vehicles", tags=["vehicles"])
api_router.include_router(trips.router, prefix="/trips", tags=["trips"])
api_router.include_router(fleet.router, prefix="/fleet", tags=["fleet"])
api_router.include_router(incidents.router, prefix="/incidents", tags=["incidents"])
api_router.include_router(evidence.router, prefix="/evidence", tags=["evidence"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(gps.router, prefix="/gps", tags=["gps"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(ws.router, tags=["websocket"])


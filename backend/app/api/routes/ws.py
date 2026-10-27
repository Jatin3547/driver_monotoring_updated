"""WebSocket endpoint: GET/WS /api/ws

Broadcasts real-time events to every connected client:
  - gps_update       (simulated vehicle positions, source="simulation")
  - monitoring_update (simulated driver monitoring status)
  - safety_event     (new AI detection, simulation or live per its own "source")
  - incident         (new incident created via the REST API)
  - alert            (new alert created via the REST API)

All periodic push data in this project currently comes from the
simulation engines (app/gps/simulator.py, app/ai/simulator.py) — there is
no real hardware/camera feed wired in. Every broadcast payload carries a
"source" field so the frontend (and any inspector) can tell simulated
data from real data at a glance.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.api.deps import MANAGER_ROLES
from app.models import User

from app.websocket.manager import manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")
    email = decode_access_token(token) if token else None
    if not email:
        await websocket.close(code=4401)
        return
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email, User.is_active.is_(True)).first()
        if user is None or user.role not in MANAGER_ROLES:
            await websocket.close(code=4403)
            return
    await manager.connect(websocket)
    try:
        while True:
            # We don't require the client to send anything; just keep the
            # connection open and drain any pings/keepalives it sends.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

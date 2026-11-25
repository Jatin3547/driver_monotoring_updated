"""In-memory state for authenticated browser camera sessions.

This MVP is intentionally single-process. The registry interface keeps session
ownership, expiry, and per-driver event cooldowns explicit for later migration
to a shared session store when the API is horizontally scaled.
"""

import threading
import time
from datetime import datetime, timezone


class BrowserSessionRegistry:
    def __init__(self) -> None:
        self._sessions: dict[str, dict] = {}
        self._expired_sessions: list[tuple[str, dict]] = []
        self._lock = threading.RLock()

    def _collect_expired_locked(self, now: float) -> None:
        for driver_id, session in list(self._sessions.items()):
            last_activity = session["lastFrameAt"] or session["startedAt"]
            if now - last_activity > 20.0:
                self._expired_sessions.append((driver_id, self._sessions.pop(driver_id)))

    def start(self, driver_id: str, driver_code: str, vehicle_code: str) -> dict:
        now = time.monotonic()
        with self._lock:
            self._collect_expired_locked(now)
            for active_id, active_session in list(self._sessions.items()):
                if active_id != driver_id:
                    raise RuntimeError("The single-process AI prototype supports one active browser camera at a time")
            session = self._sessions.get(driver_id)
            if session and self.active(session):
                raise RuntimeError("A camera session is already active for this driver account; reconnect may resume it")
            if session is None:
                session = {
                    "driverCode": driver_code,
                    "vehicleCode": vehicle_code,
                    "startedAt": now,
                    "startedAtIso": datetime.now(timezone.utc).isoformat(),
                    "lastFrameAt": 0.0,
                    "lastFrameAtIso": None,
                    "framesProcessed": 0,
                    "framesRejected": 0,
                    "processingSamplesMs": [],
                    "lastStatus": None,
                    "eventCooldowns": {},
                    "lock": threading.Lock(),
                }
                self._sessions[driver_id] = session
            else:
                session["vehicleCode"] = vehicle_code
                session["lastFrameAt"] = now
            return session

    def get(self, driver_id: str) -> dict | None:
        with self._lock:
            self._collect_expired_locked(time.monotonic())
            session = self._sessions.get(driver_id)
            return session

    def stop(self, driver_id: str) -> dict | None:
        with self._lock:
            return self._sessions.pop(driver_id, None)

    def get_for_driver_code(self, driver_code: str) -> dict | None:
        with self._lock:
            self._collect_expired_locked(time.monotonic())
            for driver_id, session in list(self._sessions.items()):
                if session["driverCode"] == driver_code:
                    return session
        return None

    def active(self, session: dict) -> bool:
        return (time.monotonic() - session["lastFrameAt"]) <= 20.0 if session["lastFrameAt"] else (time.monotonic() - session["startedAt"]) <= 20.0

    def expire_idle(self) -> list[tuple[str, dict]]:
        with self._lock:
            self._collect_expired_locked(time.monotonic())
            expired, self._expired_sessions = self._expired_sessions, []
        return expired

    def list_active(self) -> list[dict]:
        now = time.monotonic()
        with self._lock:
            self._collect_expired_locked(now)
            return [
                {
                    "driverId": session["driverCode"],
                    "vehicleId": session["vehicleCode"],
                    "startedAt": session["startedAtIso"],
                    "lastFrameAt": session["lastFrameAtIso"],
                    "status": "active" if session.get("lastStatus") else "connecting",
                    "aiHealth": (session.get("lastStatus") or {}).get("aiHealth", "starting"),
                    "framesProcessed": session.get("framesProcessed", 0),
                    "processingLatencyMs": (session.get("lastStatus") or {}).get("processingLatencyMs"),
                    "signals": {
                        key: (session.get("lastStatus") or {}).get(key)
                        for key in ("presenceDetected", "eyeState", "drowsinessLevel", "yawnStatus", "phoneUseStatus", "distractionStatus")
                    } if session.get("lastStatus") else None,
                }
                for session in self._sessions.values()
                if (now - (session["lastFrameAt"] or session["startedAt"])) <= 20.0
            ]


browser_sessions = BrowserSessionRegistry()

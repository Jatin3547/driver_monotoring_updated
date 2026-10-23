# AI Fleet Management System

An AI-assisted driver monitoring and fleet management platform: a React/TypeScript
dashboard backed by a FastAPI service, with simulated GPS tracking and simulated
AI driver-safety detection (with a structurally real, optional OpenCV/MediaPipe/YOLO
pipeline for anyone who wants to try it on real hardware).

**Read this before assuming any feature is "real": see [Demo Mode vs. Real Mode](#demo-mode-vs-real-mode) below.**

---

## 1. Project Overview

| Layer | Tech | Status |
|---|---|---|
| Frontend | React + TypeScript + Vite + Tailwind + React Router + React Leaflet + Recharts | Complete, builds cleanly |
| Backend | FastAPI + Uvicorn | Complete, all endpoints tested |
| Database | SQLAlchemy ORM → SQLite (default) or PostgreSQL (optional) | Real, tested with SQLite |
| Auth | JWT (python-jose) + bcrypt password hashing | Real, tested |
| Real-time | WebSocket (`/api/ws`) broadcasting simulated GPS + monitoring updates | Real, tested |
| GPS | Deterministic simulation engine, persisted to DB | **Simulated**, clearly labeled |
| AI driver monitoring | Deterministic simulation engine (default) + optional real OpenCV/MediaPipe/YOLO pipeline (`AI_MODE=live`) | **Simulated by default**; live pipeline is code-complete but **not camera-tested** |

## 2. Architecture

```
Browser (React SPA)
   │  fetch() + WebSocket
   ▼
FastAPI backend (Uvicorn)
   │  SQLAlchemy ORM
   ▼
SQLite (default) or PostgreSQL
```

- The frontend has **one** API architecture: `src/services/api/*.ts`, all going through
  `src/services/api/client.ts` (a single `fetch` wrapper) and `src/services/config.ts`
  (which holds the `VITE_USE_MOCK` switch). There is no second/competing API client.
- Every service function has the same shape whether `VITE_USE_MOCK` is `true` (returns
  built-in mock data, `src/mock/*.ts`) or `false` (calls the real backend). Pages never
  know or care which one is active.
- The backend mirrors this: every route returns data shaped to match the frontend's
  existing TypeScript types exactly (camelCase, human-readable IDs like `DRV-001`), so
  flipping the mock switch requires no frontend code changes.

## 3. Folder Structure

```
/ (project root)
├── src/                     Frontend (React + TS)
│   ├── components/          UI primitives, layout, and per-domain components
│   ├── context/              ThemeContext, AuthContext
│   ├── hooks/                useTheme, useAuth, useDrivers, useAsyncData, ...
│   ├── mock/                 Mock data (used when VITE_USE_MOCK=true)
│   ├── pages/                All 11 route-level pages
│   ├── routes/                AppRoutes.tsx
│   ├── services/
│   │   ├── config.ts          VITE_USE_MOCK / VITE_API_BASE_URL switch
│   │   └── api/                client.ts + one file per domain + authService.ts + healthService.ts
│   ├── types/                  Shared TS types (the frontend/backend contract)
│   └── utils/
├── public/
├── backend/                  Backend (Python + FastAPI)
│   ├── app/
│   │   ├── main.py            App entrypoint: CORS, DB init, WebSocket broadcast loop
│   │   ├── api/
│   │   │   ├── deps.py         get_db, get_current_user
│   │   │   └── routes/         auth, drivers, vehicles, fleet, incidents, alerts, gps, monitoring, analytics, ws, health
│   │   ├── core/               config.py (settings), security.py (JWT + bcrypt)
│   │   ├── db/                 session.py, init_db.py (create tables + seed data)
│   │   ├── models/             SQLAlchemy models (User, Driver, Vehicle, Fleet, Trip, GPSLocation, SafetyEvent, Incident, Alert, MaintenanceRecord)
│   │   ├── schemas/             Pydantic request/response schemas
│   │   ├── services/            serializers.py (ORM → frontend-shaped dicts)
│   │   ├── gps/                 simulator.py — SIMULATED GPS engine
│   │   ├── ai/                  base.py, simulator.py (SIMULATED), vision.py (real pipeline, optional), factory.py
│   │   └── websocket/            manager.py (ConnectionManager)
│   ├── requirements.txt         Core backend dependencies
│   ├── requirements-ai.txt      OPTIONAL: real OpenCV/MediaPipe/YOLO deps
│   └── .env.example
├── package.json / package-lock.json
├── .env.example
└── README.md (this file)
```

## 4–7. Setup (Windows / VS Code)

### 4. Frontend setup

```powershell
npm install
copy .env.example .env
```

### 5–7. Backend setup, Python, virtual environment

Requires **Python 3.12** (3.10+ should also work) on your PATH.

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
copy .env.example .env
```

### 8. PostgreSQL setup (optional — SQLite is the default and needs no setup)

The backend works out of the box with a local SQLite file (`backend/fleet.db`,
auto-created on first run). To use PostgreSQL instead:

1. Install PostgreSQL locally and create a database:
   ```sql
   CREATE DATABASE fleet_db;
   CREATE USER fleet_user WITH PASSWORD 'fleet_password';
   GRANT ALL PRIVILEGES ON DATABASE fleet_db TO fleet_user;
   ```
2. In `backend/.env`, set:
   ```
   DATABASE_URL=postgresql+psycopg2://fleet_user:fleet_password@localhost:5432/fleet_db
   ```
3. Restart the backend — tables and seed data are created automatically on startup
   (`init_db()` runs in `app/main.py`'s lifespan handler).

`psycopg2-binary` is already in `requirements.txt`, so no extra install is needed.

> **Honesty note:** this PostgreSQL path uses the exact same SQLAlchemy code as SQLite
> and there is no reason it shouldn't work, but it was **not tested against a live
> PostgreSQL server** in the environment this project was built in (no Postgres server
> was available there). Please treat it as "implemented, not independently verified"
> until you've run it once yourself.

### 9. Environment variables

**Frontend** (`.env`, project root):
| Variable | Default | Meaning |
|---|---|---|
| `VITE_USE_MOCK` | `true` | `true` = built-in mock data, no backend needed. `false` = call the real backend. |
| `VITE_API_BASE_URL` | `http://127.0.0.1:8000/api` | Backend base URL |

**Backend** (`backend/.env`):
| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./fleet.db` | SQLite by default; swap for a PostgreSQL URL (see above) |
| `SECRET_KEY` | `dev-secret-key-change-me` | JWT signing key — **change this** outside local demo use |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | JWT expiry |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed frontend origins |
| `GPS_MODE` | `simulation` | `simulation` (default) or `live` (not implemented, see below) |
| `AI_MODE` | `simulation` | `simulation` (default) or `live` (real CV pipeline, optional deps + webcam required) |

## 10–11. Running it

**Terminal 1 — backend:**
```powershell
cd backend
venv\Scripts\activate
python -m uvicorn app.main:app --reload
```
Visit `http://127.0.0.1:8000/docs` to confirm it's up (Swagger UI).

**Terminal 2 — frontend:**
```powershell
npm run dev
```
Visit `http://localhost:5173`.

By default `VITE_USE_MOCK=true`, so the frontend works standalone with mock data even
without the backend running. **To see real backend data:** set `VITE_USE_MOCK=false` in
`.env`, restart `npm run dev`, and make sure the backend is running. The Topbar shows a
"Backend Connected" / "Backend Offline" indicator (polls `/api/health` every 15s) so you
can tell at a glance.

**Demo login** (seeded automatically on first backend startup):
```
email:    admin@fleetguard.demo
password: admin123
```

## 12. How to run AI monitoring

- **Default (simulation, no setup):** nothing to do — `AI_MODE=simulation` is the
  default. `GET /api/monitoring/status` and `/api/monitoring/events` are served by
  `app/ai/simulator.py`: deterministic, smoothly time-varying, clearly
  `"source": "simulation"` in every payload.
- **Optional live mode:**
  1. `pip install -r backend/requirements-ai.txt` (OpenCV, MediaPipe, ultralytics —
     large downloads, several hundred MB).
  2. Set `AI_MODE=live` in `backend/.env`.
  3. Restart the backend. `app/ai/factory.py` will try to construct
     `LiveVisionDetector` (real MediaPipe FaceMesh eye-aspect-ratio drowsiness
     detection + YOLO phone-in-hand detection against your default webcam). If
     construction fails (deps missing, no camera), it **automatically falls back to
     simulation** and logs why — it never silently pretends to be live.
  4. **This live path is code-complete but was not tested against a real camera** in
     the environment this project was built in (no webcam available there). Test it
     yourself before relying on it.

## 13. How to run GPS simulation

Also on by default — `GPS_MODE=simulation`, implemented in `app/gps/simulator.py`.
Each trackable vehicle (not `offline`) follows a deterministic circular path around
Bengaluru, computed from real wall-clock time, persisted to the `gps_locations` table
on each request (rate-limited to one write per 3 seconds per vehicle). `GPS_MODE=live`
is **not implemented** — there is no real GPS-hardware ingestion path in this project;
see `app/gps/simulator.py`'s docstring.

## 14. API documentation

Full interactive docs: `http://127.0.0.1:8000/docs` (Swagger) once the backend is running.

Summary of implemented endpoints (all under `/api`):

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | Liveness check |
| POST | `/auth/register` | Create a user |
| POST | `/auth/login` | Form-encoded (`username`, `password`) → JWT |
| GET | `/auth/me` | Protected — requires `Authorization: Bearer <token>` |
| GET | `/fleet/summary` | Fleet-wide KPI counts |
| GET | `/drivers`, `/drivers/{code}` | |
| GET | `/vehicles`, `/vehicles/{code}` | |
| GET | `/incidents` | |
| POST | `/incidents` | Create |
| PATCH | `/incidents/{id}` | Update status/acknowledgement |
| GET | `/alerts` | |
| GET | `/gps/vehicles`, `/gps/vehicles/{code}`, `/gps/history/{code}`, `/gps/locations` (alias) | All simulation-backed |
| GET | `/monitoring/status`, `/monitoring/events` | Simulation-backed by default; `/events` also triggers escalation (see below) |
| GET | `/monitoring/ai-status` | Reports configured vs. actually-active AI source — never claims live unless it genuinely started |
| GET | `/analytics/safety-trend`, `/incident-breakdown`, `/driver-leaderboard`, `/fleet-utilization` | |
| WS | `/ws` | See below |

Only `/auth/me` currently requires a token. The other GET endpoints are intentionally
left open in this build so the dashboard is viewable without forcing a login — see
"Known limitations" below.

## 15. WebSocket documentation

Connect to `ws://127.0.0.1:8000/api/ws`. No handshake payload required. The server
pushes JSON messages shaped `{"type": "...", "payload": {...}}` every ~5 seconds while
at least one client is connected:

- `gps_update` — one message per trackable vehicle, same shape as the GPS REST endpoints
- `monitoring_update` — one message per online driver, same shape as `/monitoring/status`
- `safety_event` — one message per new AI detection (simulation or live), same shape as `/monitoring/events`
- `incident_created` — emitted when a detection escalates to an incident (see "AI event engine" below)
- `alert_created` — emitted alongside every `incident_created`

**Frontend integration:** `src/context/FleetSocketContext.tsx` opens exactly **one**
WebSocket connection for the whole app (only when `VITE_USE_MOCK=false`), with
automatic reconnect (fixed 3s backoff) and a `connecting | connected | reconnecting |
disconnected` status exposed via `useFleetSocketContext()`. Pages subscribe to
individual message types with `useFleetSocketEvent(type, handler)`
(`src/hooks/useFleetSocketEvent.ts`), which auto-unsubscribes on unmount. Currently
wired into: GPS Tracking (live marker patching), Live Monitoring (live status +
event timeline), Dashboard (refetches incidents/alerts on `incident_created` /
`alert_created`), and Incidents (live refresh). The Topbar shows a small "Live
updates / Connecting… / Reconnecting… / Offline" badge.

Tested with both a standalone Python WebSocket client (message types, payload shapes,
reconnect-on-close) and via the frontend build/type-check succeeding against the real
hook code. Browser-based manual click-through was not possible in the sandboxed build
environment (no display) — please do a quick visual pass locally.

### AI event engine (safety_event -> incident -> alert)

`backend/app/services/safety_engine.py` implements the escalation pipeline:

```
DetectionResult (simulator or live vision)
  -> SafetyEvent row (always persisted — full history, every severity)
  -> if severity == "high" AND no incident of the same type for the same
     driver was created within AI_EVENT_COOLDOWN_SECONDS (default 30s)
     -> Incident row (status="open") + Alert row
     -> broadcast safety_event, then incident_created, then alert_created
```

This is what prevents "phone detected for 500 frames" from creating 500 incidents —
tested directly: calling the detection endpoint repeatedly within the cooldown window
produces exactly one incident, confirmed by incident-count staying flat across
back-to-back calls.

## Settings page — system status

The Settings page's **System status** tab shows, live: data mode (demo/connected),
backend reachability, WebSocket connection state, AI mode (configured vs. actually
active), and whether the optional vision dependencies are installed. It never shows
"LIVE" for AI unless `/api/monitoring/ai-status` reports `activeSource: "live"` — if
`AI_MODE=live` is set but the camera/deps aren't available, it correctly shows
"Simulation" with an explanation, matching what `app/ai/factory.py` actually did.
Mode changes (`AI_MODE`, `AI_CAMERA_INDEX`, `DATABASE_URL`) require editing
`backend/.env` and restarting the backend — this is stated on the page itself.

## 16. Troubleshooting

- **"Backend Offline" badge won't go green:** confirm `python -m uvicorn app.main:app --reload`
  is running and `VITE_API_BASE_URL` in `.env` matches its address (default
  `http://127.0.0.1:8000/api`).
- **CORS errors in the browser console:** make sure the frontend is running on port
  `5173` (Vite's default) — only `http://localhost:5173` and `http://127.0.0.1:5173`
  are allowed by default (`CORS_ORIGINS` in `backend/.env`).
- **`ModuleNotFoundError` on backend startup:** make sure the virtual environment is
  activated (`venv\Scripts\activate`) before running `pip install` / `uvicorn`.
- **bcrypt/passlib errors:** this project uses the `bcrypt` package directly (not
  `passlib`) specifically to avoid a known version-incompatibility bug between
  `passlib` and `bcrypt>=4.1`. If you see bcrypt errors, run
  `pip install -r requirements.txt` again to make sure you have exactly `bcrypt==4.2.1`.
- **Database looks empty / stale:** delete `backend/fleet.db` and restart the backend —
  `init_db()` recreates and reseeds it automatically.
- **`email-validator` import error:** run `pip install -r requirements.txt` again; it's
  a required dependency for the auth schemas' `EmailStr` fields.

## 17. Demo mode instructions

This project is designed to be fully demonstrable on a low-end Windows laptop with
**no special hardware**:

- Frontend alone (`VITE_USE_MOCK=true`, the default): no backend needed at all.
- Full stack demo: run backend (SQLite, zero setup) + frontend with `VITE_USE_MOCK=false`.
  GPS and AI monitoring are simulated automatically — no camera, no GPS device, no
  PostgreSQL, no extra pip installs required.
- Everything under "optional" above (PostgreSQL, live AI) is exactly that — optional,
  and clearly separated in code and config from the default demo path.

---

## Demo Mode vs. Real Mode

| Feature | Demo/Simulation (default) | Real Mode |
|---|---|---|
| GPS positions | ✅ Implemented, tested. Deterministic simulated movement, DB-persisted, `source="simulation"` | ❌ Not implemented — no hardware ingestion path exists |
| Driver monitoring status/events | ✅ Implemented, tested. Deterministic simulated signals, `source="simulation"` | ⚠️ Code exists (`app/ai/vision.py`, real MediaPipe/YOLO), gated behind `AI_MODE=live` + optional deps + webcam. **Not camera-tested.** |
| Authentication | ✅ Implemented and tested (real JWT + bcrypt) — this is real either way, not simulated | — |
| WebSocket real-time push | ✅ Implemented and tested — pushes simulated GPS/monitoring data | — |

Nothing in this project claims simulated data is real hardware/camera output. Every
simulated payload includes an explicit `"source": "simulation"` field.

## Known limitations

- The optional live AI pipeline was not tested against a real camera (none available
  in the build environment) — treat it as implemented-but-unverified.
- PostgreSQL was not tested against a live server for the same reason — treat it as
  implemented-but-unverified; SQLite was the database used for all testing referenced
  in this README.
- Most REST GET endpoints are not auth-gated (only `/auth/me` requires a token) — this
  keeps the existing dashboard usable without forcing a login flow, matching the
  original Phase 1 UX. Add `Depends(get_current_user)` to routes if you need to lock
  them down for a real deployment.
- The frontend does not yet subscribe to the WebSocket endpoint — REST polling (via
  each page's existing `useAsyncData`/hook pattern) is what currently drives the UI.
  The backend side is real and tested; wiring a frontend WebSocket client is a
  reasonable next step, not yet done.
- The bundled JS is a single ~900KB chunk (not code-split) — fine for a local demo,
  worth revisiting for a real deployment.

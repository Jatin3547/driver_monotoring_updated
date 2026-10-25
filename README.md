# FLEETGUARD — AI Driver Monitoring & Fleet Management System

An AI-assisted driver monitoring and intelligent fleet management platform featuring:
- **Real-Time Computer Vision Driver Monitoring**: In-cab eye closure (EAR), drowsiness, yawning (MAR), head distraction (3D pose yaw), and mobile phone use detection (YOLOv8) via built-in laptop webcam or DroidCam.
- **Continuous In-Cab Acoustic Buzzer**: High-urgency acoustic alarm that beeps continuously when the driver closes their eyes, is distracted, or uses a phone until they wake up / return attention to the road.
- **Interactive Fleet Operations Dashboard**: Live vehicle telemetry, GPS map tracking, automated incident & alert escalation, and safety leaderboards built with React, Vite, Tailwind CSS, and Leaflet.
- **Incident Video Evidence Pipeline (Phase 3)**: Automatic rolling 5s pre-event + 10s post-event browser webcam recording (~15s clip) for qualifying safety events (Phone use, Drowsiness, Distraction), transcoded to genuine seekable MP4 via FFmpeg, with snapshot capture, SHA-256 cryptographic verification, 500 MB quota enforcement, and 7-day retention janitor.
- **FastAPI Real-Time Backend**: SQLite/PostgreSQL with automatic schema migrations, JWT auth, and WebSocket broadcasting.

---

## 1. System Requirements

- **Operating System**: Windows 10 or 11 (64-bit)
- **Node.js**: `v18.x` or higher (tested on Node 20 & 22)
- **Python**: `3.10`, `3.11`, `3.12`, or `3.13` (64-bit)
- **Hardware**: Any laptop or PC with a standard webcam (or a smartphone running DroidCam over Wi-Fi/USB).

---

## 2. Quick Start on Windows

### Step 1: Clone the Repository
```powershell
git clone https://github.com/Jatin3547/driver_monotoring_updated.git
cd driver_monotoring_updated
```

---

### Step 2: Configure Environment Variables

Create `.env` files from the provided templates:

**Frontend configuration (Project Root):**
```powershell
copy .env.example .env
```
Default `.env` settings:
```env
VITE_USE_MOCK=false
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```
*(Set `VITE_USE_MOCK=true` if you ever want to preview the dashboard standalone without running the backend).*

**Backend configuration (`backend/` directory):**
```powershell
copy backend\.env.example backend\.env
```
*(The defaults in `backend/.env.example` run SQLite out of the box with zero external configuration).*

---

### Step 3: Backend Setup & Installation

Open a terminal in the `backend` folder:

```powershell
cd backend

# Create Python virtual environment
python -m venv venv313

# Activate virtual environment
.\venv313\Scripts\activate

# Upgrade pip
python -m pip install --upgrade pip

# Install all backend dependencies (FastAPI, Uvicorn, OpenCV, MediaPipe, Ultralytics YOLO)
pip install -r requirements.txt
```

*(Tip: Double-clicking `start_backend.bat` or `start_all.bat` from the root will automatically detect your environment, auto-create any missing `.env` files, and launch the server for you).*

---

### Step 4: Verify Your Camera (Optional but Recommended)

With the virtual environment activated, check available cameras on your machine:

```powershell
python check_camera.py
```
- Output will display available indices: `Camera Index 0: AVAILABLE` (usually the built-in laptop webcam).
- To use **DroidCam** from a smartphone over Wi-Fi, open the DroidCam app on your phone and set `AI_CAMERA_INDEX=http://<phone-ip>:4747/video,0,1` in `backend/.env`.

---

### Step 5: Start the Backend Server

From the `backend` directory:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
*(Or double-click `start_backend.bat` in the project root).*

On startup:
- The database (`fleet.db`) automatically runs idempotent schema migrations (`app/db/migrations.py`) ensuring all required columns (including `incidents.trip_id`) and tables are ready.
- Interactive Swagger API Documentation is accessible at **`http://127.0.0.1:8000/docs`**.

---

### Step 6: Frontend Setup & Launch

Open a second terminal in the project root:

```powershell
npm install
npm run dev
```

Visit **`http://localhost:5173`** (or `http://localhost:3000`).

---

## 3. Demo Credentials

If prompted to log in:
- **Email**: `admin@fleetguard.demo`
- **Password**: `admin123`

---

## 4. In-Cab Acoustic Buzzer & AI Monitoring Behavior

Navigate to the **Monitoring** tab:
1. The primary driver card (**Arjun Mehta — DRV-001**) displays your live video feed with bounding boxes and real-time metrics (EAR, MAR, Head Yaw).
2. **Continuous Anti-Sleep Wake-Up Buzzer**:
   - **Eyes Closed / Sleeping**: When you close your eyes for > 0.5s, an urgent in-cab alarm sounds continuously (`BEEP-BEEP! BEEP-BEEP!`) until you open your eyes and wake up.
   - **Phone Usage**: Holding a smartphone up triggers continuous beeps until the phone is lowered.
   - **Distraction**: Turning your head sideways (> 25°) for > 1.5s triggers continuous beeps until you look back at the road.
   - The buzzer silences **instantly** as soon as you are alert.
   - Yawning and background simulated drivers are filtered out and will not trigger the buzzer.

---

## 5. Environment Variables Reference

### Frontend (`.env` in root)
| Variable | Default | Description |
|---|---|---|
| `VITE_USE_MOCK` | `false` | `false` = connect to real backend; `true` = standalone mock preview |
| `VITE_API_BASE_URL` | `http://127.0.0.1:8000/api` | Base URL of the FastAPI backend |

### Backend (`backend/.env`)
| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./fleet.db` | SQLite file location (or PostgreSQL connection string) |
| `SECRET_KEY` | `dev-secret-key-...` | JWT secret key |
| `CORS_ORIGINS` | `http://localhost:3000,...` | Allowed CORS origins for frontend |
| `AI_MODE` | `live` | `live` = real camera inference; `simulation` = synthetic demo data |
| `AI_CAMERA_INDEX` | `0` | Camera index (`0` = laptop webcam, or DroidCam stream URL) |
| `AI_EAR_THRESHOLD` | `0.19` | Eye Aspect Ratio threshold for eye closure detection |
| `AI_PHONE_DETECTION_ENABLED` | `True` | Enable pretrained YOLOv8 phone detection |
| `GPS_MODE` | `simulation` | Deterministic realistic GPS vehicle route simulation |

---

## 6. Running Tests

To verify backend database migrations and ORM integrity:

```powershell
cd backend
.\venv\Scripts\activate
python -m unittest tests.test_migration
```

To run the full suite:
```powershell
python -m unittest discover -s tests
```

To type-check the frontend:
```powershell
npm run build
```

---

## 7. Project Architecture

```
driver_monotoring_updated/
├── backend/
│   ├── app/
│   │   ├── ai/            # MediaPipe FaceLandmarker, YOLOv8 phone detector, CameraManager
│   │   ├── api/routes/    # REST endpoints (monitoring, incidents, gps, auth, fleet)
│   │   ├── core/          # Pydantic configuration & JWT security
│   │   ├── db/            # SQLAlchemy session, init_db.py, migrations.py
│   │   ├── models/        # Database models (Driver, Vehicle, Incident, Evidence, ...)
│   │   ├── websocket/     # WebSocket ConnectionManager for real-time telemetry
│   │   └── main.py        # FastAPI entrypoint & broadcast loop
│   ├── face_landmarker.task # Offline MediaPipe Tasks model
│   ├── yolov8n.pt         # Offline YOLOv8 phone detection model
│   ├── fleet.db           # SQLite database
│   ├── requirements.txt   # Core Python dependencies
│   ├── requirements-ai.txt# OpenCV, MediaPipe, Ultralytics dependencies
│   └── .env.example
├── src/                   # React 18, TypeScript, Tailwind CSS frontend
│   ├── components/        # DriverMonitorCard, UI cards, tables
│   ├── pages/             # MonitoringPage, DashboardPage, GpsTrackingPage
│   ├── services/          # API client and WebSocket hooks
│   └── utils/             # audioAlert.ts (Web Audio API in-cab buzzer)
├── package.json
├── .env.example
├── start_backend.bat      # Windows one-click backend launcher
└── README.md
```

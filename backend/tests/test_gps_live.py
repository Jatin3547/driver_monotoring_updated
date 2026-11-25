"""Authenticated live browser GPS ingestion tests using an isolated SQLite DB."""

import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.api.routes.gps import router
from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import Base
from app.models import Driver, Fleet, GPSLocation, User, Vehicle


class TestLiveGPSIngestion(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        with self.Session() as db:
            fleet = Fleet(name="GPS test fleet", description="isolated")
            db.add(fleet)
            db.flush()
            self.vehicle = Vehicle(
                code="VEH-GPS", plate_number="GPS-001", make="Test", model="Van",
                year=2024, type="van", status="active", fleet_id=fleet.id,
                odometer_km=0, fuel_level=100, next_service_due_km=1000,
            )
            self.user = User(
                email="gps.driver@test.local", hashed_password="unused",
                full_name="GPS Driver", role="driver", is_active=True,
            )
            db.add_all([self.vehicle, self.user])
            db.flush()
            self.vehicle_id = self.vehicle.id
            self.driver = Driver(
                code="DRV-GPS", name="GPS Driver", license_number="TEST-LIC",
                phone="000", email=self.user.email, status="on-trip",
                joined_date=date.today(), total_trips=0, total_distance_km=0,
                incident_count=0, user_id=self.user.id, assigned_vehicle_id=self.vehicle.id,
            )
            db.add(self.driver)
            db.commit()
            self.driver_token = create_access_token(self.user.email)

        test_app = FastAPI()
        test_app.include_router(router, prefix="/gps")

        def override_db():
            with self.Session() as db:
                yield db

        test_app.dependency_overrides[get_db] = override_db
        self.client = TestClient(test_app)
        self.headers = {"Authorization": f"Bearer {self.driver_token}"}

    def tearDown(self):
        self.client.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _payload(self, **overrides):
        data = {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "accuracy": 42.5,
            "speed": 4.0,
            "heading": 91.0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        data.update(overrides)
        return data

    def test_authenticated_update_associates_assigned_vehicle_and_broadcasts(self):
        with patch("app.api.routes.gps.manager.broadcast", new_callable=AsyncMock) as broadcast:
            response = self.client.post("/gps/my-location", json=self._payload(), headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertTrue(body["accepted"])
        location = body["location"]
        self.assertEqual(location["driverId"], "DRV-GPS")
        self.assertEqual(location["vehicleId"], "VEH-GPS")
        self.assertEqual(location["source"], "live")
        self.assertEqual(location["accuracyM"], 42.5)
        self.assertAlmostEqual(location["speedKmh"], 14.4)
        broadcast.assert_awaited_once_with("gps_update", location)

    def test_gps_update_requires_authentication_and_driver_role(self):
        self.assertEqual(self.client.post("/gps/my-location", json=self._payload()).status_code, 401)
        manager_token = create_access_token("manager@test.local")
        with self.Session() as db:
            db.add(User(email="manager@test.local", hashed_password="unused", full_name="Manager", role="fleet_admin", is_active=True))
            db.commit()
        response = self.client.post(
            "/gps/my-location", json=self._payload(),
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        self.assertEqual(response.status_code, 403)

    def test_invalid_coordinates_timestamp_and_vehicle_override_are_rejected(self):
        for bad in (
            {"latitude": 91},
            {"longitude": -181},
            {"timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()},
            {"timestamp": (datetime.now(timezone.utc) - timedelta(minutes=3)).isoformat()},
            {"vehicleId": "VEH-OTHER"},
        ):
            with self.subTest(bad=bad):
                response = self.client.post("/gps/my-location", json=self._payload(**bad), headers=self.headers)
                self.assertEqual(response.status_code, 422)

    def test_server_enforces_update_frequency(self):
        first = self.client.post("/gps/my-location", json=self._payload(), headers=self.headers)
        second = self.client.post("/gps/my-location", json=self._payload(), headers=self.headers)
        self.assertTrue(first.json()["accepted"])
        self.assertFalse(second.json()["accepted"])
        self.assertEqual(second.json()["reason"], "minimum update interval")
        with self.Session() as db:
            self.assertEqual(db.query(GPSLocation).filter_by(source="live").count(), 1)

    def test_live_position_becomes_stale_after_configured_threshold(self):
        old_time = datetime.now(timezone.utc) - timedelta(seconds=settings.gps_stale_after_seconds + 5)
        with self.Session() as db:
            db.add(GPSLocation(
                vehicle_id=self.vehicle_id, latitude=12.9, longitude=77.6,
                speed_kmh=0, heading=0, acceleration_ms2=0,
                accuracy_m=125.0, reported_speed_kmh=None, reported_heading=None,
                source="live", timestamp=old_time,
            ))
            db.commit()
        with patch.object(settings, "gps_mode", "live"):
            response = self.client.get("/gps/my-vehicle", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["gpsStatus"], "stale")
        self.assertEqual(response.json()["source"], "live")

    def test_live_mode_does_not_fall_back_to_simulated_coordinates(self):
        with patch.object(settings, "gps_mode", "live"):
            unavailable = self.client.get("/gps/my-vehicle", headers=self.headers)
        self.assertEqual(unavailable.status_code, 404)
        with patch.object(settings, "gps_mode", "simulation"):
            simulated = self.client.get("/gps/my-vehicle", headers=self.headers)
        self.assertEqual(simulated.status_code, 200)
        self.assertEqual(simulated.json()["source"], "simulation")
        self.assertEqual(simulated.json()["gpsStatus"], "simulated")


if __name__ == "__main__":
    unittest.main()

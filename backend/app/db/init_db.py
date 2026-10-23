"""Creates all tables and seeds demo data.

The seed data intentionally mirrors src/mock/*.mock.ts on the frontend
(same driver names, vehicle plates, Bengaluru GPS coordinates) so the
application looks and behaves consistently whether VITE_USE_MOCK is true
(frontend mock data) or false (this real backend data).

Run directly:  python -m app.db.init_db
Also called automatically on app startup (see app/main.py).
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models import (
    Alert,
    Driver,
    Evidence,
    Fleet,
    Incident,
    SafetyEvent,
    Trip,
    User,
    Vehicle,
)


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def _seed_users(db: Session) -> None:
    if db.query(User).count() > 0:
        return
    db.add(
        User(
            email="admin@fleetguard.demo",
            hashed_password=hash_password("admin123"),
            full_name="Fleet Admin",
            role="fleet_admin",
        )
    )
    db.commit()


def _seed_fleet_vehicles_drivers(db: Session) -> None:
    if db.query(Vehicle).count() > 0:
        return

    fleet = Fleet(name="Bengaluru Primary Fleet", description="Demo fleet seeded on first run")
    db.add(fleet)
    db.flush()

    vehicles_data = [
        ("VEH-001", "KA-01-AB-4521", "Tata", "Pro 6035", 2022, "truck", "active", 118420, 72, 130000),
        ("VEH-002", "KA-03-CD-7812", "Force", "Traveller", 2021, "van", "active", 203110, 45, 210000),
        ("VEH-003", "KA-05-EF-3390", "Ashok Leyland", "Signature", 2019, "truck", "active", 402330, 61, 410000),
        ("VEH-004", "KA-02-GH-1123", "Tata", "Winger", 2023, "van", "idle", 76210, 88, 90000),
        ("VEH-005", "KA-09-IJ-6654", "Tata", "407 Pickup", 2018, "truck", "active", 588400, 33, 595000),
        ("VEH-006", "KA-04-KL-9087", "Ashok Leyland", "Starbus", 2023, "bus", "active", 41200, 55, 50000),
        ("VEH-007", "KA-07-MN-2245", "Honda", "City", 2021, "car", "active", 154880, 67, 160000),
        ("VEH-008", "KA-08-OP-5578", "Mahindra", "Bolero Pickup", 2017, "truck", "maintenance", 712300, 12, 715000),
        ("VEH-009", "KA-06-QR-8834", "Toyota", "Cruiser", 2020, "van", "offline", 267500, 0, 275000),
    ]
    vehicles = {}
    for code, plate, make, model, year, vtype, status, odo, fuel, next_due in vehicles_data:
        v = Vehicle(
            code=code,
            plate_number=plate,
            make=make,
            model=model,
            year=year,
            type=vtype,
            status=status,
            odometer_km=odo,
            fuel_level=fuel,
            last_service_date=date(2026, 8, 1),
            next_service_due_km=next_due,
            fleet_id=fleet.id,
        )
        db.add(v)
        vehicles[code] = v
    db.flush()

    drivers_data = [
        ("DRV-001", "Arjun Mehta", "KA05 20230014521", "+91 98450 12345", "arjun.mehta@fleetmail.com", "on-trip", 92, "VEH-001", 842, 118420, 1),
        ("DRV-002", "Priya Nair", "KA03 20210098231", "+91 98801 22334", "priya.nair@fleetmail.com", "on-trip", 78, "VEH-002", 1204, 203110, 5),
        ("DRV-003", "Rohit Sharma", "KA01 20190045213", "+91 99001 88765", "rohit.sharma@fleetmail.com", "active", 88, "VEH-003", 2310, 402330, 3),
        ("DRV-004", "Sneha Reddy", "KA09 20220076412", "+91 97401 55678", "sneha.reddy@fleetmail.com", "off-duty", 95, "VEH-004", 512, 76210, 0),
        ("DRV-005", "Vikram Singh", "KA02 20180032190", "+91 98220 99887", "vikram.singh@fleetmail.com", "on-trip", 64, "VEH-005", 3140, 588400, 11),
        ("DRV-006", "Anita Desai", "KA04 20230011009", "+91 90080 44223", "anita.desai@fleetmail.com", "active", 90, "VEH-006", 298, 41200, 1),
        ("DRV-007", "Karan Malhotra", "KA07 20200065512", "+91 99860 33112", "karan.malhotra@fleetmail.com", "suspended", 42, None, 1876, 298700, 19),
        ("DRV-008", "Meera Iyer", "KA06 20210054332", "+91 98457 66211", "meera.iyer@fleetmail.com", "on-trip", 85, "VEH-007", 967, 154880, 2),
        ("DRV-009", "Suresh Kumar", "KA08 20170021456", "+91 90350 77441", "suresh.kumar@fleetmail.com", "active", 73, "VEH-008", 4021, 712300, 8),
    ]
    for code, name, lic, phone, email, status, score, vcode, trips, dist, inc in drivers_data:
        d = Driver(
            code=code,
            name=name,
            license_number=lic,
            phone=phone,
            email=email,
            status=status,
            safety_score=score,
            joined_date=date(2021, 1, 1),
            total_trips=trips,
            total_distance_km=dist,
            incident_count=inc,
            assigned_vehicle_id=vehicles[vcode].id if vcode else None,
        )
        db.add(d)
    db.commit()


def _seed_trips(db: Session) -> None:
    if db.query(Trip).count() > 0:
        return

    d1 = db.query(Driver).filter(Driver.code == "DRV-001").first()
    v1 = db.query(Vehicle).filter(Vehicle.code == "VEH-001").first()
    d5 = db.query(Driver).filter(Driver.code == "DRV-005").first()
    v5 = db.query(Vehicle).filter(Vehicle.code == "VEH-005").first()
    now = datetime.now(timezone.utc)

    if d1 and v1:
        db.add(
            Trip(
                driver_id=d1.id,
                vehicle_id=v1.id,
                start_time=now - timedelta(hours=1, minutes=15),
                start_location="Electronic City Hub",
                end_location="Hebbal Logistics Center",
                distance_km=34.5,
                status="in-progress",
            )
        )

    if d5 and v5:
        db.add(
            Trip(
                driver_id=d5.id,
                vehicle_id=v5.id,
                start_time=now - timedelta(hours=2, minutes=40),
                start_location="Outer Ring Road Hub",
                end_location="Whitefield Depot",
                distance_km=52.0,
                status="in-progress",
            )
        )
    db.commit()


def _seed_incidents_alerts(db: Session) -> None:
    if db.query(Incident).count() > 0:
        return

    driver = db.query(Driver).filter(Driver.code == "DRV-005").first()
    vehicle = db.query(Vehicle).filter(Vehicle.code == "VEH-005").first()
    trip = db.query(Trip).filter(Trip.driver_id == (driver.id if driver else "")).first()
    if not driver or not vehicle:
        return

    event = SafetyEvent(
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        event_type="drowsiness",
        severity="high",
        confidence=0.91,
        source="simulation",
        timestamp=datetime.now(timezone.utc),
    )
    db.add(event)
    db.flush()

    incident = Incident(
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        trip_id=trip.id if trip else None,
        safety_event_id=event.id,
        type="drowsiness",
        severity="high",
        status="open",
        location="Outer Ring Road, Bengaluru",
        description="Sustained eye closure detected at highway speed (simulated demo event).",
    )
    db.add(incident)
    db.flush()

    # Seed evidence metadata linked to this high-severity incident
    evidence = Evidence(
        incident_id=incident.id,
        safety_event_id=event.id,
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        trip_id=trip.id if trip else None,
        file_path="data/evidence/INC-501_evidence.mp4",
        file_type="video/mp4",
        file_size_bytes=4194304,
        duration_seconds=8.0,
        pre_event_seconds=5.0,
        post_event_seconds=3.0,
        retention_days=30,
        is_protected=True,
    )
    db.add(evidence)

    alert = Alert(
        type="drowsiness",
        severity="high",
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        message=f"Critical drowsiness detected — {driver.name} ({vehicle.plate_number})",
    )
    db.add(alert)
    db.commit()


def seed_all() -> None:
    db = SessionLocal()
    try:
        _seed_users(db)
        _seed_fleet_vehicles_drivers(db)
        _seed_trips(db)
        _seed_incidents_alerts(db)
    finally:
        db.close()


def init_db() -> None:
    create_tables()
    seed_all()


if __name__ == "__main__":
    init_db()
    print("Database initialized and seeded.")

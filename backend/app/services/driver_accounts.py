"""Idempotent linking of existing Driver records to User login accounts.

Passwords for newly created driver users are unique per email (HMAC of the
app secret) — never a shared default. Existing users are linked in place
and their passwords are never reset.
"""

from __future__ import annotations

import hashlib
import hmac
import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models import Driver, User

logger = logging.getLogger("fleet.db.driver_accounts")

MANAGER_ROLES = {"fleet_admin", "admin", "manager"}


def driver_bootstrap_password(email: str) -> str:
    """Deterministic unique password used only when creating a new driver user."""
    digest = hmac.new(
        settings.secret_key.encode("utf-8"),
        f"driver-login:{email.strip().lower()}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"Drv-{digest[:20]}"


def link_driver_user_accounts(db: Session) -> int:
    """Create missing driver-role users and set Driver.user_id.

    Safe to rerun: does not duplicate users, does not reset passwords, and
    will not attach a manager account to a driver record.
    Returns the number of driver rows whose user_id was written this run.
    """
    linked = 0
    drivers = db.query(Driver).order_by(Driver.code).all()
    for driver in drivers:
        if driver.user_id:
            existing = db.query(User).filter(User.id == driver.user_id).first()
            if existing:
                continue
            logger.warning("Driver %s had a dangling user_id; re-linking", driver.code)
            driver.user_id = None

        user = db.query(User).filter(User.email == driver.email).first()
        if user is None:
            user = User(
                email=driver.email,
                hashed_password=hash_password(driver_bootstrap_password(driver.email)),
                full_name=driver.name,
                role="driver",
            )
            db.add(user)
            db.flush()
        else:
            if user.role in MANAGER_ROLES:
                logger.warning(
                    "Skipping link for driver %s: email %s belongs to a manager account",
                    driver.code,
                    driver.email,
                )
                continue
            if user.role != "driver":
                user.role = "driver"

        other = (
            db.query(Driver)
            .filter(Driver.user_id == user.id, Driver.id != driver.id)
            .first()
        )
        if other:
            logger.warning(
                "Skipping link for driver %s: user %s already linked to %s",
                driver.code,
                user.email,
                other.code,
            )
            continue

        driver.user_id = user.id
        linked += 1

    db.commit()
    return linked

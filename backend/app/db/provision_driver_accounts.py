"""Link driver records to login accounts. Safe to rerun.

Usage (from the backend directory):

    python -m app.db.provision_driver_accounts
    python -m app.db.provision_driver_accounts --print-credentials
"""

from __future__ import annotations

import argparse

from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models import Driver
from app.services.driver_accounts import driver_bootstrap_password, link_driver_user_accounts


def main() -> None:
    parser = argparse.ArgumentParser(description="Link Driver records to User accounts")
    parser.add_argument(
        "--print-credentials",
        action="store_true",
        help="Print bootstrap passwords for accounts that use the HMAC login secret. "
        "Only valid for accounts created by this linker (existing passwords are never reset).",
    )
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        created_links = link_driver_user_accounts(db)
        print(f"Driver account linking complete ({created_links} new links this run).")
        if args.print_credentials:
            rows = (
                db.query(Driver)
                .filter(Driver.user_id.isnot(None))
                .order_by(Driver.code)
                .all()
            )
            print("email\tbootstrap_password\tdriver_code")
            for driver in rows:
                print(
                    f"{driver.email}\t{driver_bootstrap_password(driver.email)}\t{driver.code}"
                )
    finally:
        db.close()


if __name__ == "__main__":
    main()

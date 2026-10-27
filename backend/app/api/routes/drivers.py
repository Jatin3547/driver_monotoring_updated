"""Driver endpoints with role-based access control.

Fleet managers (fleet_admin/admin/manager) can list all drivers and fetch any
driver by code.

Driver-role users can only fetch their own driver record via GET /{driver_code}
(the code must match their linked driver account). The full list endpoint
(/api/drivers) is manager-only.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import MANAGER_ROLES, get_current_user, get_db, require_fleet_admin
from app.models import Driver, User
from app.services.serializers import driver_to_dict

router = APIRouter()


@router.get("")
def list_drivers(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_fleet_admin),
):
    """List all drivers — fleet managers only."""
    drivers = db.query(Driver).all()
    return [driver_to_dict(d) for d in drivers]


@router.get("/{driver_code}")
def get_driver(
    driver_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single driver by code.

    Fleet managers can fetch any driver.
    Driver-role users can only fetch their own record.
    """
    driver = db.query(Driver).filter(Driver.code == driver_code).first()
    if not driver:
        raise HTTPException(status_code=404, detail=f"Driver '{driver_code}' not found")

    # Fleet managers always have access
    if current_user.role in MANAGER_ROLES:
        return driver_to_dict(driver)

    # Drivers may only access their own record
    if current_user.role == "driver":
        if driver.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You may only access your own driver record.",
            )
        return driver_to_dict(driver)

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied.",
    )

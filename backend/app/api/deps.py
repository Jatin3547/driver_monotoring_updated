"""Shared FastAPI dependencies: DB session + current-user extraction from a
JWT bearer token. Import `get_db` and `get_current_user` from here in any
route that needs them.

Role helpers
------------
require_fleet_admin  – raises 403 if caller is not fleet_admin / admin / manager
get_current_driver   – resolves the Driver record linked to a driver-role user;
                       raises 403 if caller is not a driver or has no linked record
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import Driver, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

MANAGER_ROLES = {"fleet_admin", "admin", "manager"}
_MANAGER_ROLES = MANAGER_ROLES


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_exception

    email = decode_access_token(token)
    if email is None:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    if not token:
        return None
    email = decode_access_token(token)
    if not email:
        return None
    return db.query(User).filter(User.email == email).first()


def require_fleet_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency — raises 403 unless the authenticated user is a fleet manager/admin."""
    if current_user.role not in _MANAGER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Fleet manager access required.",
        )
    return current_user


def get_current_driver(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Driver:
    """Dependency — resolves the Driver record for an authenticated driver-role user.

    Raises 403 if the user is not role=driver, or if no Driver record is linked
    to their account (i.e. they have a driver user account but no driver record).
    """
    if current_user.role != "driver":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Driver access required.",
        )
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
    if driver is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No driver profile is linked to this account.",
        )
    return driver

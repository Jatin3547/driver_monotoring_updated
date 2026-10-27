"""Real JWT authentication: register, login, and protected endpoints.

This is a genuine, working implementation (bcrypt password hashing, signed
JWTs) suitable for a local/demo deployment. It is intentionally simple:
no refresh tokens, no email verification, no password-reset flow — those
are reasonable Phase 3+ additions, not claimed here.

Endpoints
---------
POST /register        – create a new user (role is always "registered";
                        clients cannot self-assign manager/admin)
POST /login           – obtain a JWT bearer token (optional OAuth2 scope
                        "manager" or "driver" to bind the login portal)
GET  /me              – get the current authenticated user
GET  /me/driver-profile  – get the Driver record linked to the logged-in
                           driver-role user (403 if not a driver)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import MANAGER_ROLES, get_current_driver, get_current_user, get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models import Driver, User
from app.schemas.auth import Token, UserOut, UserRegister
from app.services.serializers import driver_to_dict

router = APIRouter()


def _user_to_out(user: User, db: Session) -> UserOut:
    """Build UserOut, attaching driver_code if the user has role=driver."""
    driver_code: str | None = None
    if user.role == "driver":
        drv = db.query(Driver).filter(Driver.user_id == user.id).first()
        if drv:
            driver_code = drv.code
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        driver_code=driver_code,
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="A user with this email already exists")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role="registered",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_to_out(user, db)


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2PasswordRequestForm uses "username" as the field name; the
    # frontend sends the user's email in that field.
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not user.is_active or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    requested_scopes = {s.lower() for s in form_data.scopes}
    if "driver" in requested_scopes and user.role != "driver":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not a driver login.",
        )
    if "manager" in requested_scopes and user.role not in MANAGER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not a fleet manager login.",
        )

    token = create_access_token(subject=user.email)
    return Token(access_token=token, user=_user_to_out(user, db))


@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _user_to_out(current_user, db)


@router.get("/me/driver-profile")
def read_driver_profile(driver: Driver = Depends(get_current_driver)):
    """Returns the full Driver record for the authenticated driver-role user.
    Only accessible by users with role='driver' whose account is linked to
    a Driver record. Fleet managers must use /api/drivers/{code} instead.
    """
    return driver_to_dict(driver)

from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str

    class Config:
        extra = "forbid"


class UserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: str
    # Present only for driver-role users: the linked Driver's code (e.g. "DRV-001")
    driver_code: str | None = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

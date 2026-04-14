from pydantic import BaseModel, EmailStr
from typing import Optional


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AdminUserOut(BaseModel):
    id: str
    email: str
    full_name: str
    is_superadmin: bool

    model_config = {"from_attributes": True}

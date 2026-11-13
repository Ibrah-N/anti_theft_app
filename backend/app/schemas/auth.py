# app/schemas/auth.py

from datetime import datetime

from pydantic import BaseModel, EmailStr


# ── Register ──────────────────────────────────────────────────────────────────
class UserRegister(BaseModel):
    email: EmailStr
    phone: str | None = None
    full_name: str
    password: str


# ── Login ─────────────────────────────────────────────────────────────────────
class UserLogin(BaseModel):
    email: EmailStr
    password: str


# ── Token response ────────────────────────────────────────────────────────────
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ── User response (never expose password) ────────────────────────────────────
class UserResponse(BaseModel):
    id: int
    email: str
    phone: str | None
    full_name: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}

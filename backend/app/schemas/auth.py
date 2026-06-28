# app/schemas/auth.py

from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

# ── Register ──────────────────────────────────────────────────────────────────
class UserRegister(BaseModel):
    email:     EmailStr
    phone:     Optional[str] = None
    full_name: str
    password:  str

# ── Login ─────────────────────────────────────────────────────────────────────
class UserLogin(BaseModel):
    email:    EmailStr
    password: str

# ── Token response ────────────────────────────────────────────────────────────
class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"

# ── User response (never expose password) ────────────────────────────────────
class UserResponse(BaseModel):
    id:          int
    email:       str
    phone:       Optional[str]
    full_name:   str
    is_active:   bool
    is_verified: bool
    created_at:  datetime

    model_config = {"from_attributes": True}
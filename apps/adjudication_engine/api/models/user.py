from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    admin = "admin"
    claims_officer = "claims_officer"
    viewer = "viewer"


class UserCreate(BaseModel):
    email: EmailStr
    password:  str = Field(min_length=8)
    full_name: str = Field(min_length=2)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name:  str
    role: UserRole
    is_active:  bool
    created_at: datetime
    image: Optional[str] = None


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class OAuthUserData(BaseModel):
    email: EmailStr
    full_name:   Optional[str] = None
    provider: str # "google" | "microsoft"
    provider_id: str
    image: Optional[str] = None
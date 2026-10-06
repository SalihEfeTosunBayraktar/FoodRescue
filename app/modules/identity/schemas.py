"""Request/response contracts (Pydantic).

Ders notu: şemalar API'nin "sözleşmesi"dir. Veritabanı modelini (User) doğrudan dışarı
vermeyiz; aksi halde password_hash gibi alanlar sızar. Girdi doğrulaması da burada yapılır.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.identity.models import AccountStatus, UserRole

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SELF_REGISTER_ROLES = (UserRole.DONOR, UserRole.BENEFICIARY, UserRole.SHELTER)


class RegisterIn(BaseModel):
    email: str = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=150)
    role: UserRole
    phone: str | None = Field(default=None, max_length=30)
    organization_name: str | None = Field(default=None, max_length=200)
    license_number: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=300)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not _EMAIL_RE.match(value):
            raise ValueError("invalid email")
        return value

    @model_validator(mode="after")
    def _organization_fields(self) -> "RegisterIn":
        if self.role in (UserRole.DONOR, UserRole.SHELTER):
            missing = [n for n in ("organization_name", "license_number", "address") if not getattr(self, n)]
            if missing:
                raise ValueError(f"required for organizations: {', '.join(missing)}")
        if self.role == UserRole.DONOR and (self.latitude is None or self.longitude is None):
            raise ValueError("donors must provide a map location")
        return self


class LoginIn(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: UserRole
    status: AccountStatus
    phone: str | None
    organization_name: str | None
    license_number: str | None
    address: str | None
    latitude: float | None
    longitude: float | None
    review_note: str | None
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ReviewIn(BaseModel):
    decision: Literal["APPROVE", "REJECT"]
    note: str | None = Field(default=None, max_length=500)


class ReasonIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500)

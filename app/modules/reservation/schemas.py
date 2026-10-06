from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.modules.reservation.models import ReservationStatus


class ReservationCreate(BaseModel):
    food_id: int
    portions: int = Field(default=1, ge=1, le=10)
    note: str | None = Field(default=None, max_length=300)


class VerifyIn(BaseModel):
    """`code` is either the 6-digit PIN or the QR payload ("FR:<token>" or the bare token)."""

    code: str = Field(min_length=4, max_length=80)

    @field_validator("code")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class MyReservationOut(BaseModel):
    """What the beneficiary sees: includes the secrets (QR + PIN)."""

    id: int
    food_id: int
    food_title: str
    donor_name: str
    pickup_address: str
    latitude: float
    longitude: float
    portions: int
    status: ReservationStatus
    pin: str | None
    qr_svg: str | None
    created_at: datetime
    expires_at: datetime
    collected_at: datetime | None


class DonorReservationOut(BaseModel):
    """What the donor sees: no secrets, only a privacy-safe label."""

    id: int
    food_id: int
    food_title: str
    portions: int
    status: ReservationStatus
    beneficiary_label: str
    created_at: datetime
    expires_at: datetime
    collected_at: datetime | None


class VerifyOut(BaseModel):
    reservation_id: int
    food_title: str
    portions: int
    beneficiary_label: str
    collected_at: datetime

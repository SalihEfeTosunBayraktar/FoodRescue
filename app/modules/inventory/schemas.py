from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.clock import ensure_utc
from app.modules.inventory.models import FoodCategory, FoodStatus, StorageCondition


class FoodCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    category: FoodCategory = FoodCategory.HUMAN
    storage: StorageCondition = StorageCondition.HOT
    portions_total: int = Field(ge=1, le=500)
    max_per_person: int = Field(default=2, ge=1, le=10)
    pickup_until: datetime
    hygiene_confirmed: bool
    address: str | None = Field(default=None, max_length=300)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @field_validator("pickup_until")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        return ensure_utc(value)


class FoodUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    pickup_until: datetime | None = None

    @field_validator("pickup_until")
    @classmethod
    def _utc(cls, value: datetime | None) -> datetime | None:
        return ensure_utc(value) if value else None


class FoodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    donor_id: int
    donor_name: str
    title: str
    description: str | None
    category: FoodCategory
    storage: StorageCondition
    portions_total: int
    portions_left: int
    max_per_person: int
    pickup_until: datetime
    address: str
    latitude: float
    longitude: float
    photo_url: str | None
    status: FoodStatus
    is_available: bool
    created_at: datetime
    distance_km: float | None = None

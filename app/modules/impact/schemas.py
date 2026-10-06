from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.impact.models import ComplaintStatus


class SummaryOut(BaseModel):
    portions_rescued: int
    pickups_completed: int
    active_donors: int
    foods_available: int


class DonorImpactOut(BaseModel):
    portions_rescued: int
    pickups_completed: int
    portions_waiting: int
    foods_published: int


class ComplaintIn(BaseModel):
    reservation_id: int
    reason: str = Field(min_length=10, max_length=1000)


class ComplaintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reservation_id: int
    donor_id: int
    donor_name: str
    reason: str
    status: ComplaintStatus
    resolution_note: str | None
    created_at: datetime


class ResolveIn(BaseModel):
    action: Literal["RESOLVE", "DISMISS"]
    note: str | None = Field(default=None, max_length=500)


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: int | None
    action: str
    entity_type: str
    entity_id: int
    detail: str | None
    created_at: datetime


class OverviewOut(BaseModel):
    pending_accounts: int
    open_complaints: int
    users_by_role: dict[str, int]
    reservations_by_status: dict[str, int]

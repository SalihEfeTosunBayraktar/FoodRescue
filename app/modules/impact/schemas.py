from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.impact.models import ComplaintStatus


# Ana sayfadaki herkese açık sayaçlar. Kişisel veri içermez.
class SummaryOut(BaseModel):
    portions_rescued: int
    pickups_completed: int
    active_donors: int
    foods_available: int


# İşletmenin kendi panosu: teslim edilen ve bekleyen porsiyonlar.
class DonorImpactOut(BaseModel):
    portions_rescued: int
    pickups_completed: int
    portions_waiting: int
    foods_published: int


# Şikâyet girdisi: hangi teslim ve ne oldu.
class ComplaintIn(BaseModel):
    reservation_id: int
    # En az 10 karakter: tek kelimelik anlamsız şikâyetleri ayıklar.
    reason: str = Field(min_length=10, max_length=1000)


# Yönetici için şikâyet yanıtı.
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


# Yönetici kararı: haklı bul (RESOLVE) veya reddet (DISMISS), isteğe bağlı notla.
class ResolveIn(BaseModel):
    action: Literal["RESOLVE", "DISMISS"]
    note: str | None = Field(default=None, max_length=500)


# Denetim satırı yanıtı.
class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: int | None
    action: str
    entity_type: str
    entity_id: int
    detail: str | None
    created_at: datetime


# Yönetici panosundaki sayaçlar ve dağılımlar (sözlük: rol -> adet).
class OverviewOut(BaseModel):
    pending_accounts: int
    open_complaints: int
    users_by_role: dict[str, int]
    reservations_by_status: dict[str, int]

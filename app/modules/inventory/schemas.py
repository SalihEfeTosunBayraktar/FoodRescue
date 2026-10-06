from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.clock import ensure_utc
from app.modules.inventory.models import FoodCategory, FoodStatus, StorageCondition


# İlan oluşturma girdisi. Kurallar iki katmanda uygulanır: biçim kuralları burada (Pydantic), iş
# kuralları serviste (örn. 24 saat sınırı).
class FoodCreate(BaseModel):
    # Başlık 3-200 karakter.
    title: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    category: FoodCategory = FoodCategory.HUMAN
    storage: StorageCondition = StorageCondition.HOT
    # 1-500 arası: sıfır veya milyonluk porsiyon anlamsız.
    portions_total: int = Field(ge=1, le=500)
    max_per_person: int = Field(default=2, ge=1, le=10)
    # Tarih saat dilimli (ISO 8601) gelir; aşağıdaki doğrulayıcı UTC'ye çevirir.
    pickup_until: datetime
    # Alan zorunlu bool: kutu işaretli gönderilmezse servis reddeder.
    hygiene_confirmed: bool
    address: str | None = Field(default=None, max_length=300)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    # Gelen tarihi UTC'ye normalleştirir.
    @field_validator("pickup_until")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        return ensure_utc(value)


# Güncelleme: yalnızca değiştirilebilir alanlar var. Porsiyon sayısı bilerek yok: stok yalnızca
# rezervasyonlarla değişir, elle değiştirilirse sayaç tutarsızlaşır.
class FoodUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    pickup_until: datetime | None = None

    # Aynı normalleştirme; güncellemede alan isteğe bağlı olduğu için None da kabul edilir.
    @field_validator("pickup_until")
    @classmethod
    def _utc(cls, value: datetime | None) -> datetime | None:
        return ensure_utc(value) if value else None


# Yanıt şeması. `distance_km` yalnızca konum verilirse dolar (isteğe bağlı alan).
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
    # Ön yüz 'alınabilir mi?' kararını kendisi vermez; hesaplanmış sonucu sunucudan alır (tek doğru
    # kaynak).
    is_available: bool
    created_at: datetime
    distance_km: float | None = None

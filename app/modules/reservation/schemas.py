from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.modules.reservation.models import ReservationStatus


# Rezervasyon isteği. Porsiyon üst sınırı (ilanın kişi başı limiti) serviste, ilanı okuyarak
# denetlenir.
class ReservationCreate(BaseModel):
    food_id: int
    # Varsayılan 1 porsiyon.
    portions: int = Field(default=1, ge=1, le=10)
    note: str | None = Field(default=None, max_length=300)


# Teslim doğrulama girdisi: tek alan. İşletme PIN'i de QR içeriğini de aynı kutuya yazar/okutur;
# servis hangisi olduğunu biçimden anlar.
class VerifyIn(BaseModel):
    """`code` is either the 6-digit PIN or the QR payload ("FR:<token>" or the bare token)."""

    # En az 4, en çok 80 karakter.
    code: str = Field(min_length=4, max_length=80)

    # Başındaki ve sonundaki boşlukları kırpar (elle girişte sık yapılan hata).
    @field_validator("code")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


# KENDİ rezervasyonum: PIN ve QR gibi SIRLAR içerir; yalnızca sahibine gösterilir.
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
    # Yalnızca bekleyen rezervasyonda dolu; teslimden sonra sır artık gereksiz olduğundan None.
    pin: str | None
    # QR kodun SVG metni; ön yüz bunu <img> içinde gösterir (img içindeki SVG betik çalıştıramaz,
    # güvenlidir).
    qr_svg: str | None
    created_at: datetime
    expires_at: datetime
    collected_at: datetime | None


# Bağışçının gördüğü görünüm: SIR YOK (PIN ve QR alanları bilerek eksik). Aynı veri iki farklı rol
# için iki farklı şemayla sunulur.
class DonorReservationOut(BaseModel):
    """What the donor sees: no secrets, only a privacy-safe label."""

    id: int
    food_id: int
    food_title: str
    portions: int
    status: ReservationStatus
    # Yararlanıcının tam adı yerine 'Ali Y.' gibi kısaltılmış etiket (gizlilik).
    beneficiary_label: str
    created_at: datetime
    expires_at: datetime
    collected_at: datetime | None


# Teslim onayı özeti: işletmeye neyi teslim ettiğini gösterir.
class VerifyOut(BaseModel):
    reservation_id: int
    food_title: str
    portions: int
    beneficiary_label: str
    collected_at: datetime

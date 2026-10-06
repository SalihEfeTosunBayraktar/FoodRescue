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

# Basit e-posta kalıbı: @ işareti ve noktalı alan adı. Tam doğrulama mümkün değildir; gerçek kanıt,
# adrese posta gönderip tıklatmaktır (bu projede yok).
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# Kayıt ekranından seçilebilecek roller. ADMIN burada yok: kimse kendini yönetici yapamaz.
SELF_REGISTER_ROLES = (UserRole.DONOR, UserRole.BENEFICIARY, UserRole.SHELTER)


# Pydantic modeli = girdi sözleşmesi. FastAPI, istek gövdesini bu kurallara göre otomatik doğrular;
# geçersizse 422 döner ve servis koduna hiç ulaşılmaz.
class RegisterIn(BaseModel):
    # Field: alan kısıtları (uzunluk, aralık). Sınırsız uzunluktaki girdi hem veritabanını hem
    # belleği zorlar.
    email: str = Field(max_length=255)
    # Parola en az 8 karakter. Üst sınır (128) çok uzun girdiyle hash hesabını yavaşlatma
    # saldırısını önler.
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=150)
    # Enum olduğu için 'HACKER' gibi geçersiz bir rol otomatik reddedilir.
    role: UserRole
    phone: str | None = Field(default=None, max_length=30)
    organization_name: str | None = Field(default=None, max_length=200)
    license_number: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=300)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    # Alan doğrulayıcı: tek alanı kontrol eder ve düzeltebilir (küçük harfe çevirip boşlukları
    # kırpar). Böylece 'Ali@x.com' ile 'ali@x.com' aynı hesap sayılır.
    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        # ValueError fırlatmak Pydantic'e 'bu girdi geçersiz' demenin yoludur.
        if not _EMAIL_RE.match(value):
            raise ValueError("invalid email")
        return value

    # Model doğrulayıcı: ALANLAR ARASI kurallar burada kontrol edilir (tek tek alan doğrulayıcılar
    # bunu göremez).
    @model_validator(mode="after")
    def _organization_fields(self) -> "RegisterIn":
        # Kurum rolleri için ek zorunlu alanlar.
        if self.role in (UserRole.DONOR, UserRole.SHELTER):
            missing = [n for n in ("organization_name", "license_number", "address") if not getattr(self, n)]
            if missing:
                raise ValueError(f"required for organizations: {', '.join(missing)}")
        # Bağışçı haritada görünecek, bu yüzden konum zorunlu.
        if self.role == UserRole.DONOR and (self.latitude is None or self.longitude is None):
            raise ValueError("donors must provide a map location")
        return self


# Giriş isteği. Burada parola uzunluğu kontrol edilmez; yanlış parola ile kısa parola aynı hatayı
# almalı.
class LoginIn(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        return value.strip().lower()


# Yanıt şeması: dışarı verilecek alanların beyaz listesi. `password_hash` bilerek yok. Veritabanı
# modelini doğrudan döndürmek bu tür sızıntılara yol açar.
class UserOut(BaseModel):
    # from_attributes: Pydantic, SQLAlchemy nesnesinin alanlarını doğrudan okuyabilsin.
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


# Giriş yanıtı: bilet (access_token) ve kullanıcı bilgisi.
class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ReviewIn(BaseModel):
    # Literal: yalnızca bu iki metin kabul edilir.
    decision: Literal["APPROVE", "REJECT"]
    note: str | None = Field(default=None, max_length=500)


# Askıya alma gerekçesi zorunludur: denetim kaydında 'neden' sorusu cevapsız kalmasın.
class ReasonIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500)

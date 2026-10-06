"""Identity data model: one `users` table for every role.

Ders notu (veritabanı): tek tabloda rol ayrımı ("single table inheritance") küçük sistemlerde
basittir. Rol başına farklı kolonlar çok artarsa ayrı profil tabloları (1-1 ilişki) düşünülür.
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.db import Base, UTCDateTime, enum_column


# Enum: sabit değerler kümesi. `str` ile birlikte miras alınınca değerler JSON'a ve veritabanına
# metin olarak yazılır.
class UserRole(str, enum.Enum):
    # Dört rolün her biri farklı yetkilere sahiptir; yetki kontrolü identity/deps.py içinde yapılır.
    DONOR = "DONOR"              # restoran, firin, yemekhane
    BENEFICIARY = "BENEFICIARY"  # insan tuketimi icin yararlanici
    SHELTER = "SHELTER"          # hayvan barinagi / yetistirici
    ADMIN = "ADMIN"


# Hesabın yaşam döngüsü. PENDING_REVIEW -> ACTIVE | REJECTED, ACTIVE <-> SUSPENDED. Durum alanı ile
# iş akışı modellemek, 'onaylı mı?' için ayrı bir boolean tutmaktan daha esnektir.
class AccountStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PENDING_REVIEW = "PENDING_REVIEW"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


# Roles that must pass an admin review before acting (they publish or receive on behalf of an organization).
# Kurum adına çalışan roller yönetici incelemesinden geçmeden işlem yapamaz. Bu bir kural verisidir;
# kural değişirse tek yerden değişir.
REVIEWED_ROLES = (UserRole.DONOR, UserRole.SHELTER)


# Bir sınıf = bir tablo, bir nesne = bir satır (ORM: Object Relational Mapping). Tüm roller tek
# `users` tablosunda tutulur.
class User(Base):
    __tablename__ = "users"
    # Bileşik indeks: `WHERE role = ? AND status = ?` sorguları tabloyu baştan sona taramadan
    # çalışır. Plan için sql/queries.sql içindeki EXPLAIN QUERY PLAN sorgusuna bakın.
    __table_args__ = (Index("ix_users_role_status", "role", "status"),)

    # Birincil anahtar (PRIMARY KEY): her satırı tekil tanımlar; SQLite otomatik artırır.
    id: Mapped[int] = mapped_column(primary_key=True)
    # unique=True: veritabanı düzeyinde UNIQUE kısıtı. İki kişi aynı anda aynı e-postayla kayıt
    # olmaya çalışsa bile yalnızca biri başarılı olur (uygulama kodundaki kontrol buna güvenemez).
    # index=True: girişte e-postayla arama hızlı olsun.
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    # Parolanın kendisi değil özeti (hash) saklanır. Bu alan hiçbir API yanıtında dışarı verilmez
    # (schemas.UserOut'ta yok).
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(150))
    # Rol alanı yetki kararlarının temelidir.
    role: Mapped[UserRole] = mapped_column(enum_column(UserRole))
    # Hesap durumu: giriş, ilan ve rezervasyon izinleri buna bağlıdır.
    status: Mapped[AccountStatus] = mapped_column(enum_column(AccountStatus))
    phone: Mapped[str | None] = mapped_column(String(30))

    # Aşağıdaki alanlar yalnızca kurumlar (bağışçı, barınak) için doludur; bireyde NULL kalır. `X |
    # None` NULL olabilir demektir.
    organization_name: Mapped[str | None] = mapped_column(String(200))
    license_number: Mapped[str | None] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(String(300))
    # Harita koordinatı. İlan açarken varsayılan konum olarak kullanılır.
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)

    # Yönetici notu veya askıya alma gerekçesi.
    review_note: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    # default=utcnow: fonksiyonun KENDİSİ verilir, çağrılmaz; her satır eklenirken çalışır.
    # `utcnow()` yazsaydık tüm satırlar sunucunun açılış zamanını alırdı (sık yapılan hata).
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    # @property: hesaplanan alan. `user.display_name` parantezsiz okunur ve veritabanında kolon
    # değildir.
    @property
    def display_name(self) -> str:
        return self.organization_name or self.full_name

    # Gizlilik: bağışçı yararlanıcının tam adını görmez, 'Ali Y.' gibi kısaltılmış etiketi görür
    # (KVKK ruhuyla veri azaltma).
    @property
    def public_label(self) -> str:
        """Privacy-safe name: 'Ahmet Y.' Used wherever a donor sees a beneficiary."""
        parts = self.full_name.split()
        if len(parts) < 2:
            return parts[0] if parts else "-"
        return f"{parts[0]} {parts[-1][0]}."

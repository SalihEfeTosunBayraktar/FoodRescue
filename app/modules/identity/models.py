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


class UserRole(str, enum.Enum):
    DONOR = "DONOR"              # restoran, firin, yemekhane
    BENEFICIARY = "BENEFICIARY"  # insan tuketimi icin yararlanici
    SHELTER = "SHELTER"          # hayvan barinagi / yetistirici
    ADMIN = "ADMIN"


class AccountStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PENDING_REVIEW = "PENDING_REVIEW"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


# Roles that must pass an admin review before acting (they publish or receive on behalf of an organization).
REVIEWED_ROLES = (UserRole.DONOR, UserRole.SHELTER)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_role_status", "role", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(150))
    role: Mapped[UserRole] = mapped_column(enum_column(UserRole))
    status: Mapped[AccountStatus] = mapped_column(enum_column(AccountStatus))
    phone: Mapped[str | None] = mapped_column(String(30))

    organization_name: Mapped[str | None] = mapped_column(String(200))
    license_number: Mapped[str | None] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(String(300))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)

    review_note: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    @property
    def display_name(self) -> str:
        return self.organization_name or self.full_name

    @property
    def public_label(self) -> str:
        """Privacy-safe name: 'Ahmet Y.' Used wherever a donor sees a beneficiary."""
        parts = self.full_name.split()
        if len(parts) < 2:
            return parts[0] if parts else "-"
        return f"{parts[0]} {parts[-1][0]}."

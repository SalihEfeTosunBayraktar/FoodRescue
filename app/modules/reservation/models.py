"""Reservation data model.

Ders notu (veritabanı): `donor_id` aslında food_items üzerinden de bulunabilir (reservation ->
food -> donor). Burada kasıtlı olarak kopyalıyoruz; çünkü "bu bağışçının bekleyen rezervasyonları"
sorgusu en sık çalışan sorgudur ve JOIN'siz, indeksli çalışmasını istiyoruz. Bu bir
performans/okunabilirlik takasıdır (denormalization).
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utcnow
from app.core.db import Base, UTCDateTime, enum_column
from app.modules.identity.models import User
from app.modules.inventory.models import FoodItem


class ReservationStatus(str, enum.Enum):
    PENDING = "PENDING"
    COLLECTED = "COLLECTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint("portions >= 1", name="ck_reservation_portions"),
        Index("ix_reservation_donor_status", "donor_id", "status"),
        Index("ix_reservation_beneficiary_status", "beneficiary_id", "status"),
        Index("ix_reservation_status_expires", "status", "expires_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    food_id: Mapped[int] = mapped_column(ForeignKey("food_items.id"), index=True)
    beneficiary_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    donor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    portions: Mapped[int]
    qr_token: Mapped[str] = mapped_column(String(64), unique=True)
    pin: Mapped[str] = mapped_column(String(6))
    status: Mapped[ReservationStatus] = mapped_column(enum_column(ReservationStatus), default=ReservationStatus.PENDING)
    note: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    collected_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    food: Mapped[FoodItem] = relationship(lazy="joined")
    beneficiary: Mapped[User] = relationship(foreign_keys=[beneficiary_id], lazy="joined")
    donor: Mapped[User] = relationship(foreign_keys=[donor_id], lazy="joined")

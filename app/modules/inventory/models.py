"""Inventory data model.

Ders notu (veritabanı): `portions_left` türetilebilir bir değerdir (toplam - rezerve edilenler)
ama her seferinde SUM() ile hesaplamak yerine sayaç olarak tutuyoruz ("denormalization").
Bedeli: sayacın her zaman doğru kalmasını sağlamak. Bunu service.take_portions içindeki
atomik UPDATE ile garanti ederiz.
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import CheckConstraint, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utcnow
from app.core.db import Base, UTCDateTime, enum_column
from app.modules.identity.models import User


class FoodCategory(str, enum.Enum):
    HUMAN = "HUMAN"            # askida yemek, insan tuketimi
    ANIMAL = "ANIMAL"          # barinak / hayvan yemi


class StorageCondition(str, enum.Enum):
    HOT = "HOT"
    COLD = "COLD"
    ROOM = "ROOM"


class FoodStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class FoodItem(Base):
    __tablename__ = "food_items"
    __table_args__ = (
        CheckConstraint("portions_left >= 0 AND portions_left <= portions_total", name="ck_food_portions_range"),
        CheckConstraint("max_per_person >= 1", name="ck_food_max_per_person"),
        Index("ix_food_status_pickup", "status", "pickup_until"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    donor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[FoodCategory] = mapped_column(enum_column(FoodCategory))
    storage: Mapped[StorageCondition] = mapped_column(enum_column(StorageCondition))

    portions_total: Mapped[int]
    portions_left: Mapped[int]
    max_per_person: Mapped[int] = mapped_column(default=2)

    pickup_until: Mapped[datetime] = mapped_column(UTCDateTime)
    address: Mapped[str] = mapped_column(String(300))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)

    hygiene_confirmed: Mapped[bool] = mapped_column(default=False)
    photo_path: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[FoodStatus] = mapped_column(enum_column(FoodStatus), default=FoodStatus.AVAILABLE)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    donor: Mapped[User] = relationship(lazy="joined")

    @property
    def is_available(self) -> bool:
        return self.status == FoodStatus.AVAILABLE and self.portions_left > 0 and self.pickup_until > utcnow()

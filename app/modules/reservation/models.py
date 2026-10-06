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


# Rezervasyonun durum makinesi. PENDING dışındaki üç durum SON durumdur: oradan başka duruma
# geçilmez.
class ReservationStatus(str, enum.Enum):
    PENDING = "PENDING"
    COLLECTED = "COLLECTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


# Bir yararlanıcının bir ilandan ayırdığı porsiyonlar. Üç tabloyu bağlar: users (iki kez:
# yararlanıcı ve bağışçı) ve food_items.
class Reservation(Base):
    __tablename__ = "reservations"
    # Kısıtlar ve indeksler: her indeks belirli bir ekranın sorgusu için konmuştur.
    __table_args__ = (
        # Sıfır veya negatif porsiyonlu rezervasyon veritabanı düzeyinde engellenir.
        CheckConstraint("portions >= 1", name="ck_reservation_portions"),
        # Teslim masası: 'bu işletmenin BEKLEYEN rezervasyonları'.
        Index("ix_reservation_donor_status", "donor_id", "status"),
        # Cüzdan: 'bu kullanıcının rezervasyonları'.
        Index("ix_reservation_beneficiary_status", "beneficiary_id", "status"),
        # Zamanlı iş: 'süresi dolmuş BEKLEYEN rezervasyonlar'.
        Index("ix_reservation_status_expires", "status", "expires_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # ForeignKey: rezervasyon var olan bir ilana bağlıdır.
    food_id: Mapped[int] = mapped_column(ForeignKey("food_items.id"), index=True)
    # Rezervasyonu yapan kullanıcı.
    beneficiary_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # İlanın sahibi, ilandan KOPYALANMIŞTIR (denormalizasyon). Teslim masası sorgusu en sık çalışan
    # sorgudur; food_items'a JOIN yapmadan doğrudan indeksli çalışsın diye. Bedeli: ilan sahibi
    # değişmez olmalı (bizde değişmez).
    donor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # Bu rezervasyondaki porsiyon sayısı; iptalde bu kadarı stoğa iade edilir.
    portions: Mapped[int]
    # QR kodun içindeki gizli değer. unique=True: iki rezervasyon aynı kodu taşıyamaz. Tahmin
    # edilemez olmalı (secrets ile üretilir).
    qr_token: Mapped[str] = mapped_column(String(64), unique=True)
    # 6 haneli yedek kod (kamera çalışmazsa). Yalnızca 1 milyon ihtimal olduğu için kaba kuvvete
    # karşı deneme sınırı şarttır (service.verify_pickup).
    pin: Mapped[str] = mapped_column(String(6))
    # Durum makinesinin mevcut durumu.
    status: Mapped[ReservationStatus] = mapped_column(enum_column(ReservationStatus), default=ReservationStatus.PENDING)
    note: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    # Rezervasyonun son geçerlilik zamanı: en geç ilanın son teslim saati.
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    # Teslim anı; NULL ise henüz teslim edilmemiştir.
    collected_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    # İlişkiler lazy='joined': rezervasyonla birlikte ilan ve kullanıcılar tek sorguda gelir (N+1
    # sorununu önler).
    food: Mapped[FoodItem] = relationship(lazy="joined")
    # foreign_keys belirtilmeli: bu tabloda users'a İKİ yabancı anahtar var, SQLAlchemy hangisini
    # kastettiğimizi bilmek ister.
    beneficiary: Mapped[User] = relationship(foreign_keys=[beneficiary_id], lazy="joined")
    donor: Mapped[User] = relationship(foreign_keys=[donor_id], lazy="joined")

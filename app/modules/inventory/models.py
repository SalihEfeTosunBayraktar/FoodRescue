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


# HUMAN: insan tüketimi (askıda yemek). ANIMAL: barınaklar. Kategori yararlanıcı rolüyle eşleşir
# (reservation servisi kontrol eder).
class FoodCategory(str, enum.Enum):
    HUMAN = "HUMAN"            # askida yemek, insan tuketimi
    ANIMAL = "ANIMAL"          # barinak / hayvan yemi


# Saklama koşulu yararlanıcıya gösterilir (sıcak yemek geç kalınca bozulur).
class StorageCondition(str, enum.Enum):
    HOT = "HOT"
    COLD = "COLD"
    ROOM = "ROOM"


# İlan durumu. Müsaitlik tek başına durumdan değil, durum + kalan porsiyon + zamandan hesaplanır
# (is_available).
class FoodStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


# Bir bağış ilanı. Bir bağışçının (users) birçok ilanı olabilir: bire-çok (1-N) ilişki.
class FoodItem(Base):
    __tablename__ = "food_items"
    # Tablo düzeyinde kısıtlar ve indeksler. CHECK kısıtları verinin yanlış girilmesini VERİTABANI
    # düzeyinde engeller.
    __table_args__ = (
        # Son savunma hattı: uygulama kodunda hata olsa bile kalan porsiyon eksiye düşemez veya
        # toplamı aşamaz.
        CheckConstraint("portions_left >= 0 AND portions_left <= portions_total", name="ck_food_portions_range"),
        # Kişi başı en az 1 porsiyon.
        CheckConstraint("max_per_person >= 1", name="ck_food_max_per_person"),
        # Liste sorgusu hep 'durumu AVAILABLE ve süresi dolmamış olanlar'ı arar; bileşik indeks bunu
        # hızlandırır.
        Index("ix_food_status_pickup", "status", "pickup_until"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # ForeignKey: bu sütun users.id'ye başvurur; var olmayan bağışçıya ilan eklenemez (foreign_keys
    # PRAGMA açık olduğu için). index=True: 'bağışçının ilanları' sorgusu için.
    donor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[FoodCategory] = mapped_column(enum_column(FoodCategory))
    storage: Mapped[StorageCondition] = mapped_column(enum_column(StorageCondition))

    # Toplam porsiyon sabit kalır.
    portions_total: Mapped[int]
    # Kalan porsiyon bir SAYAÇtır. Türetilebilir (toplam - rezerve edilenler) ama her seferinde
    # toplamak yerine saklanır: bu bilinçli bir denormalizasyondur. Doğruluğu atomik UPDATE ile
    # korunur (service.take_portions).
    portions_left: Mapped[int]
    # Adil dağıtım: kişi başı üst sınır.
    max_per_person: Mapped[int] = mapped_column(default=2)

    # Son teslim zamanı (UTC, saat dilimli). Bu zamandan sonra ilan kapanır.
    pickup_until: Mapped[datetime] = mapped_column(UTCDateTime)
    # İlana kopyalanan adres/koordinat: bağışçı sonradan taşınsa bile eski ilanın konumu değişmez
    # (tarihsel doğruluk).
    address: Mapped[str] = mapped_column(String(300))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)

    # Bağışçı hijyen beyanını onaylamadan ilan açamaz; onay kaydı hukuki izlenebilirlik sağlar.
    hygiene_confirmed: Mapped[bool] = mapped_column(default=False)
    # Dosyanın kendisi diskte, veritabanında yalnızca göreli yolu tutulur (büyük ikili veriyi
    # veritabanına koymamak yaygın bir tercihtir).
    photo_path: Mapped[str | None] = mapped_column(String(255))
    # Durum alanı varsayılan olarak AVAILABLE.
    status: Mapped[FoodStatus] = mapped_column(enum_column(FoodStatus), default=FoodStatus.AVAILABLE)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    # relationship: ilanın bağışçısına nesne olarak ulaşmak (`food.donor.display_name`).
    # lazy='joined': ilan çekilirken tek sorguda JOIN ile birlikte gelir; her ilan için ayrı sorgu
    # atılmaz (N+1 sorunu).
    donor: Mapped[User] = relationship(lazy="joined")

    # Hesaplanan özellik: ilan şu anda gerçekten alınabilir mi? Üç koşul birlikte sağlanmalı.
    @property
    def is_available(self) -> bool:
        return self.status == FoodStatus.AVAILABLE and self.portions_left > 0 and self.pickup_until > utcnow()

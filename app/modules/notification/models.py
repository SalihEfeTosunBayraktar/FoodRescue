from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.db import Base, UTCDateTime


# Uygulama içi bildirim kutusu satırı.
class Notification(Base):
    __tablename__ = "notifications"
    # Ders notu: "kullanıcının okunmamış bildirimleri" sorgusu için bileşik indeks (user_id, read_at).
    __table_args__ = (Index("ix_notification_user_read", "user_id", "read_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # Bildirimin sahibi. Her kullanıcı yalnızca kendi bildirimlerini görür (sorgu user_id ile
    # daraltılır).
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # Bildirim türü anahtarı (örn. 'reservation.created.donor'). Şablonu bu anahtardan buluruz.
    kind: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    # NULL = okunmamış. Ayrı bir 'okundu' boolean'ı yerine zaman damgası: hem durumu hem ne zaman
    # okunduğunu verir.
    read_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

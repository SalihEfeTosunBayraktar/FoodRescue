from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utcnow
from app.core.db import Base, UTCDateTime, enum_column
from app.modules.identity.models import User


# Denetim kaydı: 'kim, ne zaman, neyi yaptı?' sorusunun değiştirilemez cevabı.
class AuditLog(Base):
    """Append-only record of who did what. Rows are never updated or deleted.

    Ders notu: denetim kaydı (audit log) güvenlik ve hesap verebilirlik içindir. Silme/güncelleme
    endpoint'i bilerek yoktur.
    """

    __tablename__ = "audit_log"
    # Bir kaydın tüm geçmişi (entity_type + entity_id) sık sorgulanır; bileşik indeks bunun içindir.
    __table_args__ = (Index("ix_audit_entity", "entity_type", "entity_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # NULL olabilir: sistem kendisi yaptıysa (zamanlı iş gibi) kullanıcı yoktur.
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    # Olay adı (örn. 'reservation.collected'). index=True: işleme göre filtre için.
    action: Mapped[str] = mapped_column(String(80), index=True)
    # Neyin üzerinde: 'user', 'food', 'reservation', 'complaint'. Tek tabloda farklı varlıkları
    # izlemenin 'polimorfik' yolu.
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[int]
    # Ek bilgiler JSON metni olarak saklanır; şema değişmeden yeni alan eklenebilir.
    detail: Mapped[str | None] = mapped_column(Text)
    # index=True: 'son N olay' sorgusu için.
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)


# OPEN -> RESOLVED | DISMISSED.
class ComplaintStatus(str, enum.Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


# Yararlanıcının bir teslimle ilgili şikâyeti.
class Complaint(Base):
    __tablename__ = "complaints"
    # Bir işletme hakkındaki AÇIK şikâyetleri saymak (eşik kontrolü) sık çalışan sorgudur; bileşik
    # indeks bunun içindir.
    __table_args__ = (Index("ix_complaint_donor_status", "donor_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # Şikâyet eden.
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    donor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # UNIQUE: one complaint per reservation keeps a single user from triggering a suspension alone.
    # Şikâyet bir REZERVASYONA bağlıdır: sadece gerçekten teslim almış biri şikâyet edebilir (sahte
    # şikâyeti zorlaştırır).
    reservation_id: Mapped[int] = mapped_column(ForeignKey("reservations.id"), unique=True)
    reason: Mapped[str] = mapped_column(Text)
    # Şikâyetin yönetici tarafından sonuçlandırılma durumu.
    status: Mapped[ComplaintStatus] = mapped_column(enum_column(ComplaintStatus), default=ComplaintStatus.OPEN)
    resolution_note: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    # Şikâyet edilen işletmeye nesne olarak ulaşmak için.
    donor: Mapped[User] = relationship(foreign_keys=[donor_id], lazy="joined")

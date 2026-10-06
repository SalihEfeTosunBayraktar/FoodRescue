from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utcnow
from app.core.db import Base, UTCDateTime, enum_column
from app.modules.identity.models import User


class AuditLog(Base):
    """Append-only record of who did what. Rows are never updated or deleted.

    Ders notu: denetim kaydı (audit log) güvenlik ve hesap verebilirlik içindir. Silme/güncelleme
    endpoint'i bilerek yoktur.
    """

    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_entity", "entity_type", "entity_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[int]
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)


class ComplaintStatus(str, enum.Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class Complaint(Base):
    __tablename__ = "complaints"
    __table_args__ = (Index("ix_complaint_donor_status", "donor_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    donor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # UNIQUE: one complaint per reservation keeps a single user from triggering a suspension alone.
    reservation_id: Mapped[int] = mapped_column(ForeignKey("reservations.id"), unique=True)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[ComplaintStatus] = mapped_column(enum_column(ComplaintStatus), default=ComplaintStatus.OPEN)
    resolution_note: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    donor: Mapped[User] = relationship(foreign_keys=[donor_id], lazy="joined")

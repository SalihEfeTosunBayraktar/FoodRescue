"""Impact: statistics, complaints and audit trail.

Ders notu (SQL): burada GROUP BY, COUNT, SUM ve COALESCE kullanılır. Aynı sorguların ham SQL
karşılığı modülün `sql/queries.sql` dosyasındadır; ikisini yan yana okuyun.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import events
from app.config.messages import COMPLAINT_SUSPEND_REASON
from app.core.clock import utcnow
from app.core.context import ctx_of
from app.core.errors import AppError
from app.modules.identity import service as identity
from app.modules.identity.models import AccountStatus, User, UserRole
from app.modules.impact.models import AuditLog, Complaint, ComplaintStatus
from app.modules.impact.schemas import ComplaintIn, ComplaintOut, DonorImpactOut, OverviewOut, SummaryOut
from app.modules.inventory.models import FoodItem, FoodStatus
from app.modules.reservation.models import Reservation, ReservationStatus

# Olay yükündeki standart alanlar ayrı kolonlara gider; kalanı 'detail' JSON'una yazılır.
_AUDIT_STANDARD_KEYS = {"actor_id", "entity_type", "entity_id"}


# ---- statistics ---------------------------------------------------------------------------------

# Ana sayfa sayaçları. Üç ayrı sorgu: toplam porsiyon+teslim, onaylı bağışçı, müsait ilan.
def summary(db: Session) -> SummaryOut:
    # COALESCE(SUM(...), 0): hiç satır yoksa SUM, NULL döner; bu 0'a çevrilir. Tek sorguda iki
    # toplama (SUM ve COUNT). `.one()` tam bir satır bekler.
    portions, pickups = db.execute(
        select(func.coalesce(func.sum(Reservation.portions), 0), func.count(Reservation.id)).where(
            Reservation.status == ReservationStatus.COLLECTED
        )
    ).one()
    # Aktif (onaylı) bağışçı sayısı.
    donors = db.scalar(
        select(func.count()).select_from(User).where(User.role == UserRole.DONOR, User.status == AccountStatus.ACTIVE)
    )
    # Şu an alınabilir ilan sayısı: inventory'deki üç koşulla aynı.
    available = db.scalar(
        select(func.count()).select_from(FoodItem).where(
            FoodItem.status == FoodStatus.AVAILABLE, FoodItem.portions_left > 0, FoodItem.pickup_until > utcnow()
        )
    )
    return SummaryOut(portions_rescued=portions, pickups_completed=pickups, active_donors=donors, foods_available=available)


# İşletme panosu: teslim edilen / bekleyen porsiyon ve ilan sayısı.
def donor_impact(db: Session, donor: User) -> DonorImpactOut:
    # Aynı toplama, bu kez yalnızca bu işletmenin rezervasyonları için (donor_id süzgeci).
    portions, pickups = db.execute(
        select(func.coalesce(func.sum(Reservation.portions), 0), func.count(Reservation.id)).where(
            Reservation.donor_id == donor.id, Reservation.status == ReservationStatus.COLLECTED
        )
    ).one()
    # Bekleyen porsiyon toplamı (henüz alınmamış, ama ayrılmış).
    waiting = db.scalar(
        select(func.coalesce(func.sum(Reservation.portions), 0)).where(
            Reservation.donor_id == donor.id, Reservation.status == ReservationStatus.PENDING
        )
    )
    foods = db.scalar(select(func.count()).select_from(FoodItem).where(FoodItem.donor_id == donor.id))
    return DonorImpactOut(portions_rescued=portions, pickups_completed=pickups, portions_waiting=waiting, foods_published=foods)


# Yönetici genel bakışı: kaç hesap onay bekliyor, kaç şikâyet açık, dağılımlar.
def overview(db: Session) -> OverviewOut:
    # GROUP BY: rol başına satır sayısı. `dict(satırlar)`: (anahtar, değer) çiftlerinden sözlük
    # kurar.
    by_role = dict(db.execute(select(User.role, func.count()).group_by(User.role)).all())
    # Aynı desen: rezervasyon durumlarının dağılımı.
    by_status = dict(db.execute(select(Reservation.status, func.count()).group_by(Reservation.status)).all())
    return OverviewOut(
        pending_accounts=db.scalar(
            select(func.count()).select_from(User).where(User.status == AccountStatus.PENDING_REVIEW)
        ),
        open_complaints=db.scalar(
            select(func.count()).select_from(Complaint).where(Complaint.status == ComplaintStatus.OPEN)
        ),
        users_by_role={role.value: n for role, n in by_role.items()},
        reservations_by_status={status.value: n for status, n in by_status.items()},
    )


# ---- complaints ---------------------------------------------------------------------------------

# Şikâyet akışı: doğrula -> kaydet -> eşiği kontrol et -> gerekirse askıya al. Hepsi TEK işlemde.
def file_complaint(db: Session, reporter: User, data: ComplaintIn) -> Complaint:
    settings = ctx_of(db).settings
    # Impact başka modülün tablosunu yalnızca OKUR.
    res = db.get(Reservation, data.reservation_id)
    # Yalnızca kendi rezervasyonu için şikâyet. Başkasınınki için 404: varlığı bile belli etmeyiz.
    if not res or res.beneficiary_id != reporter.id:
        raise AppError("reservation.not_found", 404)
    # Aynı rezervasyon için ikinci şikâyet reddedilir (veritabanında da UNIQUE var; burada
    # kullanıcıya düzgün mesaj verilir).
    if db.scalar(select(Complaint.id).where(Complaint.reservation_id == res.id)):
        raise AppError("complaint.duplicate", 409)

    # Şikâyet kaydı hazırlanır.
    complaint = Complaint(reporter_id=reporter.id, donor_id=res.donor_id, reservation_id=res.id, reason=data.reason.strip())
    db.add(complaint)
    db.flush()
    ctx_of(db).bus.publish(
        db, events.COMPLAINT_FILED, actor_id=reporter.id, entity_type="complaint", entity_id=complaint.id, donor_id=res.donor_id
    )

    # COUNT(DISTINCT reporter_id): FARKLI kaç kişi şikâyet etmiş? Aynı kişi birden çok şikâyet etse
    # tek sayılır; böylece tek kullanıcı bir işletmeyi tek başına askıya aldıramaz.
    distinct_reporters = db.scalar(
        select(func.count(func.distinct(Complaint.reporter_id))).where(
            Complaint.donor_id == res.donor_id, Complaint.status == ComplaintStatus.OPEN
        )
    )
    donor = res.donor
    # Eşik aşıldı ve işletme hâlâ aktifse askıya al.
    if distinct_reporters >= settings.complaint_suspend_threshold and donor.status == AccountStatus.ACTIVE:
        # Burada tek çağrı var; geri kalanı (ilanların kaldırılması, rezervasyonların iptali,
        # bildirimler) olay zinciriyle kendiliğinden olur.
        identity.suspend_account(db, donor, COMPLAINT_SUSPEND_REASON, actor_id=None)
    db.commit()
    return complaint


# Yönetici listesi, isteğe bağlı durum süzgeci.
def list_complaints(db: Session, status: ComplaintStatus | None = None) -> list[Complaint]:
    query = select(Complaint).order_by(Complaint.created_at.desc())
    if status:
        query = query.where(Complaint.status == status)
    return list(db.scalars(query).unique())


# Yönetici kararı. Sonuçlanmış şikâyet tekrar değiştirilemez.
def resolve_complaint(db: Session, admin: User, complaint_id: int, dismiss: bool, note: str | None) -> Complaint:
    complaint = db.get(Complaint, complaint_id)
    if not complaint:
        raise AppError("complaint.not_found", 404)
    if complaint.status != ComplaintStatus.OPEN:
        raise AppError("complaint.closed", 409)
    complaint.status = ComplaintStatus.DISMISSED if dismiss else ComplaintStatus.RESOLVED
    complaint.resolution_note = note
    complaint.resolved_by = admin.id
    complaint.resolved_at = utcnow()
    ctx_of(db).bus.publish(
        db, events.COMPLAINT_RESOLVED, actor_id=admin.id, entity_type="complaint", entity_id=complaint.id, dismissed=dismiss
    )
    db.commit()
    return complaint


# Model -> yanıt şeması dönüşümü.
def to_complaint_out(complaint: Complaint) -> ComplaintOut:
    return ComplaintOut(
        id=complaint.id,
        reservation_id=complaint.reservation_id,
        donor_id=complaint.donor_id,
        donor_name=complaint.donor.display_name,
        reason=complaint.reason,
        status=complaint.status,
        resolution_note=complaint.resolution_note,
        created_at=complaint.created_at,
    )


# ---- audit --------------------------------------------------------------------------------------

# Her olayı denetim tablosuna ekler. Bu tabloya yalnızca INSERT yapılır; güncelleme/silme yolu
# bilerek yoktur (append-only).
def record_audit(db: Session, event: str, payload: dict[str, Any]) -> None:
    # Standart olmayan alanlar ek bilgi olarak toplanır (sözlük anlama).
    detail = {k: v for k, v in payload.items() if k not in _AUDIT_STANDARD_KEYS}
    db.add(
        # default=str: JSON'a çevrilemeyen nesneler (tarih gibi) metne çevrilir.
        AuditLog(
            actor_id=payload.get("actor_id"),
            action=event,
            entity_type=payload["entity_type"],
            entity_id=payload["entity_id"],
            detail=json.dumps(detail, ensure_ascii=False, default=str) if detail else None,
        )
    )


# Sayfalama: limit + offset. Sınırsız denetim listesi veritabanını ve ağı yorar.
def list_audit(db: Session, action: str | None = None, limit: int = 100, offset: int = 0) -> list[AuditLog]:
    query = select(AuditLog).order_by(AuditLog.id.desc()).limit(limit).offset(offset)
    if action:
        query = query.where(AuditLog.action == action)
    return list(db.scalars(query))

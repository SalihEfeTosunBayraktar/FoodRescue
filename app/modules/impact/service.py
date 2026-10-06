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

_AUDIT_STANDARD_KEYS = {"actor_id", "entity_type", "entity_id"}


# ---- statistics ---------------------------------------------------------------------------------

def summary(db: Session) -> SummaryOut:
    portions, pickups = db.execute(
        select(func.coalesce(func.sum(Reservation.portions), 0), func.count(Reservation.id)).where(
            Reservation.status == ReservationStatus.COLLECTED
        )
    ).one()
    donors = db.scalar(
        select(func.count()).select_from(User).where(User.role == UserRole.DONOR, User.status == AccountStatus.ACTIVE)
    )
    available = db.scalar(
        select(func.count()).select_from(FoodItem).where(
            FoodItem.status == FoodStatus.AVAILABLE, FoodItem.portions_left > 0, FoodItem.pickup_until > utcnow()
        )
    )
    return SummaryOut(portions_rescued=portions, pickups_completed=pickups, active_donors=donors, foods_available=available)


def donor_impact(db: Session, donor: User) -> DonorImpactOut:
    portions, pickups = db.execute(
        select(func.coalesce(func.sum(Reservation.portions), 0), func.count(Reservation.id)).where(
            Reservation.donor_id == donor.id, Reservation.status == ReservationStatus.COLLECTED
        )
    ).one()
    waiting = db.scalar(
        select(func.coalesce(func.sum(Reservation.portions), 0)).where(
            Reservation.donor_id == donor.id, Reservation.status == ReservationStatus.PENDING
        )
    )
    foods = db.scalar(select(func.count()).select_from(FoodItem).where(FoodItem.donor_id == donor.id))
    return DonorImpactOut(portions_rescued=portions, pickups_completed=pickups, portions_waiting=waiting, foods_published=foods)


def overview(db: Session) -> OverviewOut:
    by_role = dict(db.execute(select(User.role, func.count()).group_by(User.role)).all())
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

def file_complaint(db: Session, reporter: User, data: ComplaintIn) -> Complaint:
    settings = ctx_of(db).settings
    res = db.get(Reservation, data.reservation_id)
    if not res or res.beneficiary_id != reporter.id:
        raise AppError("reservation.not_found", 404)
    if db.scalar(select(Complaint.id).where(Complaint.reservation_id == res.id)):
        raise AppError("complaint.duplicate", 409)

    complaint = Complaint(reporter_id=reporter.id, donor_id=res.donor_id, reservation_id=res.id, reason=data.reason.strip())
    db.add(complaint)
    db.flush()
    ctx_of(db).bus.publish(
        db, events.COMPLAINT_FILED, actor_id=reporter.id, entity_type="complaint", entity_id=complaint.id, donor_id=res.donor_id
    )

    distinct_reporters = db.scalar(
        select(func.count(func.distinct(Complaint.reporter_id))).where(
            Complaint.donor_id == res.donor_id, Complaint.status == ComplaintStatus.OPEN
        )
    )
    donor = res.donor
    if distinct_reporters >= settings.complaint_suspend_threshold and donor.status == AccountStatus.ACTIVE:
        identity.suspend_account(db, donor, COMPLAINT_SUSPEND_REASON, actor_id=None)
    db.commit()
    return complaint


def list_complaints(db: Session, status: ComplaintStatus | None = None) -> list[Complaint]:
    query = select(Complaint).order_by(Complaint.created_at.desc())
    if status:
        query = query.where(Complaint.status == status)
    return list(db.scalars(query).unique())


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

def record_audit(db: Session, event: str, payload: dict[str, Any]) -> None:
    detail = {k: v for k, v in payload.items() if k not in _AUDIT_STANDARD_KEYS}
    db.add(
        AuditLog(
            actor_id=payload.get("actor_id"),
            action=event,
            entity_type=payload["entity_type"],
            entity_id=payload["entity_id"],
            detail=json.dumps(detail, ensure_ascii=False, default=str) if detail else None,
        )
    )


def list_audit(db: Session, action: str | None = None, limit: int = 100, offset: int = 0) -> list[AuditLog]:
    query = select(AuditLog).order_by(AuditLog.id.desc()).limit(limit).offset(offset)
    if action:
        query = query.where(AuditLog.action == action)
    return list(db.scalars(query))

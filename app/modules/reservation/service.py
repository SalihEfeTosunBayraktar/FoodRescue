"""Reservation use-cases: reserve, cancel, verify at pickup, expire.

State machine:   PENDING --verify--> COLLECTED
                 PENDING --cancel--> CANCELLED
                 PENDING --timeout-> EXPIRED
Only PENDING can move; the other three are terminal.

Ders notu (güvenlik): doğrulama (verify) şu kurallarla korunur:
  1. Yalnızca ilanın sahibi bağışçı doğrulayabilir (sorgu donor_id ile daraltılır).
  2. PIN yalnızca 1 milyon ihtimaldir; bu yüzden bağışçı başına hatalı deneme sınırı vardır.
  3. Kodlar `secrets` ile üretilir (random modülü tahmin edilebilir).
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import events
from app.core.clock import utcnow
from app.core.context import ctx_of
from app.core.errors import AppError
from app.core.security import random_pin, random_token
from app.modules.identity.models import User, UserRole
from app.modules.inventory import service as inventory
from app.modules.inventory.models import FoodItem
from app.modules.reservation import qr
from app.modules.reservation.models import Reservation, ReservationStatus
from app.modules.reservation.schemas import (
    DonorReservationOut,
    MyReservationOut,
    ReservationCreate,
    VerifyOut,
)

_PIN_RETRIES = 20


def _event_payload(res: Reservation, actor_id: int | None, **extra) -> dict:
    return {
        "actor_id": actor_id,
        "entity_type": "reservation",
        "entity_id": res.id,
        "food_id": res.food_id,
        "food_title": res.food.title,
        "portions": res.portions,
        "donor_id": res.donor_id,
        "beneficiary_id": res.beneficiary_id,
        "beneficiary": res.beneficiary.public_label,
        **extra,
    }


def _unique_pin(db: Session, donor_id: int) -> str:
    """A PIN must be unique among the donor's PENDING reservations, otherwise a PIN lookup is ambiguous."""
    for _ in range(_PIN_RETRIES):
        pin = random_pin()
        taken = db.scalar(
            select(func.count()).select_from(Reservation).where(
                Reservation.donor_id == donor_id, Reservation.status == ReservationStatus.PENDING, Reservation.pin == pin
            )
        )
        if not taken:
            return pin
    raise AppError("food.unavailable", 409)


def create_reservation(db: Session, user: User, data: ReservationCreate) -> Reservation:
    settings = ctx_of(db).settings
    food = inventory.get_food(db, data.food_id)

    if inventory.category_for_role(user.role) != food.category:
        raise AppError("reservation.wrong_category", 403)
    if data.portions > food.max_per_person:
        raise AppError("reservation.too_many_portions", 422, limit=food.max_per_person)

    active = db.scalar(
        select(func.count()).select_from(Reservation).where(
            Reservation.beneficiary_id == user.id, Reservation.status == ReservationStatus.PENDING
        )
    )
    if active >= settings.max_active_reservations:
        raise AppError("reservation.too_many_active", 409, limit=settings.max_active_reservations)

    now = utcnow()
    food = inventory.take_portions(db, food.id, data.portions, now)  # atomic; raises if sold out
    res = Reservation(
        food_id=food.id,
        beneficiary_id=user.id,
        donor_id=food.donor_id,
        portions=data.portions,
        qr_token=random_token(),
        pin=_unique_pin(db, food.donor_id),
        note=data.note,
        expires_at=min(now + timedelta(minutes=settings.reservation_ttl_minutes), food.pickup_until),
    )
    db.add(res)
    db.flush()
    ctx_of(db).bus.publish(db, events.RESERVATION_CREATED, **_event_payload(res, user.id))
    db.commit()
    return res


def get_reservation(db: Session, reservation_id: int) -> Reservation:
    res = db.get(Reservation, reservation_id)
    if not res:
        raise AppError("reservation.not_found", 404)
    return res


def my_reservations(db: Session, user: User) -> list[Reservation]:
    query = select(Reservation).where(Reservation.beneficiary_id == user.id).order_by(Reservation.created_at.desc())
    return list(db.scalars(query).unique())


def donor_reservations(db: Session, donor: User, status: ReservationStatus | None = None) -> list[Reservation]:
    query = select(Reservation).where(Reservation.donor_id == donor.id).order_by(Reservation.created_at.desc())
    if status:
        query = query.where(Reservation.status == status)
    return list(db.scalars(query.limit(200)).unique())


def cancel_reservation(db: Session, actor: User, reservation_id: int) -> Reservation:
    res = get_reservation(db, reservation_id)
    if res.beneficiary_id != actor.id and actor.role != UserRole.ADMIN:
        raise AppError("reservation.not_owner", 403)
    if res.status != ReservationStatus.PENDING:
        raise AppError("reservation.not_pending", 409)
    _release(db, res, ReservationStatus.CANCELLED, events.RESERVATION_CANCELLED, actor.id, reason="beneficiary")
    db.commit()
    return res


def cancel_pending_for_food(db: Session, food_id: int, actor_id: int | None) -> int:
    """Food was removed by the donor/admin: cancel its pending reservations. Does not commit."""
    pending = list(
        db.scalars(
            select(Reservation).where(Reservation.food_id == food_id, Reservation.status == ReservationStatus.PENDING)
        ).unique()
    )
    for res in pending:
        res.status = ReservationStatus.CANCELLED
        ctx_of(db).bus.publish(
            db, events.RESERVATION_CANCELLED, **_event_payload(res, actor_id, reason="food_cancelled")
        )
    return len(pending)


def _release(db: Session, res: Reservation, status: ReservationStatus, event: str, actor_id: int | None, **extra) -> None:
    res.status = status
    inventory.return_portions(db, res.food_id, res.portions)
    ctx_of(db).bus.publish(db, event, **_event_payload(res, actor_id, **extra))


def verify_pickup(db: Session, donor: User, code: str) -> VerifyOut:
    ctx = ctx_of(db)
    limiter_key = f"verify:{donor.id}"
    wait = ctx.verify_limiter.retry_after(limiter_key)
    if wait:
        raise AppError("auth.too_many_attempts", 429, seconds=wait)

    now = utcnow()
    candidate = qr.parse_payload(code)
    query = select(Reservation).where(
        Reservation.donor_id == donor.id,  # rule 1: only the owning donor's reservations are searchable
        Reservation.status == ReservationStatus.PENDING,
        Reservation.expires_at > now,
    )
    if candidate.isdigit() and len(candidate) == 6:
        query = query.where(Reservation.pin == candidate)
    else:
        query = query.where(Reservation.qr_token == candidate)
    res = db.scalars(query).unique().first()

    if res is None:
        ctx.verify_limiter.record_failure(limiter_key)  # rule 2
        raise AppError("reservation.code_not_found", 404)

    ctx.verify_limiter.reset(limiter_key)
    res.status = ReservationStatus.COLLECTED
    res.collected_at = now
    ctx.bus.publish(db, events.RESERVATION_COLLECTED, **_event_payload(res, donor.id))
    db.commit()
    return VerifyOut(
        reservation_id=res.id,
        food_title=res.food.title,
        portions=res.portions,
        beneficiary_label=res.beneficiary.public_label,
        collected_at=res.collected_at,
    )


def expire_due(db: Session, now: datetime) -> int:
    due = list(
        db.scalars(
            select(Reservation).where(Reservation.status == ReservationStatus.PENDING, Reservation.expires_at <= now)
        ).unique()
    )
    for res in due:
        _release(db, res, ReservationStatus.EXPIRED, events.RESERVATION_EXPIRED, None)
    db.commit()
    return len(due)


def to_my_out(res: Reservation) -> MyReservationOut:
    pending = res.status == ReservationStatus.PENDING
    return MyReservationOut(
        id=res.id,
        food_id=res.food_id,
        food_title=res.food.title,
        donor_name=res.donor.display_name,
        pickup_address=res.food.address,
        latitude=res.food.latitude,
        longitude=res.food.longitude,
        portions=res.portions,
        status=res.status,
        pin=res.pin if pending else None,
        qr_svg=qr.render_svg(qr.qr_payload(res.qr_token)) if pending else None,
        created_at=res.created_at,
        expires_at=res.expires_at,
        collected_at=res.collected_at,
    )


def to_donor_out(res: Reservation) -> DonorReservationOut:
    return DonorReservationOut(
        id=res.id,
        food_id=res.food_id,
        food_title=res.food.title,
        portions=res.portions,
        status=res.status,
        beneficiary_label=res.beneficiary.public_label,
        created_at=res.created_at,
        expires_at=res.expires_at,
        collected_at=res.collected_at,
    )

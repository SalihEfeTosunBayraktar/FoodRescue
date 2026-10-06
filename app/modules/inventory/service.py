"""Inventory use-cases.

Ders notu (eşzamanlılık): iki kişi son porsiyonu aynı anda rezerve etmeye çalışırsa ne olur?
"önce oku, sonra yaz" (SELECT sonra UPDATE) yaklaşımı yarış durumuna (race condition) açıktır.
`take_portions` koşulu UPDATE'in WHERE kısmına koyar; veritabanı satırı kilitleyip kontrolü ve
düşümü tek adımda yapar. Etkilenen satır sayısı (rowcount) 0 ise işlem başarısız olmuştur.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import case, select, update
from sqlalchemy.orm import Session

from app.config import events
from app.core.clock import utcnow
from app.core.context import ctx_of
from app.core.errors import AppError
from app.core.geo import haversine_km
from app.modules.identity.models import User, UserRole
from app.modules.inventory.models import FoodCategory, FoodItem, FoodStatus
from app.modules.inventory.schemas import FoodCreate, FoodOut, FoodUpdate

_IMAGE_SIGNATURES = (
    (b"\xff\xd8\xff", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
)


def to_out(food: FoodItem, distance_km: float | None = None) -> FoodOut:
    out = FoodOut.model_validate(
        {
            **{c.name: getattr(food, c.name) for c in FoodItem.__table__.columns},
            "donor_name": food.donor.display_name,
            "photo_url": f"/uploads/{food.photo_path}" if food.photo_path else None,
            "is_available": food.is_available,
            "distance_km": round(distance_km, 2) if distance_km is not None else None,
        }
    )
    return out


def create_food(db: Session, donor: User, data: FoodCreate) -> FoodItem:
    settings = ctx_of(db).settings
    if not data.hygiene_confirmed:
        raise AppError("food.hygiene_required", 422)
    now = utcnow()
    if data.pickup_until <= now:
        raise AppError("food.pickup_in_past", 422)
    if data.pickup_until > now + timedelta(hours=settings.max_pickup_window_hours):
        raise AppError("food.pickup_too_far", 422, hours=settings.max_pickup_window_hours)

    food = FoodItem(
        donor_id=donor.id,
        title=data.title.strip(),
        description=data.description,
        category=data.category,
        storage=data.storage,
        portions_total=data.portions_total,
        portions_left=data.portions_total,
        max_per_person=min(data.max_per_person, data.portions_total),
        pickup_until=data.pickup_until,
        address=data.address or donor.address or "",
        latitude=data.latitude if data.latitude is not None else donor.latitude,
        longitude=data.longitude if data.longitude is not None else donor.longitude,
        hygiene_confirmed=True,
    )
    db.add(food)
    db.flush()
    ctx_of(db).bus.publish(
        db, events.FOOD_PUBLISHED, actor_id=donor.id, entity_type="food", entity_id=food.id, title=food.title
    )
    db.commit()
    return food


def get_food(db: Session, food_id: int) -> FoodItem:
    food = db.get(FoodItem, food_id)
    if not food:
        raise AppError("food.not_found", 404)
    return food


def list_foods(
    db: Session,
    *,
    category: FoodCategory | None = None,
    q: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float | None = None,
    include_unavailable: bool = False,
) -> list[tuple[FoodItem, float | None]]:
    query = select(FoodItem).order_by(FoodItem.pickup_until.asc())
    if not include_unavailable:
        query = query.where(
            FoodItem.status == FoodStatus.AVAILABLE, FoodItem.portions_left > 0, FoodItem.pickup_until > utcnow()
        )
    if category:
        query = query.where(FoodItem.category == category)
    if q:
        like = f"%{q.strip()}%"
        query = query.where(FoodItem.title.ilike(like) | FoodItem.description.ilike(like))

    foods = list(db.scalars(query).unique())
    if lat is None or lon is None:
        return [(food, None) for food in foods]

    # Distance is computed in Python (haversine). With PostgreSQL this becomes a PostGIS ST_DWithin query.
    ranked = [(food, haversine_km(lat, lon, food.latitude, food.longitude)) for food in foods]
    if radius_km is not None:
        ranked = [(food, dist) for food, dist in ranked if dist <= radius_km]
    return sorted(ranked, key=lambda pair: pair[1])


def donor_foods(db: Session, donor: User) -> list[FoodItem]:
    query = select(FoodItem).where(FoodItem.donor_id == donor.id).order_by(FoodItem.created_at.desc())
    return list(db.scalars(query).unique())


def _owned_food(db: Session, actor: User, food_id: int) -> FoodItem:
    food = get_food(db, food_id)
    if food.donor_id != actor.id and actor.role != UserRole.ADMIN:
        raise AppError("food.not_owner", 403)
    return food


def update_food(db: Session, donor: User, food_id: int, data: FoodUpdate) -> FoodItem:
    food = _owned_food(db, donor, food_id)
    if food.status != FoodStatus.AVAILABLE:
        raise AppError("food.not_editable", 409)
    if data.title is not None:
        food.title = data.title.strip()
    if data.description is not None:
        food.description = data.description
    if data.pickup_until is not None:
        settings = ctx_of(db).settings
        now = utcnow()
        if data.pickup_until <= now:
            raise AppError("food.pickup_in_past", 422)
        if data.pickup_until > now + timedelta(hours=settings.max_pickup_window_hours):
            raise AppError("food.pickup_too_far", 422, hours=settings.max_pickup_window_hours)
        food.pickup_until = data.pickup_until
    db.commit()
    return food


def cancel_food(db: Session, actor: User, food_id: int) -> FoodItem:
    food = _owned_food(db, actor, food_id)
    if food.status != FoodStatus.AVAILABLE:
        raise AppError("food.not_editable", 409)
    _cancel(db, food, actor.id)
    db.commit()
    return food


def cancel_all_for_donor(db: Session, donor_id: int, actor_id: int | None) -> int:
    """Called when a donor is suspended. Does not commit (runs inside the publisher's transaction)."""
    foods = db.scalars(
        select(FoodItem).where(FoodItem.donor_id == donor_id, FoodItem.status == FoodStatus.AVAILABLE)
    ).unique()
    count = 0
    for food in foods:
        _cancel(db, food, actor_id)
        count += 1
    return count


def _cancel(db: Session, food: FoodItem, actor_id: int | None) -> None:
    food.status = FoodStatus.CANCELLED
    ctx_of(db).bus.publish(
        db, events.FOOD_CANCELLED, actor_id=actor_id, entity_type="food", entity_id=food.id, food_id=food.id
    )


def save_photo(db: Session, donor: User, food_id: int, upload: UploadFile) -> FoodItem:
    settings = ctx_of(db).settings
    food = _owned_food(db, donor, food_id)
    content = upload.file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise AppError("food.image_too_large", 413, mb=settings.max_upload_bytes // (1024 * 1024))

    # Never trust the client's file name or Content-Type: sniff the magic bytes instead.
    extension = next((ext for sig, ext in _IMAGE_SIGNATURES if content.startswith(sig)), None)
    if extension is None and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        extension = ".webp"
    if extension is None:
        raise AppError("food.bad_image", 415)

    relative = Path("foods") / f"{uuid.uuid4().hex}{extension}"
    target = settings.upload_dir / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    food.photo_path = relative.as_posix()
    db.commit()
    return food


def take_portions(db: Session, food_id: int, count: int, now: datetime | None = None) -> FoodItem:
    """Atomically reserve `count` portions or raise. Does not commit."""
    now = now or utcnow()
    result = db.execute(
        update(FoodItem)
        .where(
            FoodItem.id == food_id,
            FoodItem.status == FoodStatus.AVAILABLE,
            FoodItem.portions_left >= count,
            FoodItem.pickup_until > now,
        )
        .values(portions_left=FoodItem.portions_left - count)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        if db.get(FoodItem, food_id) is None:
            raise AppError("food.not_found", 404)
        raise AppError("food.unavailable", 409)
    food = get_food(db, food_id)
    db.refresh(food, attribute_names=["portions_left"])  # the raw UPDATE bypassed the identity map
    return food


def return_portions(db: Session, food_id: int, count: int) -> None:
    """Give portions back (cancelled or expired reservation). Never exceeds portions_total. Does not commit."""
    db.execute(
        update(FoodItem)
        .where(FoodItem.id == food_id)
        .values(
            portions_left=case(
                (FoodItem.portions_left + count > FoodItem.portions_total, FoodItem.portions_total),
                else_=FoodItem.portions_left + count,
            )
        )
        .execution_options(synchronize_session=False)
    )


def expire_due(db: Session, now: datetime) -> int:
    foods = list(
        db.scalars(select(FoodItem).where(FoodItem.status == FoodStatus.AVAILABLE, FoodItem.pickup_until <= now)).unique()
    )
    for food in foods:
        food.status = FoodStatus.EXPIRED
        ctx_of(db).bus.publish(
            db, events.FOOD_EXPIRED, actor_id=None, entity_type="food", entity_id=food.id, food_id=food.id
        )
    db.commit()
    return len(foods)


def category_for_role(role: UserRole) -> FoodCategory | None:
    return {UserRole.BENEFICIARY: FoodCategory.HUMAN, UserRole.SHELTER: FoodCategory.ANIMAL}.get(role)

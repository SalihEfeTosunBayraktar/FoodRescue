from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.identity.deps import active_user, current_user
from app.modules.identity.models import User, UserRole
from app.modules.inventory import service
from app.modules.inventory.models import FoodCategory
from app.modules.inventory.schemas import FoodCreate, FoodOut, FoodUpdate

router = APIRouter(prefix="/api/v1/foods", tags=["inventory"])

_donor = active_user(UserRole.DONOR)


@router.get("", response_model=list[FoodOut])
def list_foods(
    category: FoodCategory | None = None,
    q: str | None = Query(default=None, max_length=100),
    lat: float | None = Query(default=None, ge=-90, le=90),
    lon: float | None = Query(default=None, ge=-180, le=180),
    radius_km: float | None = Query(default=None, gt=0, le=200),
    db: Session = Depends(get_db),
):
    """Public: visitors can browse live donations without an account."""
    rows = service.list_foods(db, category=category, q=q, lat=lat, lon=lon, radius_km=radius_km)
    return [service.to_out(food, distance) for food, distance in rows]


@router.get("/mine", response_model=list[FoodOut])
def my_foods(donor: User = Depends(_donor), db: Session = Depends(get_db)):
    return [service.to_out(food) for food in service.donor_foods(db, donor)]


@router.get("/{food_id}", response_model=FoodOut)
def get_food(food_id: int, db: Session = Depends(get_db)):
    return service.to_out(service.get_food(db, food_id))


@router.post("", response_model=FoodOut, status_code=201)
def create_food(payload: FoodCreate, donor: User = Depends(_donor), db: Session = Depends(get_db)):
    return service.to_out(service.create_food(db, donor, payload))


@router.patch("/{food_id}", response_model=FoodOut)
def update_food(food_id: int, payload: FoodUpdate, donor: User = Depends(_donor), db: Session = Depends(get_db)):
    return service.to_out(service.update_food(db, donor, food_id, payload))


@router.delete("/{food_id}", response_model=FoodOut)
def cancel_food(food_id: int, actor: User = Depends(current_user), db: Session = Depends(get_db)):
    return service.to_out(service.cancel_food(db, actor, food_id))


@router.post("/{food_id}/photo", response_model=FoodOut)
def upload_photo(
    food_id: int, file: UploadFile = File(...), donor: User = Depends(_donor), db: Session = Depends(get_db)
):
    return service.to_out(service.save_photo(db, donor, food_id, file))

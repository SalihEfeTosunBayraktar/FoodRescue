from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.identity.deps import active_user, current_user
from app.modules.identity.models import User, UserRole
from app.modules.reservation import service
from app.modules.reservation.models import ReservationStatus
from app.modules.reservation.schemas import (
    DonorReservationOut,
    MyReservationOut,
    ReservationCreate,
    VerifyIn,
    VerifyOut,
)

router = APIRouter(prefix="/api/v1/reservations", tags=["reservation"])

_receiver = active_user(UserRole.BENEFICIARY, UserRole.SHELTER)
_donor = active_user(UserRole.DONOR)


@router.post("", response_model=MyReservationOut, status_code=201)
def create(payload: ReservationCreate, user: User = Depends(_receiver), db: Session = Depends(get_db)):
    return service.to_my_out(service.create_reservation(db, user, payload))


@router.get("/mine", response_model=list[MyReservationOut])
def mine(user: User = Depends(_receiver), db: Session = Depends(get_db)):
    return [service.to_my_out(res) for res in service.my_reservations(db, user)]


@router.get("/incoming", response_model=list[DonorReservationOut])
def incoming(status: ReservationStatus | None = None, donor: User = Depends(_donor), db: Session = Depends(get_db)):
    return [service.to_donor_out(res) for res in service.donor_reservations(db, donor, status)]


@router.post("/verify", response_model=VerifyOut)
def verify(payload: VerifyIn, donor: User = Depends(_donor), db: Session = Depends(get_db)):
    return service.verify_pickup(db, donor, payload.code)


@router.post("/{reservation_id}/cancel", response_model=MyReservationOut)
def cancel(reservation_id: int, actor: User = Depends(current_user), db: Session = Depends(get_db)):
    return service.to_my_out(service.cancel_reservation(db, actor, reservation_id))

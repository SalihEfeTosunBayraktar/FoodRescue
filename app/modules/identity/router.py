from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.identity import service
from app.modules.identity.deps import current_user, require_admin
from app.modules.identity.models import AccountStatus, User, UserRole
from app.modules.identity.schemas import LoginIn, ReasonIn, RegisterIn, ReviewIn, TokenOut, UserOut

auth_router = APIRouter(prefix="/api/v1/auth", tags=["identity"])
admin_router = APIRouter(prefix="/api/v1/admin/accounts", tags=["identity-admin"])


@auth_router.post("/register", response_model=UserOut, status_code=201)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    return service.register(db, payload)


@auth_router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user, token = service.authenticate(db, payload.email, payload.password)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@auth_router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@admin_router.get("", response_model=list[UserOut])
def list_accounts(
    status: AccountStatus | None = None,
    role: UserRole | None = None,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return service.list_accounts(db, status, role)


@admin_router.post("/{user_id}/review", response_model=UserOut)
def review(user_id: int, payload: ReviewIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return service.review_account(db, admin, user_id, payload.decision == "APPROVE", payload.note)


@admin_router.post("/{user_id}/suspend", response_model=UserOut)
def suspend(user_id: int, payload: ReasonIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return service.suspend_account_by_admin(db, admin, user_id, payload.reason)


@admin_router.post("/{user_id}/reinstate", response_model=UserOut)
def reinstate(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return service.reinstate_account(db, admin, user_id)

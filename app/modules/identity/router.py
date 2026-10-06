from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.identity import service
from app.modules.identity.deps import current_user, require_admin
from app.modules.identity.models import AccountStatus, User, UserRole
from app.modules.identity.schemas import LoginIn, ReasonIn, RegisterIn, ReviewIn, TokenOut, UserOut

# APIRouter: bir modülün uç noktalarını gruplar. prefix ortak yol başlangıcıdır; tags /docs
# sayfasında gruplama sağlar.
auth_router = APIRouter(prefix="/api/v1/auth", tags=["identity"])
# Yönetici uç noktaları ayrı bir router'dadır: yetki gereksinimi grup düzeyinde kolayca okunur.
admin_router = APIRouter(prefix="/api/v1/admin/accounts", tags=["identity-admin"])


# Router ince tutulur: şemayı doğrulatır, servisi çağırır, sonucu şemaya çevirir. İş kuralı burada
# yok.
@auth_router.post("/register", response_model=UserOut, status_code=201)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    return service.register(db, payload)


# Başarılı girişte bilet ve kullanıcı birlikte döner; ön yüz ikinci bir istek yapmaz.
@auth_router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user, token = service.authenticate(db, payload.email, payload.password)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


# Biletle 'ben kimim?' sorusu. Ön yüz açılışta bunu çağırıp rol ve durumu tazeler (örn. hesap
# onaylandı mı?).
@auth_router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


# Yalnızca yönetici. Parametreler `?status=PENDING_REVIEW` gibi sorgu dizisinden gelir.
@admin_router.get("", response_model=list[UserOut])
def list_accounts(
    status: AccountStatus | None = None,
    role: UserRole | None = None,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return service.list_accounts(db, status, role)


# Yol parametresi {user_id} fonksiyona otomatik aktarılır.
@admin_router.post("/{user_id}/review", response_model=UserOut)
def review(user_id: int, payload: ReviewIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return service.review_account(db, admin, user_id, payload.decision == "APPROVE", payload.note)


# Askıya alma gerekçe ister (ReasonIn).
@admin_router.post("/{user_id}/suspend", response_model=UserOut)
def suspend(user_id: int, payload: ReasonIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return service.suspend_account_by_admin(db, admin, user_id, payload.reason)


# Askıyı kaldırır.
@admin_router.post("/{user_id}/reinstate", response_model=UserOut)
def reinstate(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return service.reinstate_account(db, admin, user_id)

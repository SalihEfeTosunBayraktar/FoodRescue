"""Identity use-cases. This layer owns transactions: each public function commits once.

Ders notu (katmanlar): router -> service -> model. Router HTTP'yi, service iş kuralını,
model veriyi bilir. Böylece iş kuralları HTTP olmadan da test edilebilir.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import events
from app.core.clock import utcnow
from app.core.context import ctx_of
from app.core.errors import AppError
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.identity.models import REVIEWED_ROLES, AccountStatus, User, UserRole
from app.modules.identity.schemas import SELF_REGISTER_ROLES, RegisterIn

# Pre-computed once so that unknown e-mails cost the same time as wrong passwords.
_DUMMY_HASH = hash_password("timing-equalizer")


def register(db: Session, data: RegisterIn) -> User:
    if data.role not in SELF_REGISTER_ROLES:
        raise AppError("auth.role_not_allowed", 403)
    status = AccountStatus.PENDING_REVIEW if data.role in REVIEWED_ROLES else AccountStatus.ACTIVE
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name.strip(),
        role=data.role,
        status=status,
        phone=data.phone,
        organization_name=data.organization_name,
        license_number=data.license_number,
        address=data.address,
        latitude=data.latitude,
        longitude=data.longitude,
    )
    db.add(user)
    try:
        db.flush()  # assigns user.id and surfaces the UNIQUE(email) violation early
    except IntegrityError as exc:
        db.rollback()
        raise AppError("auth.email_taken", 409) from exc
    ctx_of(db).bus.publish(
        db, events.ACCOUNT_REGISTERED, actor_id=user.id, entity_type="user", entity_id=user.id, role=user.role.value
    )
    db.commit()
    return user


def authenticate(db: Session, email: str, password: str) -> tuple[User, str]:
    ctx = ctx_of(db)
    limiter = ctx.login_limiter
    wait = limiter.retry_after(email)
    if wait:
        raise AppError("auth.too_many_attempts", 429, seconds=wait)

    user = db.scalar(select(User).where(User.email == email))
    # Always run one hash verification, even for unknown e-mails (prevents user enumeration by timing).
    valid = verify_password(password, user.password_hash if user else _DUMMY_HASH)
    if not user or not valid:
        limiter.record_failure(email)
        raise AppError("auth.invalid_credentials", 401)

    limiter.reset(email)
    if user.status == AccountStatus.REJECTED:
        raise AppError("auth.account_rejected", 403)
    if user.status == AccountStatus.SUSPENDED:
        raise AppError("auth.account_suspended", 403)
    token = create_access_token(ctx.settings.secret_key, user.id, user.role.value, ctx.settings.token_ttl_minutes)
    return user, token


def get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user:
        raise AppError("account.not_found", 404)
    return user


def list_accounts(db: Session, status: AccountStatus | None = None, role: UserRole | None = None) -> list[User]:
    query = select(User).order_by(User.created_at.desc())
    if status:
        query = query.where(User.status == status)
    if role:
        query = query.where(User.role == role)
    return list(db.scalars(query))


def review_account(db: Session, admin: User, user_id: int, approve: bool, note: str | None) -> User:
    user = get_user(db, user_id)
    if user.status != AccountStatus.PENDING_REVIEW:
        raise AppError("account.invalid_state", 409)
    user.status = AccountStatus.ACTIVE if approve else AccountStatus.REJECTED
    user.review_note = note
    user.reviewed_at = utcnow()
    ctx_of(db).bus.publish(
        db,
        events.ACCOUNT_REVIEWED,
        actor_id=admin.id,
        entity_type="user",
        entity_id=user.id,
        user_id=user.id,
        approved=approve,
        note=note or "-",
    )
    db.commit()
    return user


def suspend_account(db: Session, user: User, reason: str, actor_id: int | None) -> User:
    """Used by admins and by the complaint workflow. Does not commit when called inside another use-case."""
    if user.role == UserRole.ADMIN:
        raise AppError("account.invalid_state", 409)
    user.status = AccountStatus.SUSPENDED
    user.review_note = reason
    ctx_of(db).bus.publish(
        db, events.ACCOUNT_SUSPENDED, actor_id=actor_id, entity_type="user", entity_id=user.id, user_id=user.id, reason=reason
    )
    return user


def suspend_account_by_admin(db: Session, admin: User, user_id: int, reason: str) -> User:
    user = suspend_account(db, get_user(db, user_id), reason, admin.id)
    db.commit()
    return user


def reinstate_account(db: Session, admin: User, user_id: int) -> User:
    user = get_user(db, user_id)
    if user.status != AccountStatus.SUSPENDED:
        raise AppError("account.invalid_state", 409)
    user.status = AccountStatus.ACTIVE
    ctx_of(db).bus.publish(
        db, events.ACCOUNT_REINSTATED, actor_id=admin.id, entity_type="user", entity_id=user.id, user_id=user.id
    )
    db.commit()
    return user

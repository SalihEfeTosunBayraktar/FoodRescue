"""FastAPI dependencies other modules reuse to authenticate and authorize requests.

Ders notu: `Depends` bir "bağımlılık enjeksiyonu" mekanizmasıdır. Endpoint, kimin çağırdığını
kendisi çözmez; hazır çözülmüş `User` nesnesini parametre olarak alır.
"""
from __future__ import annotations

from typing import Callable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.modules.identity.models import AccountStatus, User, UserRole

_bearer = HTTPBearer(auto_error=False)


def optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User | None:
    if credentials is None:
        return None
    claims = decode_access_token(request.app.state.ctx.settings.secret_key, credentials.credentials)
    user = db.get(User, int(claims["sub"]))
    if user is None:
        raise AppError("auth.invalid_token", 401)
    if user.status == AccountStatus.SUSPENDED:
        raise AppError("auth.account_suspended", 403)
    if user.status == AccountStatus.REJECTED:
        raise AppError("auth.account_rejected", 403)
    return user


def current_user(user: User | None = Depends(optional_user)) -> User:
    if user is None:
        raise AppError("auth.missing_token", 401)
    return user


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    def dependency(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise AppError("auth.forbidden", 403)
        return user

    return dependency


def active_user(*roles: UserRole) -> Callable[[User], User]:
    """Role check plus: the account must be ACTIVE (approved)."""
    role_check = require_roles(*roles)

    def dependency(user: User = Depends(role_check)) -> User:
        if user.status != AccountStatus.ACTIVE:
            key = "donor.not_approved" if user.role == UserRole.DONOR else "account.not_active"
            raise AppError(key, 403)
        return user

    return dependency


require_admin = require_roles(UserRole.ADMIN)

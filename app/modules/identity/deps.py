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

# HTTPBearer: 'Authorization: Bearer <bilet>' başlığını okur. auto_error=False: başlık yoksa hemen
# hata vermez; hatayı biz kendi mesajımızla veririz.
_bearer = HTTPBearer(auto_error=False)


# Giriş yapmış kullanıcıyı çözer; giriş yoksa None döner. Herkese açık ama girişliyken farklı
# davranan uç noktalar için.
def optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User | None:
    # Başlık yoksa anonim ziyaretçi.
    if credentials is None:
        return None
    # İmza ve süre doğrulanır; geçersizse burada 401 fırlar.
    claims = decode_access_token(request.app.state.ctx.settings.secret_key, credentials.credentials)
    # Bilet geçerli olsa bile kullanıcı silinmiş olabilir; her istekte güncel kaydı veritabanından
    # okuruz.
    user = db.get(User, int(claims["sub"]))
    # Biletin kullanıcısı artık yok.
    if user is None:
        raise AppError("auth.invalid_token", 401)
    # Askıya alınan kullanıcının eski bileti hâlâ geçerli görünür; bu yüzden durumu her istekte
    # kontrol ederiz (JWT'nin bilinen zayıflığı: bileti iptal edemeyiz).
    if user.status == AccountStatus.SUSPENDED:
        raise AppError("auth.account_suspended", 403)
    if user.status == AccountStatus.REJECTED:
        raise AppError("auth.account_rejected", 403)
    return user


# Giriş ZORUNLU olan uç noktalar için bağımlılık. Başka bir bağımlılığa dayanır (Depends zinciri).
def current_user(user: User | None = Depends(optional_user)) -> User:
    if user is None:
        raise AppError("auth.missing_token", 401)
    return user


# Fabrika fonksiyon: izin verilen rolleri alıp bir bağımlılık fonksiyonu üretir (closure). Kullanım:
# `Depends(require_roles(UserRole.ADMIN))`.
def require_roles(*roles: UserRole) -> Callable[[User], User]:
    # Giriş yapılmış mı VE rolü uygun mu? Değilse 403 Forbidden.
    def dependency(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise AppError("auth.forbidden", 403)
        return user

    return dependency


# Rol kontrolüne ek olarak hesabın ACTIVE (onaylı) olmasını ister. İlan ve rezervasyon uç noktaları
# bunu kullanır.
def active_user(*roles: UserRole) -> Callable[[User], User]:
    """Role check plus: the account must be ACTIVE (approved)."""
    # Önce rol kontrolü; sonra durum kontrolü (iç içe bağımlılık).
    role_check = require_roles(*roles)

    # Rolü doğru ama hesabı henüz onaylanmamış kullanıcı için anlamlı hata anahtarı seçilir.
    def dependency(user: User = Depends(role_check)) -> User:
        if user.status != AccountStatus.ACTIVE:
            key = "donor.not_approved" if user.role == UserRole.DONOR else "account.not_active"
            raise AppError(key, 403)
        return user

    return dependency


# Sık kullanıldığı için hazır bir kısayol.
require_admin = require_roles(UserRole.ADMIN)

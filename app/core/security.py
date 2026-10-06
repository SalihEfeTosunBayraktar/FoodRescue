from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import timedelta
from typing import Any

import jwt

from app.core.clock import utcnow
from app.core.errors import AppError

# scrypt maliyet ayarları: n = işlemci/bellek maliyeti, r = blok boyutu, p = paralellik.
# Artırırsanız saldırganın deneme hızı da düşer, ama giriş de yavaşlar.
_SCRYPT = {"n": 2**14, "r": 8, "p": 1, "dklen": 32}
_ALGORITHM = "HS256"


# Parolayı geri çevrilemeyen bir özete (hash) dönüştürür. Düz parola hiçbir yerde saklanmaz.
def hash_password(password: str) -> str:
    # Salt: her parola için rastgele değer. Aynı parolayı kullanan iki kullanıcının hash'i farklı
    # çıkar ve hazır hash tabloları (rainbow table) işe yaramaz.
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    # Saklama biçimi algoritma$salt$hash. Algoritmayı kayda yazmak, ileride ayarı değiştirince eski
    # kayıtları tanımamızı sağlar.
    return f"scrypt${salt.hex()}${digest.hex()}"


# Girilen parolayı kayıtlı özetle karşılaştırır. Aynı salt ile yeniden hash'leyip sonuçlara bakarız.
def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    if scheme != "scrypt":
        return False
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), **_SCRYPT)
    # Sabit zamanlı karşılaştırma. Normal == ilk farklı karakterde durur; süre farkından hash tahmin
    # edilebilir (zamanlama saldırısı).
    return hmac.compare_digest(digest.hex(), digest_hex)


# JWT (JSON Web Token): sunucunun imzaladığı, süresi olan kimlik bileti. Sunucu oturum hatırlamaz;
# her istekte gelen bileti imzasından doğrular.
def create_access_token(secret: str, user_id: int, role: str, ttl_minutes: int) -> str:
    now = utcnow()
    # Bilet içeriği (claims): sub = kullanıcı no, role = rol, iat = üretim zamanı, exp = bitiş.
    # Token İMZALIDIR ama ŞİFRELİ DEĞİLDİR: içine parola gibi sır koymayın.
    claims = {"sub": str(user_id), "role": role, "iat": now, "exp": now + timedelta(minutes=ttl_minutes)}
    return jwt.encode(claims, secret, algorithm=_ALGORITHM)


# Süresi dolmuş, imzası bozuk veya sahte bilet PyJWTError fırlatır; hepsini tek bir iş hatasına
# çeviririz.
def decode_access_token(secret: str, token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, secret, algorithms=[_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise AppError("auth.invalid_token", 401) from exc


# randbelow(900000) + 100000 = 100000..999999: baş hanesi sıfır olmayan 6 hane. `secrets` işletim
# sisteminin güvenli rastgeleliğini kullanır; `random` modülü tahmin edilebilir olduğu için kod
# üretiminde kullanılmaz.
def random_pin() -> str:
    return f"{secrets.randbelow(900000) + 100000}"


# 24 bayt = 192 bit rastgelelik. URL'de güvenle taşınabilen metin üretir (QR içeriği).
def random_token() -> str:
    return secrets.token_urlsafe(24)

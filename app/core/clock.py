from __future__ import annotations

from datetime import datetime, timezone


# Neden saat dilimli (aware) tarih? Saat dilimsiz (naive) bir tarih hangi dilimde olduğunu bilmez;
# iki sunucu arasında sessizce yanlış karşılaştırma üretir. Projede her zaman UTC kullanırız,
# ekranda tarayıcı yerel saate çevirir.
def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Dışarıdan gelen tarih saat dilimsizse UTC varsayarız, dilimliyse UTC'ye çeviririz. Böylece
# veritabanına her zaman tek biçim girer.
def ensure_utc(value: datetime) -> datetime:
    """Naive datetimes are interpreted as UTC; aware ones are converted."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

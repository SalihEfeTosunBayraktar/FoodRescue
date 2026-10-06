from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config.settings import Settings
from app.core.events import EventBus
from app.core.mailer import LogMailer, Mailer
from app.core.ratelimit import FailureLimiter


# Uygulama genelinde paylaşılan nesneler (ayarlar, olay yolu, sınırlayıcılar, posta). Global
# değişken yerine bu paket kullanılır; her test kendi bağlamını kurduğu için testler birbirini
# etkilemez.
@dataclass
class AppContext:
    """Per-application collaborators. Reachable from any Session via ctx_of(db)."""

    settings: Settings
    bus: EventBus
    login_limiter: FailureLimiter
    verify_limiter: FailureLimiter
    mailer: Mailer


# Bağlamı ayarlardan kurar. Üretimde LogMailer yerine SMTP sınıfı burada bağlanır.
def build_context(settings: Settings) -> AppContext:
    return AppContext(
        settings=settings,
        bus=EventBus(),
        login_limiter=FailureLimiter(settings.login_max_failures, settings.login_window_seconds),
        verify_limiter=FailureLimiter(settings.verify_max_failures, settings.verify_window_seconds),
        mailer=LogMailer(),
    )


# Session nesnesine eklenmiş bilgiden bağlama ulaşır (Database.session() ekler). Servis
# fonksiyonları böylece HTTP isteğini bilmeden ayarlara erişir.
def ctx_of(db: Session) -> AppContext:
    return db.info["ctx"]

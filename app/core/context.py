from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config.settings import Settings
from app.core.events import EventBus
from app.core.mailer import LogMailer, Mailer
from app.core.ratelimit import FailureLimiter


@dataclass
class AppContext:
    """Per-application collaborators. Reachable from any Session via ctx_of(db)."""

    settings: Settings
    bus: EventBus
    login_limiter: FailureLimiter
    verify_limiter: FailureLimiter
    mailer: Mailer


def build_context(settings: Settings) -> AppContext:
    return AppContext(
        settings=settings,
        bus=EventBus(),
        login_limiter=FailureLimiter(settings.login_max_failures, settings.login_window_seconds),
        verify_limiter=FailureLimiter(settings.verify_max_failures, settings.verify_window_seconds),
        mailer=LogMailer(),
    )


def ctx_of(db: Session) -> AppContext:
    return db.info["ctx"]

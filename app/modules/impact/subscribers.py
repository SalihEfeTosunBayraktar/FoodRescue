from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.events import EventBus
from app.modules.impact import service


# Her olayı kayda geçirir. Modüller denetim kaydından habersizdir; olayı yayınlamak yeterlidir.
def _audit_everything(db: Session, event: str, payload: dict[str, Any]) -> None:
    service.record_audit(db, event, payload)


# subscribe_all: tüm olay adlarını dinler.
def subscribe(bus: EventBus) -> None:
    bus.subscribe_all(_audit_everything)

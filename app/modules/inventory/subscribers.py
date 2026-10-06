"""Reactions to other modules' events."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.config import events
from app.core.events import EventBus
from app.modules.inventory import service


# Başka modülün olayına tepki: askıya alınan bağışçının ilanları kaldırılır. Identity modülü
# inventory'yi bilmez, yalnızca 'hesap askıya alındı' diye duyurur.
def _on_account_suspended(db: Session, _event: str, payload: dict[str, Any]) -> None:
    service.cancel_all_for_donor(db, payload["user_id"], payload.get("actor_id"))


# Dinleyicileri olay yoluna kaydeder; app/main.py açılışta çağırır.
def subscribe(bus: EventBus) -> None:
    bus.subscribe(events.ACCOUNT_SUSPENDED, _on_account_suspended)

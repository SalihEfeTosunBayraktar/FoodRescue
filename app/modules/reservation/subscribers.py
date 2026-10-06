from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.config import events
from app.core.events import EventBus
from app.modules.reservation import service


# İlan kaldırıldığında bekleyen rezervasyonlar iptal olur. Inventory modülü reservation'ı hiç
# tanımaz.
def _on_food_cancelled(db: Session, _event: str, payload: dict[str, Any]) -> None:
    service.cancel_pending_for_food(db, payload["food_id"], payload.get("actor_id"))


# Dinleyiciyi olay yoluna kaydeder.
def subscribe(bus: EventBus) -> None:
    bus.subscribe(events.FOOD_CANCELLED, _on_food_cancelled)

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.config import events
from app.core.events import EventBus
from app.modules.reservation import service


def _on_food_cancelled(db: Session, _event: str, payload: dict[str, Any]) -> None:
    service.cancel_pending_for_food(db, payload["food_id"], payload.get("actor_id"))


def subscribe(bus: EventBus) -> None:
    bus.subscribe(events.FOOD_CANCELLED, _on_food_cancelled)

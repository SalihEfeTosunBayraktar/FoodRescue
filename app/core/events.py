"""Synchronous in-process event bus. Handlers run inside the publisher's transaction."""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable

from sqlalchemy.orm import Session

Handler = Callable[[Session, str, dict[str, Any]], None]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)
        self._global: list[Handler] = []

    def subscribe(self, event: str, handler: Handler) -> None:
        self._handlers[event].append(handler)

    def subscribe_all(self, handler: Handler) -> None:
        self._global.append(handler)

    def publish(self, db: Session, event: str, **payload: Any) -> None:
        for handler in (*self._handlers.get(event, ()), *self._global):
            handler(db, event, payload)

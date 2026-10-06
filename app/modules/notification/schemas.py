from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


# Tek bildirim yanıtı.
class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    title: str
    body: str
    created_at: datetime
    read_at: datetime | None


# Liste + okunmamış sayacı birlikte döner: zil simgesi için ayrı istek gerekmez.
class NotificationList(BaseModel):
    unread: int
    items: list[NotificationOut]

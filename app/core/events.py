"""Synchronous in-process event bus. Handlers run inside the publisher's transaction."""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable

from sqlalchemy.orm import Session

# Dinleyicinin imzası: (veritabanı oturumu, olay adı, yük sözlüğü) alır, bir şey döndürmez.
Handler = Callable[[Session, str, dict[str, Any]], None]


# Yayınla/abone ol (publish/subscribe) deseninin en küçük hali. Yayıncı kimin dinlediğini, dinleyici
# kimin yayınladığını bilmez. Bu 'gevşek bağlılık' modülleri birbirinden bağımsız tutar: reservation
# modülü notification modülünü hiç import etmez.
class EventBus:
    def __init__(self) -> None:
        # olay adı -> o olayı dinleyen fonksiyonların listesi. defaultdict: olmayan anahtar
        # istenince boş liste üretir, 'anahtar var mı?' kontrolü gerekmez.
        self._handlers: dict[str, list[Handler]] = defaultdict(list)
        # Her olayı dinleyenler (denetim kaydı gibi).
        self._global: list[Handler] = []

    # Belirli bir olaya abone ol.
    def subscribe(self, event: str, handler: Handler) -> None:
        self._handlers[event].append(handler)

    # Her olaya abone ol.
    def subscribe_all(self, handler: Handler) -> None:
        self._global.append(handler)

    # Olayı yayınlar. Dinleyiciler SENKRON ve yayıncının veritabanı oturumu içinde çalışır; bu
    # yüzden tek işlem (transaction) olarak ya hep ya hiç kaydedilir.
    def publish(self, db: Session, event: str, **payload: Any) -> None:
        # Önce olaya özel dinleyiciler, sonra genel dinleyiciler çalışır.
        for handler in (*self._handlers.get(event, ()), *self._global):
            handler(db, event, payload)

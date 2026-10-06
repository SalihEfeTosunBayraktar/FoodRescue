from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from importlib import import_module
from typing import Callable

from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.core.events import EventBus


# frozen=True: nesne oluşturulduktan sonra değiştirilemez (değişmez nesne). Yanlışlıkla ayar
# bozulmaz.
@dataclass(frozen=True)
# Bir modülün 'kartviziti': adı, router'ları, olay dinleyicileri, zamanlı işi. Uygulama modülün
# içini bilmez, yalnızca bu kartviziti okur (açık/kapalı ilkesi): yeni modül eklemek mevcut kodu
# değiştirmez.
class ModuleSpec:
    """What a module exposes to the application. Each module defines SPEC in its module.py."""

    name: str
    routers: tuple[APIRouter, ...]
    # Modülün olay dinleyicilerini kaydeden fonksiyon (isteğe bağlı).
    subscribe: Callable[[EventBus], None] | None = None
    # Periyodik çalışan iş (isteğe bağlı), ör. süresi dolan rezervasyonları kapatma.
    on_tick: Callable[[Session, datetime], None] | None = None


# import_module: modül adını metin olarak verip çalışma anında yükler. Ayarlardaki enabled_modules
# listesinden bir ad çıkarmak o modülü tamamen devre dışı bırakır.
def load_modules(names: tuple[str, ...]) -> list[ModuleSpec]:
    return [import_module(f"app.modules.{name}.module").SPEC for name in names]

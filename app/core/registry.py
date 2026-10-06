from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from importlib import import_module
from typing import Callable

from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.core.events import EventBus


@dataclass(frozen=True)
class ModuleSpec:
    """What a module exposes to the application. Each module defines SPEC in its module.py."""

    name: str
    routers: tuple[APIRouter, ...]
    subscribe: Callable[[EventBus], None] | None = None
    on_tick: Callable[[Session, datetime], None] | None = None


def load_modules(names: tuple[str, ...]) -> list[ModuleSpec]:
    return [import_module(f"app.modules.{name}.module").SPEC for name in names]

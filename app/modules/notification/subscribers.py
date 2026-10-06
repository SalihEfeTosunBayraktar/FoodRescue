"""Maps domain events to notifications. The only place that knows who should be told what."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.config import events
from app.core.events import EventBus
from app.modules.notification.service import notify


def _on_account_reviewed(db: Session, _e: str, p: dict[str, Any]) -> None:
    kind = "account.approved" if p["approved"] else "account.rejected"
    notify(db, p["user_id"], kind, note=p["note"])


def _on_account_suspended(db: Session, _e: str, p: dict[str, Any]) -> None:
    notify(db, p["user_id"], "account.suspended", reason=p["reason"])


def _on_reservation_created(db: Session, _e: str, p: dict[str, Any]) -> None:
    notify(db, p["donor_id"], "reservation.created.donor", **_fields(p))


def _on_reservation_collected(db: Session, _e: str, p: dict[str, Any]) -> None:
    notify(db, p["beneficiary_id"], "reservation.collected.beneficiary", **_fields(p))


def _on_reservation_expired(db: Session, _e: str, p: dict[str, Any]) -> None:
    notify(db, p["beneficiary_id"], "reservation.expired.beneficiary", **_fields(p))


def _on_reservation_cancelled(db: Session, _e: str, p: dict[str, Any]) -> None:
    if p.get("reason") == "food_cancelled":
        notify(db, p["beneficiary_id"], "reservation.cancelled.beneficiary", **_fields(p))
    else:
        notify(db, p["donor_id"], "reservation.cancelled.donor", **_fields(p))


def _fields(p: dict[str, Any]) -> dict[str, Any]:
    return {"food_title": p["food_title"], "portions": p["portions"], "beneficiary": p["beneficiary"]}


def subscribe(bus: EventBus) -> None:
    bus.subscribe(events.ACCOUNT_REVIEWED, _on_account_reviewed)
    bus.subscribe(events.ACCOUNT_SUSPENDED, _on_account_suspended)
    bus.subscribe(events.RESERVATION_CREATED, _on_reservation_created)
    bus.subscribe(events.RESERVATION_COLLECTED, _on_reservation_collected)
    bus.subscribe(events.RESERVATION_EXPIRED, _on_reservation_expired)
    bus.subscribe(events.RESERVATION_CANCELLED, _on_reservation_cancelled)

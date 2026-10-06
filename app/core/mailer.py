from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger("foodrescue.mail")


class Mailer(Protocol):
    def send(self, to: str, subject: str, body: str) -> None: ...


class LogMailer:
    """Local test backend: mail is written to the log instead of being delivered."""

    def send(self, to: str, subject: str, body: str) -> None:
        logger.info("MAIL to=%s subject=%s body=%s", to, subject, body)

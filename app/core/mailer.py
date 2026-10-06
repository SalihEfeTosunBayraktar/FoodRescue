from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger("foodrescue.mail")


# Protocol: 'şu metoda sahip her sınıf Mailer sayılır' (yapısal tipleme). Gerçek SMTP sınıfı
# yazıldığında bildirim kodu değişmez; bu Dependency Inversion ilkesidir: üst katman somut sınıfa
# değil arayüze bağlıdır.
class Mailer(Protocol):
    def send(self, to: str, subject: str, body: str) -> None: ...


# Yerel test için sahte posta gönderici: postayı göndermek yerine log'a yazar.
class LogMailer:
    """Local test backend: mail is written to the log instead of being delivered."""

    def send(self, to: str, subject: str, body: str) -> None:
        logger.info("MAIL to=%s subject=%s body=%s", to, subject, body)

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config.messages import ERRORS


# İş kuralı hatası. Durum kodunu ve mesaj ANAHTARINI taşır. Mesajın metni burada değil
# app/config/messages.py içindedir: metin ile kod ayrı tutulur.
class AppError(Exception):
    """Business error. `key` indexes app.config.messages.ERRORS."""

    def __init__(self, key: str, status: int = 400, **params) -> None:
        self.key = key
        self.status = status
        self.params = params
        super().__init__(key)

    @property
    # Şablondaki {yer_tutucular} `params` ile doldurulur.
    def message(self) -> str:
        template = ERRORS.get(self.key, self.key)
        return template.format(**self.params)


# FastAPI'ye 'AppError fırlatılırsa şu JSON'a çevir' kuralını öğretir. Böylece servis katmanı HTTP
# bilmeden hata fırlatabilir.
def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse({"detail": exc.message, "code": exc.key}, status_code=exc.status)

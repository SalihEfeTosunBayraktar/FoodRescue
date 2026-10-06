"""QR rendering. Kept separate so the library can be swapped without touching business rules."""
from __future__ import annotations

import io

import qrcode
import qrcode.image.svg
from qrcode.constants import ERROR_CORRECT_M

QR_PREFIX = "FR:"


def qr_payload(token: str) -> str:
    return f"{QR_PREFIX}{token}"


def parse_payload(code: str) -> str:
    return code[len(QR_PREFIX):] if code.startswith(QR_PREFIX) else code


def render_svg(payload: str) -> str:
    image = qrcode.make(
        payload,
        image_factory=qrcode.image.svg.SvgPathImage,
        error_correction=ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    buffer = io.BytesIO()
    image.save(buffer)
    return buffer.getvalue().decode("utf-8")

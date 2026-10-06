"""QR rendering. Kept separate so the library can be swapped without touching business rules."""
from __future__ import annotations

import io

import qrcode
import qrcode.image.svg
from qrcode.constants import ERROR_CORRECT_M

# QR içeriğinin başına 'FR:' ekleriz. Telefon kamerası başka bir QR'ı okursa uygulama bunu kendi
# kodundan ayırt edebilir.
QR_PREFIX = "FR:"


# Gizli değerden QR içeriğini üretir.
def qr_payload(token: str) -> str:
    return f"{QR_PREFIX}{token}"


# Okunan metni çözer: 'FR:' önekini atar. Önek yoksa metnin kendisi kodu (elle girilen PIN veya ham
# değer) sayılır.
def parse_payload(code: str) -> str:
    return code[len(QR_PREFIX):] if code.startswith(QR_PREFIX) else code


# QR görüntüsünü SVG metni olarak üretir. SVG vektördür: her ekran boyutunda keskin kalır ve Pillow
# gibi görüntü kütüphanesi gerekmez.
def render_svg(payload: str) -> str:
    # Hata düzeltme seviyesi M (~%15 bozulmaya dayanıklı): kod bir miktar kirlense veya ekran
    # parlasa bile okunur. Seviye arttıkça QR büyür.
    image = qrcode.make(
        payload,
        image_factory=qrcode.image.svg.SvgPathImage,
        error_correction=ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    # Bellekte geçici dosya: diske yazmadan çıktıyı alırız.
    buffer = io.BytesIO()
    image.save(buffer)
    return buffer.getvalue().decode("utf-8")

from __future__ import annotations

import math

# Dünya'yı küre varsayıp ortalama yarıçapını km cinsinden sabitleriz.
_EARTH_RADIUS_KM = 6371.0088


# Haversine formülü: küre üzerinde iki koordinat arasındaki en kısa (büyük daire) mesafe. Şehir içi
# mesafelerde hata yüzde 0.5'ten azdır.
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # Enlem/boylam derece olarak gelir ama trigonometri fonksiyonları RADYAN bekler; önce çeviririz.
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    # Formülün son adımı: açısal uzaklığı yarıçapla çarpıp km'ye çeviririz.
    return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))

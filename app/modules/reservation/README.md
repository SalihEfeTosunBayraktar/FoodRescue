# Modül 3: reservation (rezervasyon, QR/PIN, teslim)

**Sahip:** Kişi 3 | **Çalışma alanı:** `app/modules/reservation/` ve `web/modules/reservation/`
**İlgili dersler:** Python (durum yönetimi, kütüphane kullanımı), Veritabanına Giriş (çoklu JOIN, indeks, alt sorgu), JavaScript (zamanlayıcılar, kamera API'si)

## Öğrenme hedefleri
1. Bir nesnenin yaşam döngüsünü **durum makinesi** olarak modellemek.
2. `random` ile `secrets` arasındaki farkı ve neden önemli olduğunu açıklamak.
3. "Kim, neye erişebilir?" sorusunu sorguyu daraltarak çözmek (sahiplik kontrolü).
4. Kaba kuvvet saldırısını sınırlandırmak.

## Durum makinesi
```
              teslim doğrulandı
   PENDING  ------------------->  COLLECTED
      |  \
      |   \ kullanıcı iptal    ->  CANCELLED   (porsiyonlar stoğa döner)
      |    \ süre doldu        ->  EXPIRED     (porsiyonlar stoğa döner)
```
Yalnızca `PENDING` durumundan çıkılır; diğer üç durum son durumdur.

## Sorumluluk ve sınır
- **Yapar:** rezervasyon oluşturma/iptal, QR ve PIN üretimi, teslim doğrulama, süre dolumu.
- **Yapmaz:** stoğu doğrudan değiştirmez. `inventory.service.take_portions` / `return_portions` çağırır.
- **Dinlediği olay:** `food.cancelled` (ilan kaldırılınca bekleyen rezervasyonlar iptal olur).
- **Yayınladığı olaylar:** `reservation.created / collected / cancelled / expired` (bildirim ve denetim kaydı bunları dinler).

## Dosya turu
| Dosya | Görevi |
| --- | --- |
| `models.py` | `Reservation`, üç bileşik indeks |
| `schemas.py` | `MyReservationOut` (PIN ve QR içerir), `DonorReservationOut` (sır içermez) |
| `qr.py` | QR üretimi (SVG). Kütüphane değişirse yalnızca bu dosya değişir |
| `service.py` | `create_reservation`, `verify_pickup`, `cancel_reservation`, `expire_due` |
| `router.py` | `/api/v1/reservations` |
| `web/modules/reservation/` | `wallet.js` (QR/PIN cüzdanı), `desk.js` (teslim masası), `scanner.js` (kamera) |

## Güvenlik tasarımı (`verify_pickup`)
| Tehdit | Önlem |
| --- | --- |
| Başka işletme benim rezervasyonumu onaylar | Sorgu `donor_id = giriş yapan işletme` ile daraltılır |
| PIN'i denemeyle bulma (1.000.000 ihtimal) | İşletme başına 5 hatalı denemede 5 dakika kilit (`core/ratelimit.py`) |
| Tahmin edilebilir kod | `secrets` modülü; `random` kullanılmaz |
| Aynı kodla ikinci teslim | Yalnızca `PENDING` aranır; ilk kullanımdan sonra bulunamaz |
| Yararlanıcının kimliği | İşletme yalnızca "Ali Y." gibi etiket görür |

## Veritabanı
Tablo: `reservations`. İndeksler: `(donor_id, status)` teslim masası için, `(beneficiary_id, status)` cüzdan için, `(status, expires_at)` süre dolumu işi için. Her indeksin hangi sorgu için olduğunu `sql/queries.sql` içindeki `EXPLAIN QUERY PLAN` ile doğrulayın.

## Alıştırmalar
1. **Kolay:** `settings.reservation_ttl_minutes` değerini 45 yapıp `expires_at` farkını bir testle doğrulayın. Ayarın neden kodda sabit olmadığını açıklayın.
2. **Kolay (SQL):** `queries.sql` içine "en çok porsiyon alan 3 yararlanıcıyı" bulan sorgu ekleyin (`GROUP BY` + `ORDER BY ... LIMIT 3`).
3. **Orta:** Teslim alınmadan süresi dolan rezervasyonları sayan bir "gelmeyen" sayacı ekleyin ve 3'ten fazla gelmeyen kullanıcıya uyarı bildirimi gönderin (olay yayınlayın, bildirim modülü dinlesin).
4. **Orta (ön yüz):** Cüzdandaki geri sayım 5 dakikanın altına inince kartı kırmızı yapın.
5. **Zor:** `_unique_pin` şu an uygulama düzeyinde benzersizlik sağlıyor. Aynısını veritabanı düzeyinde (kısmi benzersiz indeks: `CREATE UNIQUE INDEX ... WHERE status = 'PENDING'`) kurun. Uygulama kodunda hangi hata yakalanmalı?

## Testler
`python -m pytest tests/test_reservation.py -q`

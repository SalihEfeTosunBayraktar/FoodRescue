# Modül 5: impact (etki, şikâyet, denetim, yönetim)

**Sahip:** Kişi 5 | **Çalışma alanı:** `app/modules/impact/` ve `web/modules/impact/`
**İlgili dersler:** Veritabanına Giriş (toplama fonksiyonları, GROUP BY, HAVING, pencere fonksiyonu), Python (veri işleme), JavaScript (tablo ve grafik çizimi)

## Öğrenme hedefleri
1. İstatistik sorgularını yazmak: `COUNT`, `SUM`, `COALESCE`, `GROUP BY`, `HAVING`, koşullu toplama (`CASE`).
2. **Denetim kaydının** (audit log) neden yalnızca eklemeli (append-only) olduğunu açıklamak.
3. Eşiğe bağlı otomatik kural (3 farklı kişiden şikâyet -> askıya alma) tasarlamak.
4. Başka modüllerin verisini **salt okunur** kullanmanın sınırını çizmek.

## Sorumluluk ve sınır
- **Yapar:** herkese açık sayaçlar, işletme panosu, şikâyet akışı, denetim kaydı, yönetici genel bakışı.
- **Okur (salt):** `reservations`, `food_items`, `users` tabloları. Bunlara **yazmaz**.
- **Yazar:** `audit_log`, `complaints`.
- **Başka modülü çağırdığı tek yer:** eşik aşılınca `identity.service.suspend_account`. Sonrasını olay zinciri halleder: `account.suspended` -> inventory ilanları kaldırır -> reservation bekleyenleri iptal eder -> notification işletmeyi bilgilendirir.
- **Her olayı dinler:** `subscribers.py` tüm olayları `audit_log` tablosuna yazar.

## Dosya turu
| Dosya | Görevi |
| --- | --- |
| `models.py` | `AuditLog`, `Complaint` (`reservation_id` UNIQUE) |
| `service.py` | `summary`, `donor_impact`, `overview`, `file_complaint`, `record_audit` |
| `router.py` | `/api/v1/impact`, `/api/v1/complaints`, `/api/v1/admin/*` |
| `subscribers.py` | Tüm olayları denetim kaydına yazar |
| `web/modules/impact/` | Ana sayfa, yönetim paneli (4 sekme), şikâyet penceresi |

## Şikâyet eşiği nasıl çalışır?
```
Yararlanıcı şikâyet eder  ->  complaints satırı eklenir (reservation_id UNIQUE: aynı rezervasyon için tek şikâyet)
Aynı işletme için AÇIK şikâyetlerde COUNT(DISTINCT reporter_id) >= 3 ise  ->  işletme askıya alınır
```
`DISTINCT` kritiktir: tek kişi birden fazla rezervasyondan şikâyet edip işletmeyi tek başına askıya aldıramaz.

## Kavram kutuları
- **COALESCE:** hiç satır yoksa `SUM` değeri `NULL` döner, arayüzde "null" görünür. `COALESCE(SUM(x), 0)` bunu 0 yapar.
- **Koşullu toplama:** `SUM(CASE WHEN status='COLLECTED' THEN portions END)` ile tek sorguda birden çok toplam.
- **Append-only:** denetim kaydına silme veya güncelleme uç noktası bilerek yoktur. "Kim ne zaman ne yaptı" sorusunun cevabı değiştirilememelidir.
- **Okuma modeli:** raporlama sorguları yazma yolunu yavaşlatmamalı. Büyüdüğünde ayrı bir özet tablo veya önbellek düşünülür.

## Alıştırmalar
1. **Kolay (SQL):** `queries.sql` içine "teslim edilen toplam porsiyonun işletme bazında yüzdesini" ekleyin (`SUM(...) * 100.0 / (SELECT SUM(...) ...)`).
2. **Kolay:** `summary` yanıtına "farklı yararlanıcı sayısı" ekleyin (`COUNT(DISTINCT beneficiary_id)`), şemayı ve testi güncelleyin.
3. **Orta:** `GET /api/v1/impact/daily?days=14`: son 14 günün günlük teslim edilen porsiyonları (`GROUP BY date(collected_at)`). Boş günler 0 görünmeli; bunu SQL'de mi Python'da mı yapmak daha doğru, gerekçeyle seçin.
4. **Orta (ön yüz):** Bu uç nokta için bağımlılıksız (kütüphanesiz) bir SVG çubuk grafik çizin.
5. **Zor:** Yönetici denetim kaydını CSV olarak indirsin. Büyük tabloda belleği şişirmeden, akış (streaming) halinde gönderin.

## Testler
`python -m pytest tests/test_notification_impact.py -q`

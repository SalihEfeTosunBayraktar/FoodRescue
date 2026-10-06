# Modül 2: inventory (gıda ilanları ve stok)

**Sahip:** Kişi 2 | **Çalışma alanı:** `app/modules/inventory/` ve `web/modules/inventory/`
**İlgili dersler:** Veritabanına Giriş (CHECK, indeks, UPDATE, işlem), Python (dosya işleme, fonksiyonlar), JavaScript (async/await, DOM)

## Öğrenme hedefleri
1. Bir "sayaç" kolonunu (kalan porsiyon) eşzamanlı isteklere karşı doğru tutmak.
2. Veritabanı kısıtlarının (`CHECK`) uygulama kodunun son savunma hattı olduğunu görmek.
3. İki koordinat arası mesafeyi (haversine) hesaplamak ve sıralamak.
4. Kullanıcıdan gelen dosyaya neden güvenilmediğini anlamak.

## Sorumluluk ve sınır
- **Yapar:** ilan oluşturma/düzenleme/kaldırma, listeleme ve filtreleme, yakınlık sıralaması, fotoğraf yükleme, süresi dolan ilanları kapatma, stoktan porsiyon düşme/iade.
- **Yapmaz:** rezervasyon, QR/PIN. Rezervasyon modülü stok için yalnızca `service.take_portions` ve `service.return_portions` fonksiyonlarını çağırır.
- **Dinlediği olay:** `account.suspended` (askıdaki işletmenin ilanları kaldırılır, `subscribers.py`).

## Dosya turu
| Dosya | Görevi |
| --- | --- |
| `models.py` | `FoodItem`, `CHECK` kısıtları ve indeksler |
| `schemas.py` | `FoodCreate` (hijyen beyanı zorunlu), `FoodOut` |
| `service.py` | `create_food`, `list_foods`, `take_portions` (atomik), `save_photo`, `expire_due` |
| `router.py` | `/api/v1/foods` uç noktaları. Listeleme herkese açık |
| `subscribers.py` | Başka modüllerin olaylarına tepkiler |
| `sql/queries.sql` | SQL çalışma defteri |
| `web/modules/inventory/` | Akış + harita, ilan detayı, bağışçı paneli, ilan formu |

## Bir isteğin yolculuğu: ilan listesi
```
GET /api/v1/foods?category=HUMAN&lat=39.75&lon=37.01&radius_km=5
  list_foods(): SQL ile durum/stok/zaman süzülür (veritabanı işi)
                -> Python'da haversine ile mesafe hesaplanır ve sıralanır (hesap işi)
Ön yüz: feed.js sonuçları kart + işaretçi olarak çizer; 30 sn'de bir yeniler.
```

## Veritabanı
Tablo: `food_items` (FK: `donor_id -> users.id`). İndeks: `(status, pickup_until)`.
Kısıt: `CHECK (portions_left >= 0 AND portions_left <= portions_total)`.

## Kavram kutuları
- **Atomik güncelleme:** iki kişi son porsiyona aynı anda basarsa? `take_portions` koşulu `UPDATE ... WHERE portions_left >= n` içine koyar. Veritabanı kontrolü ve düşümü tek adımda yapar; `rowcount == 0` ise başarısızdır. `tests/test_inventory.py::test_take_portions_is_atomic_under_concurrency` 12 thread ile bunu sınar.
- **Denormalizasyon:** `portions_left` türetilebilir bir değerdir ama sayaç olarak tutulur. Okuması hızlıdır, bedeli doğruluğu korumaktır.
- **Dosya yükleme güvenliği:** `Content-Type` ve dosya adı istemciden gelir, sahte olabilir. Servis dosyanın ilk baytlarına (magic bytes) bakar ve adı rastgele üretir.
- **Veritabanı mı Python mu?** Süzme ve sıralama veritabanında, formül Python'da. Bu ayrım ölçek büyüdükçe önemlidir.

## Alıştırmalar
1. **Kolay:** `FoodCreate` içinde başlığın yalnızca rakamlardan oluşmasını yasaklayın. Önce test.
2. **Kolay (SQL):** `queries.sql` içine "bugün açılmış ilanların kategori bazında sayısı" sorgusunu ekleyin (`date(created_at) = date('now')`).
3. **Orta:** İlana "en erken alım saati" (`pickup_from`) alanı ekleyin. Model, şema, form ve test. Mevcut veritabanı dosyasına ne olur? (`create_all` mevcut tabloyu değiştirmez; bunu not edin ve nedenini araştırın. Çözüm: migration.)
4. **Orta (ön yüz):** Akışa "en yakın önce / en geç biten önce" sıralama seçeneği ekleyin.
5. **Zor:** Haversine'i her ilan için hesaplamak yerine önce SQL'de basit bir "kare kutu" (bounding box) süzgeci uygulayın. Süreyi 5000 ilanlık sentetik veriyle ölçüp önce/sonra karşılaştırın.

## Testler
`python -m pytest tests/test_inventory.py -q`

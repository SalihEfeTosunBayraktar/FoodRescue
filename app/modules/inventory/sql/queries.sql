-- INVENTORY modülü: SQL çalışma defteri
-- Çalıştırma:  python tools/sqlshell.py app/modules/inventory/sql/queries.sql --write
--   (--write gerekir: BEGIN/ROLLBACK bloğu yazılabilir bağlantı ister; bloğun sonunda ROLLBACK ile veri korunur)

-- 1) CHECK kısıtı tanımı: porsiyon sayısı 0 ile toplam arasında kalmak zorunda.
SELECT sql FROM sqlite_master WHERE name = 'food_items';

-- 2) Şu an gerçekten müsait ilanlar (service.list_foods ile aynı koşul).
--    Üç koşulun hepsi birlikte sağlanmalı: durum, kalan porsiyon, zaman.
SELECT id, title, portions_left, pickup_until
FROM food_items
WHERE status = 'AVAILABLE'
  AND portions_left > 0
  AND pickup_until > datetime('now')
ORDER BY pickup_until;

-- 3) Hesaplanan kolon: ilanın yüzde kaçı rezerve edildi?
SELECT title,
       portions_total,
       portions_left,
       ROUND((portions_total - portions_left) * 100.0 / portions_total, 1) AS doluluk_yuzdesi
FROM food_items
ORDER BY doluluk_yuzdesi DESC;

-- 4) JOIN: ilan + bağışçı adı. ORM'de lazy="joined" ilişkisi bu JOIN'i bizim yerimize yapar.
SELECT f.title, u.organization_name AS isletme, f.category
FROM food_items AS f
JOIN users AS u ON u.id = f.donor_id
ORDER BY u.organization_name, f.title;

-- 5) Kategori bazında toplam ve kalan porsiyon (SUM + GROUP BY).
SELECT category, SUM(portions_total) AS toplam, SUM(portions_left) AS kalan
FROM food_items
GROUP BY category;

-- 6) ATOMİK STOK DÜŞÜMÜ: service.take_portions işleminin ham SQL karşılığı.
--    Koşul WHERE içinde olduğu için "kontrol + düşüm" tek adımdır; iki kişi aynı anda
--    son porsiyonu alamaz. changes() etkilenen satır sayısını verir (0 = başarısız).
--    Deneme bir işlem (transaction) içinde yapılıp ROLLBACK ile geri alınır, veri değişmez.
BEGIN;
UPDATE food_items
SET portions_left = portions_left - 2
WHERE id = 1 AND status = 'AVAILABLE' AND portions_left >= 2;
SELECT changes() AS etkilenen_satir;
SELECT id, portions_left FROM food_items WHERE id = 1;
ROLLBACK;

-- 7) Karşılaştırma: "önce oku sonra yaz" yaklaşımı (YANLIŞ yol). İki oturum arada
--    SELECT sonucunu aynı anda okursa ikisi de UPDATE yapar ve stok eksiye düşebilirdi.
--    CHECK kısıtı son savunma hattıdır: UPDATE food_items SET portions_left = -1 WHERE id = 1;
--    -> CHECK constraint failed: ck_food_portions_range

-- 8) İndeks kullanımı: (status, pickup_until) bileşik indeksi.
EXPLAIN QUERY PLAN
SELECT id FROM food_items WHERE status = 'AVAILABLE' AND pickup_until > datetime('now');

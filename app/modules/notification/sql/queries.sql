-- NOTIFICATION modülü: SQL çalışma defteri
-- Çalıştırma:  python tools/sqlshell.py app/modules/notification/sql/queries.sql --write
--   (--write gerekir: BEGIN/ROLLBACK bloğu yazılabilir bağlantı ister; bloğun sonunda ROLLBACK ile veri korunur)

-- 1) Kullanıcı başına okunmamış bildirim sayısı. read_at NULL ise okunmamıştır.
--    Önemli: NULL için "= NULL" yazılmaz, IS NULL yazılır (NULL hiçbir değere eşit değildir).
SELECT user_id, COUNT(*) AS okunmamis
FROM notifications
WHERE read_at IS NULL
GROUP BY user_id;

-- 2) Bir kullanıcının son 10 bildirimi (kutu sayfası sorgusu).
SELECT id, kind, title, created_at
FROM notifications
WHERE user_id = 2
ORDER BY id DESC
LIMIT 10;

-- 3) Bildirim türlerine göre dağılım. Hangi olay en çok bildirim üretiyor?
SELECT kind, COUNT(*) AS adet FROM notifications GROUP BY kind ORDER BY adet DESC;

-- 4) İndeks planı: (user_id, read_at) bileşik indeksi hem filtreyi hem sayımı hızlandırır.
EXPLAIN QUERY PLAN
SELECT COUNT(*) FROM notifications WHERE user_id = 2 AND read_at IS NULL;

-- 5) Hiç bildirimi olmayan kullanıcılar: NOT EXISTS ile.
SELECT u.id, u.email
FROM users AS u
WHERE NOT EXISTS (SELECT 1 FROM notifications AS n WHERE n.user_id = u.id);

-- 6) Toplu "okundu" işaretleme (mark_all_read karşılığı), bir işlem içinde denenir ve geri alınır.
BEGIN;
UPDATE notifications SET read_at = datetime('now') WHERE user_id = 2 AND read_at IS NULL;
SELECT changes() AS guncellenen;
ROLLBACK;

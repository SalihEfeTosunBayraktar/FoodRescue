-- RESERVATION modülü: SQL çalışma defteri
-- Çalıştırma:  python tools/sqlshell.py app/modules/reservation/sql/queries.sql

-- 1) Durum dağılımı. Rezervasyon bir durum makinesidir: PENDING -> COLLECTED | CANCELLED | EXPIRED.
SELECT status, COUNT(*) AS adet, SUM(portions) AS porsiyon FROM reservations GROUP BY status;

-- 2) Üç tablo JOIN: kim, hangi yemeği, hangi işletmeden rezerve etti?
SELECT r.id,
       b.full_name   AS yararlanici,
       f.title       AS yemek,
       d.organization_name AS isletme,
       r.portions,
       r.status
FROM reservations AS r
JOIN users      AS b ON b.id = r.beneficiary_id
JOIN users      AS d ON d.id = r.donor_id
JOIN food_items AS f ON f.id = r.food_id
ORDER BY r.created_at DESC;
-- Dikkat: users tablosuna iki kez, farklı takma adlarla (b, d) bağlandık.

-- 3) Teslim masası sorgusu: bir işletmenin bekleyen rezervasyonları.
--    Güvenlik kuralı #1: sorgu donor_id ile daraltılır; başka işletmenin kodu bulunamaz.
SELECT id, pin, expires_at
FROM reservations
WHERE donor_id = (SELECT id FROM users WHERE email = 'restoran@foodrescue.local')
  AND status = 'PENDING'
  AND expires_at > datetime('now');

-- 4) Bu sorgu için ix_reservation_donor_status indeksi kullanılır. Planı okuyun.
EXPLAIN QUERY PLAN
SELECT id FROM reservations WHERE donor_id = 2 AND status = 'PENDING';

-- 5) Süresi dolacak rezervasyonlar (service.expire_due'nun SELECT kısmı).
SELECT id, expires_at FROM reservations WHERE status = 'PENDING' AND expires_at <= datetime('now', '+1 day');

-- 6) Alt sorgu: en az bir kez teslim almış yararlanıcılar.
SELECT id, full_name
FROM users
WHERE id IN (SELECT beneficiary_id FROM reservations WHERE status = 'COLLECTED');

-- 7) İşletme başına teslim edilen porsiyon (HAVING ile eşik).
SELECT d.organization_name, SUM(r.portions) AS teslim_edilen
FROM reservations AS r
JOIN users AS d ON d.id = r.donor_id
WHERE r.status = 'COLLECTED'
GROUP BY d.id, d.organization_name
HAVING SUM(r.portions) >= 1;

-- 8) PIN neden işletmeye göre benzersiz? Aynı işletmede iki bekleyen rezervasyon aynı PIN'i
--    taşırsa arama belirsiz olur. Bu kontrol service._unique_pin içinde yapılır:
SELECT donor_id, pin, COUNT(*) AS adet
FROM reservations
WHERE status = 'PENDING'
GROUP BY donor_id, pin
HAVING COUNT(*) > 1;   -- sonuç boş olmalı

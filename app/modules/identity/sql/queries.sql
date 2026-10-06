-- IDENTITY modülü: SQL çalışma defteri
-- Çalıştırma:  python tools/sqlshell.py app/modules/identity/sql/queries.sql
-- Her sorguyu önce okuyun, sonucu tahmin edin, sonra çalıştırın.

-- 1) Tablo yapısı. SQLite bu tablonun CREATE ifadesini sqlite_master içinde saklar.
--    UNIQUE, NOT NULL ve CHECK kısıtlarını burada görebilirsiniz.
SELECT sql FROM sqlite_master WHERE name = 'users';

-- 2) Seçme + sıralama. ORM karşılığı: select(User).order_by(User.created_at.desc())
SELECT id, email, role, status FROM users ORDER BY created_at DESC;

-- 3) GROUP BY: roller bazında kullanıcı sayısı. ORM karşılığı: service.overview() içindeki users_by_role
SELECT role, COUNT(*) AS adet FROM users GROUP BY role ORDER BY adet DESC;

-- 4) WHERE ile filtre: yönetici onayı bekleyen kurumlar. ORM: service.list_accounts(status=PENDING_REVIEW)
SELECT id, organization_name, license_number, address
FROM users
WHERE status = 'PENDING_REVIEW'
ORDER BY created_at;

-- 5) LEFT JOIN: her bağışçının kaç ilanı var? İlanı olmayan bağışçı da 0 ile listelenir.
--    (INNER JOIN kullansaydık ilanı olmayanlar sonuçtan kaybolurdu. Farkı deneyin.)
SELECT u.id, u.organization_name, COUNT(f.id) AS ilan_sayisi
FROM users AS u
LEFT JOIN food_items AS f ON f.donor_id = u.id
WHERE u.role = 'DONOR'
GROUP BY u.id, u.organization_name
ORDER BY ilan_sayisi DESC;

-- 6) Bileşik indeks: (role, status) indeksi sayesinde bu sorgu tabloyu baştan sona taramaz.
--    Çıktıda "USING INDEX ix_users_role_status" ifadesini arayın.
EXPLAIN QUERY PLAN
SELECT COUNT(*) FROM users WHERE role = 'DONOR' AND status = 'ACTIVE';

-- 7) E-posta üzerindeki UNIQUE indeks: girişte (login) kullanılan arama hızlıdır.
EXPLAIN QUERY PLAN
SELECT id FROM users WHERE email = 'admin@foodrescue.local';

-- 8) Kısıt denemesi (bilerek yorumda, çalıştırırsanız hata alırsınız):
--    INSERT INTO users (email, password_hash, full_name, role, status, created_at)
--    VALUES ('admin@foodrescue.local', 'x', 'Kopya', 'ADMIN', 'ACTIVE', datetime('now'));
--    -> UNIQUE constraint failed: users.email

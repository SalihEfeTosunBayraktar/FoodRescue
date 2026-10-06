-- IMPACT modülü: SQL çalışma defteri
-- Çalıştırma:  python tools/sqlshell.py app/modules/impact/sql/queries.sql

-- 1) Ana sayfadaki "kurtarılan porsiyon" sayacı (service.summary).
--    COALESCE: hiç satır yoksa SUM NULL döner; COALESCE bunu 0'a çevirir.
SELECT COALESCE(SUM(portions), 0) AS kurtarilan_porsiyon, COUNT(*) AS teslim_sayisi
FROM reservations
WHERE status = 'COLLECTED';

-- 2) İşletme panosu (service.donor_impact): her işletmenin teslim ettiği ve bekleyen porsiyon.
--    Koşullu toplama: CASE WHEN ile tek sorguda iki ayrı toplam.
SELECT d.organization_name,
       COALESCE(SUM(CASE WHEN r.status = 'COLLECTED' THEN r.portions END), 0) AS teslim,
       COALESCE(SUM(CASE WHEN r.status = 'PENDING'   THEN r.portions END), 0) AS bekleyen
FROM users AS d
LEFT JOIN reservations AS r ON r.donor_id = d.id
WHERE d.role = 'DONOR'
GROUP BY d.id, d.organization_name;

-- 3) Şikâyet eşiği (service.file_complaint): bir işletmeye FARKLI kişilerden kaç açık şikâyet var?
--    DISTINCT önemlidir: aynı kişi üç kez şikâyet etse bile eşik tek kişi sayılır.
--    Eşik 3 ise bu sorgunun HAVING satırındaki sayı 3 olur ve işletme askıya alınır.
SELECT donor_id, COUNT(DISTINCT reporter_id) AS farkli_kisi
FROM complaints
WHERE status = 'OPEN'
GROUP BY donor_id
HAVING COUNT(DISTINCT reporter_id) >= 1;

-- 4) UNIQUE(reservation_id) kısıtı: bir rezervasyon için tek şikâyet. Tanıma bakın:
SELECT sql FROM sqlite_master WHERE name = 'complaints';

-- 5) Denetim kaydı (audit_log): en son 20 olay. Bu tabloya yalnızca INSERT yapılır.
SELECT id, actor_id, action, entity_type, entity_id, created_at
FROM audit_log
ORDER BY id DESC
LIMIT 20;

-- 6) Hangi olaydan kaç kayıt var?
SELECT action, COUNT(*) AS adet FROM audit_log GROUP BY action ORDER BY adet DESC;

-- 7) Bir kaydın tüm geçmişi: örneğin 1 numaralı rezervasyonda neler olmuş? (ix_audit_entity indeksi)
SELECT created_at, action, actor_id, detail
FROM audit_log
WHERE entity_type = 'reservation' AND entity_id = 1
ORDER BY id;

-- 8) Pencere fonksiyonu (ileri düzey): teslimlerin birikimli toplamı.
SELECT id,
       portions,
       SUM(portions) OVER (ORDER BY collected_at) AS birikimli_porsiyon
FROM reservations
WHERE status = 'COLLECTED'
ORDER BY collected_at;

# Öğrenme yolu

Bu proje, programlama dilleri ve veritabanına giriş derslerinde gördüklerinizin **tek bir gerçek uygulamada** nasıl bir araya geldiğini göstermek için yazıldı. Önce çalıştırın, sonra okuyun, sonra bozup düzeltin.

## 1) Derslerden dosyalara harita

| Dersteki konu | Projede nerede görürsünüz |
| --- | --- |
| Sınıflar, kalıtım (Python) | `app/modules/*/models.py` (SQLAlchemy sınıfları), `schemas.py` (Pydantic) |
| Fonksiyonlar, tip ipuçları | `service.py` dosyaları |
| İstisnalar (exception) | `app/core/errors.py` (`AppError`), servislerdeki `raise` kullanımları |
| Modüller, paketler | `app/modules/` düzeni, `module.py` ile kayıt |
| Enum, durum modeli | `UserRole`, `ReservationStatus` |
| Dosya işleme | `inventory/service.py::save_photo` |
| Eşzamanlılık (thread) | `tests/test_inventory.py` içindeki yarış testi |
| JavaScript: DOM, olaylar | `web/core/dom.js`, `web/modules/*/` sayfaları |
| JavaScript: async/await, fetch | `web/core/api.js` |
| JavaScript: ES modülleri | her `import`/`export`; `web/main.js` |
| HTTP ve REST | `router.py` dosyaları, `/docs` sayfası |
| SQL: SELECT, WHERE, ORDER BY | her modülün `sql/queries.sql` dosyası, ilk sorgular |
| SQL: JOIN, GROUP BY, HAVING | `reservation/sql`, `impact/sql` |
| SQL: kısıtlar (PRIMARY, FOREIGN, UNIQUE, CHECK) | `models.py` + `sqlite_master` sorguları |
| SQL: indeks ve sorgu planı | `EXPLAIN QUERY PLAN` sorguları |
| SQL: işlem (transaction), atomiklik | `inventory/sql/queries.sql` 6. sorgu, `take_portions` |
| Normalizasyon ve bilinçli denormalizasyon | `portions_left` sayacı, `reservations.donor_id` |
| Test yazma | `tests/` klasörü |

## 2) Dört haftalık okuma planı

**Hafta 1: Çalıştır ve gez.** `python run.py` ile açın. Her demo hesapla giriş yapıp akışı elle deneyin. `/docs` sayfasında uç noktaları deneyin. Sonra `sqlshell.py` ile her tabloya bakın: `SELECT * FROM users`.
**Hafta 2: Bir isteğin yolu.** Girişten (`identity`) başlayın: tarayıcıdaki `auth_pages.js` -> `api.js` -> `router.py` -> `service.py` -> `models.py` -> SQL. Modül README'sindeki "Bir isteğin yolculuğu" bölümünü yanınızda tutun.
**Hafta 3: Kendi modülünüz.** README'deki kavram kutularını okuyup bir kolay ve bir orta alıştırma yapın. Önce test yazın.
**Hafta 4: Modüller arası.** `docs/ARCHITECTURE.md` içindeki olay akışını `app/core/events.py` ve `audit_log` tablosu üzerinden izleyin: bir şikâyet gönderin, `SELECT * FROM audit_log ORDER BY id DESC` ile zinciri okuyun.

## 3) Hata ayıklama alışkanlıkları
- Hata mesajını **okuyun**; ilk satır neyin, son satır nerede olduğunu söyler.
- Tarayıcıda F12 > Network: isteğin durum kodu ve yanıt gövdesi. `4xx` genelde istemci/iş kuralı, `5xx` sunucu hatasıdır.
- Şüphelenince veriye bakın: `python tools/sqlshell.py "SELECT * FROM reservations"`.
- Bir şeyin **neden** çalıştığını açıklayamıyorsanız, testini bozup hangi testin kırıldığına bakın.

## 4) Sözlük
- **API / endpoint:** programın dışarıya açtığı, URL ile çağrılan işlev.
- **ORM:** tabloları sınıf, satırları nesne gibi kullanmanızı sağlayan katman.
- **Transaction (işlem):** ya hep ya hiç prensibiyle çalışan işlem grubu.
- **Atomik:** bölünemez; yarım kalmaz.
- **İndeks:** aramayı hızlandıran, ek yer kaplayan veri yapısı.
- **JWT:** imzalı, süresi olan kimlik bileti.
- **RBAC:** rol tabanlı erişim denetimi.
- **Hash:** geri çevrilemeyen özet. Parolalar bununla saklanır.
- **Olay (event):** "şu oldu" duyurusu; kimin dinleyeceğini yayıncı bilmez.
- **Denormalizasyon:** hızlı okuma için veriyi bilinçli olarak tekrar saklamak.
- **XSS:** kullanıcı girdisinin sayfada kod olarak çalışması.

# Ekip çalışma düzeni

## Neden "dikey dilim"?
Her kişi **bir modülün hem sunucu hem arayüz tarafının** sahibidir (ör. Kişi 3: `app/modules/reservation/` + `web/modules/reservation/`). "Backend ekibi" ve "frontend ekibi" ayrımı yerine bu seçildi, çünkü:
- Her üye SQL, Python ve JavaScript derslerinin üçünü de **aynı özellikte** uygular.
- Bir özellik bitince uçtan uca çalışır; "API hazır ama ekran yok" beklemesi olmaz.
- Dosya sahipliği net olduğundan Git çakışması azalır.

| Kişi | Modül | Ana öğrenme alanı |
| --- | --- | --- |
| 1 | identity | Güvenlik, kimlik doğrulama, yetkilendirme |
| 2 | inventory | Veritabanı kısıtları, atomik güncelleme, dosya işleme |
| 3 | reservation | Durum makinesi, güvenli kod üretimi, kamera/QR |
| 4 | notification | Olay tabanlı tasarım, soyutlama, zamanlayıcılar |
| 5 | impact | SQL raporlama, denetim kaydı, yönetim ekranları |

## Git akışı
1. Her iş için dal: `feat/<modül>-<kısa-ad>` (ör. `feat/reservation-noshow-counter`).
2. Yalnızca **kendi modül klasörünüze** yazın. Ortak dosyalar (`app/core/*`, `app/config/*`, `web/core/*`) için küçük ve ayrı bir PR açın, en az bir kişi onaylasın.
3. PR açmadan önce: `python -m pytest tests -q --ignore=tests/e2e` yeşil olmalı.
4. Commit mesajı İngilizce, tek konu: `feat(inventory): add pickup_from field`.
5. Başkasının modülünde hata görürseniz düzeltmeyin: issue açın veya sahibine söyleyin.

## Bir özellik nasıl eklenir (kontrol listesi)
1. Ne yapılacağını bir cümleyle yazın; kabul ölçütlerini listeleyin.
2. **Önce test:** başarısız bir test yazın (`tests/test_<modül>.py`).
3. Model ve şema -> service -> router sırasıyla ilerleyin.
4. Başka modülü ilgilendiriyorsa **olay** ekleyin (`app/config/events.py`), doğrudan çağırmayın.
5. Kullanıcıya görünen her metin `messages.py` veya `strings.js` içine girer.
6. Ön yüzü ekleyin; `web/modules/<modül>/index.js` yolları ve menüyü bildirir.
7. Veritabanı değiştiyse `sql/queries.sql` çalışma defterini güncelleyin (test bunu doğrular).
8. Modül README'sine kavram veya alıştırma ekleyin.

## Kodlama kuralları (kısa)
- Fonksiyon tek iş yapar; 30 satırı aşıyorsa bölün.
- Router'da iş kuralı yok, service'te HTTP yok.
- İsimler iş dilinden gelir (`take_portions`, `verify_pickup`), `process_data` gibi genel isimlerden kaçının.
- `try/except` ile sessizce hata yutmayın; beklenen iş hataları `AppError` ile, anahtarla (`messages.py`) fırlatılır.
- Sihirli sayı yok: eşikler `settings.py` içindedir.
- Yorumlar Türkçe ve öğreticidir: 'ne yapıyor' değil 'NEDEN böyle' yazın (örn. bir kontrolün hangi saldırıyı veya hatayı önlediği). Kodu tekrar eden yorum yazmayın.

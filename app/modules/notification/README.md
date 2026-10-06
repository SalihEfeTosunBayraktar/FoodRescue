# Modül 4: notification (bildirimler)

**Sahip:** Kişi 4 | **Çalışma alanı:** `app/modules/notification/` ve `web/modules/notification/`
**İlgili dersler:** Python (arayüz/Protocol, fonksiyonları değer olarak kullanma), Veritabanına Giriş (NULL, bileşik indeks), JavaScript (zamanlayıcı, olay dinleme)

## Öğrenme hedefleri
1. **Olay tabanlı (publish/subscribe)** tasarım: göndereni alıcıdan ayırmak.
2. "Genişlemeye açık, değişikliğe kapalı" ilkesini (Open/Closed) uygulamak.
3. Dış bağımlılığı (e-posta) soyut bir arayüzün arkasına koymak.
4. SQL'de `NULL` ile doğru çalışmak.

## Fikir
Rezervasyon modülü bildirim modülünü **tanımaz**. "Rezervasyon oluşturuldu" olayını yayınlar. Bildirim modülü bu olayı dinler ve kime ne yazılacağına kendisi karar verir.
```
reservation.service  --publish("reservation.created")-->  EventBus
                                                             |-> notification.subscribers  -> notify() -> notifications tablosu + mailer
                                                             |-> impact.subscribers        -> audit_log
```
Bu sayede yeni bir bildirim eklemek için rezervasyon koduna dokunmak gerekmez.

## Dosya turu
| Dosya | Görevi |
| --- | --- |
| `models.py` | `Notification`, `(user_id, read_at)` bileşik indeksi |
| `subscribers.py` | **Olay -> alıcı + şablon** eşlemesi. Kime ne söyleneceği tek yerde |
| `service.py` | `notify()`, listeleme, okundu işaretleme |
| `router.py` | `/api/v1/notifications` (her kullanıcı yalnızca kendi bildirimlerini görür) |
| `app/config/messages.py` | Bildirim metin şablonları (kodda gömülü metin yok) |
| `app/core/mailer.py` | `Mailer` arayüzü ve yerel `LogMailer` (postayı log'a yazar) |
| `web/modules/notification/` | Zil simgesi (okunmamış sayacı) ve gelen kutusu |

## Kavram kutuları
- **Olay yayınlama:** `core/events.py` ~25 satırdır; okuyup bir olay yayınlamak ve dinlemek için gerekenleri çıkarın.
- **Arayüz ile soyutlama:** `Mailer` bir `Protocol`'dür. Gerçek SMTP sınıfı yazıldığında `notify()` değişmez; yalnızca `build_context` içinde hangi sınıfın kullanılacağı değişir.
- **NULL mantığı:** `read_at IS NULL` okunmamış demektir. `read_at = NULL` hiçbir satırı eşleştirmez, çünkü NULL hiçbir değere (kendisine bile) eşit değildir.
- **Aynı işlem (transaction):** olay işleyicileri yayıncının işlemi içinde çalışır. Rezervasyon geri alınırsa bildirim de geri alınır; "var olmayan şey hakkında bildirim" oluşmaz.

## Alıştırmalar
1. **Kolay:** Hesap yeniden aktifleştirilince (`account.reinstated`) kullanıcıya bildirim gönderin: şablonu `messages.py`, eşlemeyi `subscribers.py` içine ekleyin.
2. **Kolay (SQL):** "Hiç okunmamış bildirimi 7 günden eski olan kullanıcıları" listeleyen sorguyu yazın.
3. **Orta:** Her bildirim türü için kullanıcının kapatabileceği bir tercih tablosu tasarlayın (şema çizimi + model).
4. **Orta (ön yüz):** Zil rozetinde okunmamış sayısı değişince küçük bir animasyon. `prefers-reduced-motion` ayarına saygı gösterin.
5. **Zor:** 30 saniyede bir sorgulama (polling) yerine Server-Sent Events ile anlık bildirim. Hangi durumlarda polling daha doğru bir seçimdir, tartışın.

## Testler
`python -m pytest tests/test_notification_impact.py -q -k notification`

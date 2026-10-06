# Modül 1: identity (kimlik ve yetki)

**Sahip:** Kişi 1 | **Çalışma alanı:** `app/modules/identity/` ve `web/modules/identity/`
**İlgili dersler:** Python (sınıflar, istisnalar, tip ipuçları), Veritabanına Giriş (kısıtlar, JOIN), JavaScript (DOM, fetch)

## Öğrenme hedefleri
Bu modülü bitirdiğinizde şunları açıklayabilirsiniz:
1. Parola neden saklanmaz da "hash"lenir; `salt` ne işe yarar.
2. JWT nedir, sunucu oturumu nasıl hatırlamadan kullanıcıyı tanır.
3. Rol tabanlı yetkilendirme (RBAC) FastAPI'de `Depends` ile nasıl yazılır.
4. Bir iş akışı (başvuru, onay, askıya alma) durum alanıyla nasıl modellenir.

## Sorumluluk ve sınır
- **Yapar:** kayıt, giriş, kimlik doğrulama, rol kontrolü, hesap onayı/askıya alma.
- **Yapmaz:** ilan, rezervasyon, bildirim, istatistik. Başka modüle ihtiyaç olursa olay yayınlar (`app/config/events.py`).
- **Dışarıya verdiği tek şey:** `deps.py` (`current_user`, `require_roles`, `active_user`) ve `User` modeli. Diğer modüller bunları kullanır.

## Dosya turu
| Dosya | Görevi |
| --- | --- |
| `models.py` | `User` tablosu, `UserRole`, `AccountStatus` |
| `schemas.py` | Girdi doğrulama (Pydantic) ve dışarı verilen alanlar. `password_hash` burada yok, bu bilinçlidir |
| `service.py` | İş kuralları: `register`, `authenticate`, `review_account`, `suspend_account` |
| `deps.py` | Yetki bağımlılıkları. Router'lar `Depends(...)` ile bunları kullanır |
| `router.py` | HTTP uç noktaları (ince katman, iş kuralı içermez) |
| `module.py` | Modülü uygulamaya tanıtır (`SPEC`) |
| `sql/queries.sql` | Bu modülün tablolarına SQL çalışma defteri |
| `web/modules/identity/` | Giriş, kayıt sayfaları ve yönetici hesap paneli |

## Bir isteğin yolculuğu: giriş
```
Tarayıcı  POST /api/v1/auth/login {email, password}
  router.login()            -> sadece şemayı doğrular, service'i çağırır
  service.authenticate()    -> 1) hatalı deneme sınırı  2) kullanıcıyı bul
                               3) scrypt ile parola doğrula  4) hesap durumunu kontrol et
                               5) JWT üret
  Tarayıcı                  <- {access_token, user}; token localStorage'a yazılır
Sonraki her istek: Authorization: Bearer <token>  -> deps.current_user token'ı çözer
```

## Veritabanı
Tek tablo: `users`. `email` üzerinde UNIQUE indeks, `(role, status)` üzerinde bileşik indeks vardır.
SQL denemek için: `python tools/sqlshell.py app/modules/identity/sql/queries.sql`

## Kavram kutuları
- **Hash ve salt:** `core/security.py` her parola için rastgele 16 bayt `salt` üretir ve `scrypt` ile türetir. Aynı parolayı kullanan iki kullanıcının hash'i farklı olur.
- **Zamanlama saldırısı:** `service.authenticate` kullanıcı yokken de sahte bir hash'i doğrular. Böylece "bu e-posta kayıtlı mı?" sorusu yanıt süresinden anlaşılamaz.
- **Hata mesajı sızıntısı:** yanlış parola ve bilinmeyen e-posta aynı yanıtı verir (`auth.invalid_credentials`).
- **İş akışı durum alanı:** `PENDING_REVIEW -> ACTIVE | REJECTED`, `ACTIVE <-> SUSPENDED`. Geçersiz geçişler `409` döner.
- **Katman ayrımı:** router HTTP bilir, service iş kuralı bilir. `tests/test_identity.py` iki katmanı da dolaylı sınar.

## Alıştırmalar
1. **Kolay:** `RegisterIn` içine "parola en az bir rakam içermeli" doğrulayıcısı ekleyin. Önce başarısız bir test yazın (`tests/test_identity.py`), sonra geçirin.
2. **Kolay (SQL):** `queries.sql` içine "hiç ilan açmamış onaylı bağışçıları" bulan bir sorgu ekleyin (ipucu: `LEFT JOIN ... WHERE f.id IS NULL`).
3. **Orta:** `PATCH /api/v1/auth/me` uç noktası yazın: telefon ve adres güncellensin, rol ve durum değişmesin. Neden değişmemeli, bir test ile kanıtlayın.
4. **Orta (ön yüz):** Kayıt formuna "parolayı göster" düğmesi ekleyin. `innerHTML` kullanmadan yapın.
5. **Zor:** Access token süresini kısaltıp bir "refresh token" mekanizması tasarlayın. Önce `docs/ogrenme/guvenlik.md` içindeki token saklama tartışmasını okuyun, tasarımı yazıya dökün, sonra kodlayın.

## Testler
`python -m pytest tests/test_identity.py -q`

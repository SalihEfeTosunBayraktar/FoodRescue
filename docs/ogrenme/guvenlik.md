# Güvenlik: bu projede ne yapıldı, neden

Her başlık "tehdit -> önlem -> nerede" biçimindedir. Önlemlerin çoğu bir testle kanıtlıdır; testin adı yazılıdır.

## 1) Parolalar
- **Tehdit:** veritabanı sızarsa parolalar okunur.
- **Önlem:** scrypt + kullanıcıya özel rastgele salt (`core/security.py`). Parola hiçbir yerde düz saklanmaz veya loglanmaz.
- **Neden scrypt?** Kasıtlı yavaştır ve bellek ister; saldırganın deneme hızını düşürür. SHA-256 gibi hızlı özetler parola için uygun değildir.

## 2) Giriş
- **Tehdit:** parola tahmini; "bu e-posta kayıtlı mı?" sızıntısı.
- **Önlem:** e-posta başına hatalı deneme sınırı (`FailureLimiter`), tek tip hata mesajı, kullanıcı yokken de sahte hash doğrulaması.
- **Test:** `test_login_lockout_after_repeated_failures`, `test_wrong_password_and_unknown_email_look_the_same`.

## 3) Oturum belirteci (token) ve saklama ödünleşimi
- Token `localStorage`'da tutulur. Avantaj: basit, API'ye `Authorization` başlığıyla gider. Dezavantaj: sayfaya bir script enjekte edilirse (XSS) token okunabilir.
- Bu yüzden **arayüzde `innerHTML` yoktur**; tüm metin `textContent` ile eklenir.
- Alternatif: `httpOnly` çerez. Script okuyamaz ama CSRF'e karşı ek önlem (SameSite, CSRF belirteci) gerekir. Üretimde bu seçenek değerlendirilmelidir.

## 4) Yetkilendirme (kim neye erişir)
- **Tehdit:** giriş yapmış herhangi bir kullanıcı başkasının verisine erişir veya işlem yapar.
- **Önlem:** rol kontrolü `Depends` ile her uç noktada; **sahiplik** sorgu düzeyinde (`verify_pickup` yalnızca giriş yapan işletmenin rezervasyonlarını arar; `_owned_food` ilan sahibini denetler).
- **Test:** `test_other_donor_cannot_verify_someone_elses_reservation`, `test_only_owner_can_edit_or_cancel`, `test_notifications_are_private`.
- **Ders:** "giriş yaptı mı?" ile "bu işlemi yapmaya hakkı var mı?" farklı sorulardır. Eski prototipte ikincisi eksikti.

## 4b) Teslim kodları
- **Tehdit:** 6 haneli PIN'in denemeyle bulunması.
- **Önlem:** `secrets` ile üretim; arama işletmeyle daraltılmış; işletme başına 5 hatalı denemede 5 dakika kilit; kod tek kullanımlık; süreli.
- **Test:** `test_pin_guessing_is_locked_out`.
- **Dürüst not:** PIN yararlanıcının ekranında tekrar gösterilebilmesi için düz saklanır. Bu bilinçli bir ödünleşimdir; koruma, sorgunun daraltılması ve deneme sınırıdır.

## 5) Dosya yükleme
- **Tehdit:** `.png` adlı bir betik dosyası, çok büyük dosya, yol atlatma (`../../`).
- **Önlem:** içerik başlığı (magic bytes) kontrolü, boyut sınırı, dosya adı sunucuda rastgele üretilir (`save_photo`).
- **Test:** `test_photo_upload_checks_content_not_filename`.

## 6) Girdi doğrulama
- Pydantic şemaları uzunluk, aralık ve biçimi doğrular. İş kuralları (gelecekte bir saat, 24 saat sınırı, hijyen beyanı) serviste uygulanır.
- SQL enjeksiyonu: ORM parametreli sorgu kullanır; ham SQL yalnızca `sql/` çalışma defterlerinde ve sabit metindir.

## 7) Yapılandırma
- `SECRET_KEY` yerel dışında zorunludur; yerelde makineye özel bir anahtar `data/.dev_secret` içinde üretilir ve git dışında tutulur.
- `/docs` yalnızca yerelde açıktır. CORS varsayılan olarak kapalıdır.
- Demo parolası yalnızca yerel tohum veride bulunur.

## Hâlâ eksik olanlar (dürüst liste)
- Token iptali / yenileme yok. CSRF çerez moduna geçilirse gerekir.
- Hız sınırı bellek içidir: sunucu yeniden başlarsa sıfırlanır, çok süreçte paylaşılmaz.
- E-posta doğrulaması yok (kayıt sırasında adresin sahibi olunduğu kanıtlanmıyor).
- Güvenlik başlıkları (CSP, HSTS) eklenmedi; canlıda ters vekil (reverse proxy) ile eklenmeli.
- Kişisel veri saklama süreleri ve silme talebi (KVKK) tanımlı değil.

"""All user-facing server texts (errors, notifications, mail subjects). Turkish."""

# Hata mesajı anahtarı -> Türkçe metin. Kod yalnızca anahtarı (örn. 'food.unavailable') bilir. Metni
# değiştirmek ya da başka dile çevirmek için tek yer burasıdır. {ad} yer tutucular AppError(params)
# ile doldurulur.
ERRORS: dict[str, str] = {
    "auth.invalid_credentials": "E-posta veya şifre hatalı.",
    "auth.too_many_attempts": "Çok fazla hatalı deneme. {seconds} saniye sonra tekrar deneyin.",
    "auth.missing_token": "Giriş yapmanız gerekiyor.",
    "auth.invalid_token": "Oturumunuz geçersiz veya süresi dolmuş.",
    "auth.forbidden": "Bu işlem için yetkiniz yok.",
    "auth.email_taken": "Bu e-posta adresi zaten kayıtlı.",
    "auth.role_not_allowed": "Bu rol ile kayıt olunamaz.",
    "auth.account_rejected": "Başvurunuz reddedildi. Ayrıntı için yönetici ile iletişime geçin.",
    "auth.account_suspended": "Hesabınız askıya alındı.",
    "account.not_found": "Hesap bulunamadı.",
    "account.invalid_state": "Bu hesap için işlem şu an yapılamaz.",
    "donor.not_approved": "İşletmeniz henüz onaylanmadı, ilan açılamaz.",
    "account.not_active": "Hesabınız henüz aktif değil.",
    "food.not_found": "İlan bulunamadı.",
    "food.not_owner": "Bu ilan size ait değil.",
    "food.hygiene_required": "Hijyen beyanını onaylamanız gerekiyor.",
    "food.pickup_in_past": "Son teslim zamanı gelecekte olmalı.",
    "food.pickup_too_far": "Son teslim zamanı en fazla {hours} saat sonrası olabilir.",
    "food.unavailable": "Bu ilan artık müsait değil veya yeterli porsiyon kalmadı.",
    "food.not_editable": "Bu ilan artık düzenlenemez.",
    "food.bad_image": "Yalnızca JPEG, PNG veya WebP görsel yüklenebilir.",
    "food.image_too_large": "Görsel en fazla {mb} MB olabilir.",
    "reservation.not_found": "Rezervasyon bulunamadı.",
    "reservation.wrong_category": "Hesap türünüz bu ilan kategorisini rezerve edemez.",
    "reservation.too_many_active": "En fazla {limit} aktif rezervasyonunuz olabilir.",
    "reservation.too_many_portions": "Bu ilandan kişi başı en fazla {limit} porsiyon alınabilir.",
    "reservation.not_pending": "Yalnızca bekleyen rezervasyonlar için işlem yapılabilir.",
    "reservation.code_not_found": "Geçerli bir rezervasyon bulunamadı.",
    "reservation.not_owner": "Bu rezervasyon size ait değil.",
    "complaint.not_found": "Şikâyet bulunamadı.",
    "complaint.duplicate": "Bu rezervasyon için zaten şikâyet ilettiniz.",
    "complaint.closed": "Bu şikâyet zaten sonuçlandırılmış.",
    "notification.not_found": "Bildirim bulunamadı.",
}

# kind -> (title, body). Placeholders are filled from the event payload.
# Bildirim türü -> (başlık, gövde) şablonu. Yeni bildirim türü eklemek için buraya şablon,
# notification/subscribers.py içine eşleme eklenir.
NOTIFICATIONS: dict[str, tuple[str, str]] = {
    "account.approved": ("Başvurunuz onaylandı", "Hesabınız onaylandı, artık işlem yapabilirsiniz."),
    "account.rejected": ("Başvurunuz reddedildi", "Gerekçe: {note}"),
    "account.suspended": ("Hesabınız askıya alındı", "Gerekçe: {reason}"),
    "reservation.created.donor": ("Yeni rezervasyon", "{beneficiary} için {portions} porsiyon ayrıldı: {food_title}"),
    "reservation.collected.beneficiary": ("Teslim tamamlandı", "{food_title} teslim alındı. Afiyet olsun."),
    "reservation.expired.beneficiary": ("Rezervasyon süresi doldu", "{food_title} için süre doldu, porsiyonlar serbest bırakıldı."),
    "reservation.cancelled.donor": ("Rezervasyon iptal edildi", "{food_title} için {portions} porsiyonluk rezervasyon iptal edildi."),
    "reservation.cancelled.beneficiary": ("Rezervasyonunuz iptal edildi", "{food_title} ilanı kaldırıldığı için rezervasyonunuz iptal edildi."),
}

# Şikâyet eşiği aşılınca askıya alma gerekçesi olarak kayda yazılan metin.
COMPLAINT_SUSPEND_REASON = "Birden fazla kullanıcıdan şikâyet alındı, inceleme için askıya alındı."
MAIL_SUBJECT_PREFIX = "[FoodRescue] "

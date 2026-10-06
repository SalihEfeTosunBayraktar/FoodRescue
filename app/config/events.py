"""Domain event names. Modules talk to each other through these instead of importing services."""

# Olay adları sabit olarak tanımlanır; metin hatası (typo) yerine editörün hata vermesini sağlar.
ACCOUNT_REGISTERED = "account.registered"
ACCOUNT_REVIEWED = "account.reviewed"
ACCOUNT_SUSPENDED = "account.suspended"
ACCOUNT_REINSTATED = "account.reinstated"

FOOD_PUBLISHED = "food.published"
FOOD_CANCELLED = "food.cancelled"
FOOD_EXPIRED = "food.expired"

RESERVATION_CREATED = "reservation.created"
RESERVATION_COLLECTED = "reservation.collected"
RESERVATION_CANCELLED = "reservation.cancelled"
RESERVATION_EXPIRED = "reservation.expired"

COMPLAINT_FILED = "complaint.filed"
COMPLAINT_RESOLVED = "complaint.resolved"

# Sözleşme: her olay yükü (payload) üç alan taşır: kimin yaptığı (actor_id), neyin üzerinde
# (entity_type) ve hangi kayıt (entity_id). Denetim kaydı bu üçlüye dayanır.
# Every payload carries: actor_id (int | None), entity_type (str), entity_id (int).

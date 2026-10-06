"""Identity use-cases. This layer owns transactions: each public function commits once.

Ders notu (katmanlar): router -> service -> model. Router HTTP'yi, service iş kuralını,
model veriyi bilir. Böylece iş kuralları HTTP olmadan da test edilebilir.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import events
from app.core.clock import utcnow
from app.core.context import ctx_of
from app.core.errors import AppError
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.identity.models import REVIEWED_ROLES, AccountStatus, User, UserRole
from app.modules.identity.schemas import SELF_REGISTER_ROLES, RegisterIn

# Pre-computed once so that unknown e-mails cost the same time as wrong passwords.
# Bilinmeyen e-posta için de bir hash doğrulaması yapabilmek üzere önceden hesaplanmış sahte hash.
_DUMMY_HASH = hash_password("timing-equalizer")


# Kayıt iş akışı: doğrula -> oluştur -> olay yayınla -> tek seferde kaydet.
def register(db: Session, data: RegisterIn) -> User:
    # Savunma derinliği: şema zaten engeller, servis yine de kontrol eder (servis başka yerden de
    # çağrılabilir).
    if data.role not in SELF_REGISTER_ROLES:
        raise AppError("auth.role_not_allowed", 403)
    # Kurum rolleri incelemeye düşer, bireyler hemen aktif olur.
    status = AccountStatus.PENDING_REVIEW if data.role in REVIEWED_ROLES else AccountStatus.ACTIVE
    # Nesne oluşturmak veritabanına yazmaz; yalnızca bellekte hazırlar.
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name.strip(),
        role=data.role,
        status=status,
        phone=data.phone,
        organization_name=data.organization_name,
        license_number=data.license_number,
        address=data.address,
        latitude=data.latitude,
        longitude=data.longitude,
    )
    # Nesneyi oturuma (session) ekler: 'bunu kaydetmeyi planlıyorum'.
    db.add(user)
    try:
        # flush: değişiklikleri veritabanına GÖNDERİR ama işlemi (transaction) henüz bitirmez.
        # Böylece user.id oluşur ve UNIQUE(email) ihlali şimdi yakalanır.
        db.flush()  # assigns user.id and surfaces the UNIQUE(email) violation early
    # Veritabanı kısıt hatası = e-posta başkasında. İşlemi geri alıp kullanıcıya anlaşılır hata
    # veririz.
    except IntegrityError as exc:
        db.rollback()
        raise AppError("auth.email_taken", 409) from exc
    # Olay yayınla: denetim kaydı bunu dinler. Bu servis denetim modülünü tanımaz.
    ctx_of(db).bus.publish(
        db, events.ACCOUNT_REGISTERED, actor_id=user.id, entity_type="user", entity_id=user.id, role=user.role.value
    )
    # commit: işlemi bitirir, tüm değişiklikler KALICI olur. Her kullanım senaryosu sonunda tek
    # commit yapılır; arada hata olursa hiçbir şey kaydedilmez.
    db.commit()
    return user


# Giriş akışı. Güvenlik kararları sırayla: hız sınırı -> kullanıcı -> parola -> hesap durumu ->
# bilet.
def authenticate(db: Session, email: str, password: str) -> tuple[User, str]:
    ctx = ctx_of(db)
    limiter = ctx.login_limiter
    # Önce hız sınırı: kilitliyse parolaya hiç bakmayız (hash hesabı pahalıdır, kaba kuvvetin işini
    # kolaylaştırmayız).
    wait = limiter.retry_after(email)
    if wait:
        raise AppError("auth.too_many_attempts", 429, seconds=wait)

    # select(...).where(...): ORM'in SELECT * FROM users WHERE email = ? karşılığı. Parametre
    # bağlanır, SQL enjeksiyonu olmaz.
    user = db.scalar(select(User).where(User.email == email))
    # Always run one hash verification, even for unknown e-mails (prevents user enumeration by timing).
    # Kullanıcı olmasa bile hash doğrulaması yapılır: yanıt süresi 'bu e-posta kayıtlı mı?'
    # bilgisini sızdırmasın.
    valid = verify_password(password, user.password_hash if user else _DUMMY_HASH)
    # Yanlış parola ile bilinmeyen e-posta AYNI hatayı verir; saldırgan hesap varlığını öğrenemez.
    if not user or not valid:
        limiter.record_failure(email)
        raise AppError("auth.invalid_credentials", 401)

    # Doğru girişte sayaç sıfırlanır.
    limiter.reset(email)
    # Parola doğru ama hesap engelli: ancak parola doğrulandıktan SONRA söyleriz, aksi halde hesap
    # durumu sızar.
    if user.status == AccountStatus.REJECTED:
        raise AppError("auth.account_rejected", 403)
    if user.status == AccountStatus.SUSPENDED:
        raise AppError("auth.account_suspended", 403)
    # Her şey tamam: imzalı bilet üret.
    token = create_access_token(ctx.settings.secret_key, user.id, user.role.value, ctx.settings.token_ttl_minutes)
    return user, token


# ID ile kullanıcıyı getirir, yoksa 404 iş hatası fırlatır (tekrar eden kod tek yerde).
def get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user:
        raise AppError("account.not_found", 404)
    return user


# Yönetici paneli için filtreli liste: durum ve rol isteğe bağlı.
def list_accounts(db: Session, status: AccountStatus | None = None, role: UserRole | None = None) -> list[User]:
    # Sorgu parça parça kurulur; filtre varsa .where() eklenir (builder deseni).
    query = select(User).order_by(User.created_at.desc())
    if status:
        query = query.where(User.status == status)
    if role:
        query = query.where(User.role == role)
    return list(db.scalars(query))


# Yönetici onay/ret akışı. Yalnızca PENDING_REVIEW durumundaki hesap incelenebilir.
def review_account(db: Session, admin: User, user_id: int, approve: bool, note: str | None) -> User:
    user = get_user(db, user_id)
    # Geçersiz durum geçişini engelleriz (örn. reddedilmiş hesabı tekrar onaylamak). 409 Conflict:
    # isteğin mevcut durumla çeliştiğini söyler.
    if user.status != AccountStatus.PENDING_REVIEW:
        raise AppError("account.invalid_state", 409)
    # Tek satırlık koşullu atama (üçlü ifade).
    user.status = AccountStatus.ACTIVE if approve else AccountStatus.REJECTED
    user.review_note = note
    user.reviewed_at = utcnow()
    ctx_of(db).bus.publish(
        db,
        events.ACCOUNT_REVIEWED,
        actor_id=admin.id,
        entity_type="user",
        entity_id=user.id,
        user_id=user.id,
        approved=approve,
        note=note or "-",
    )
    db.commit()
    return user


# Askıya alma çekirdeği. commit ETMEZ: şikâyet akışı gibi başka bir işlemin parçası olarak çağrılır;
# commit eden dış fonksiyondur.
def suspend_account(db: Session, user: User, reason: str, actor_id: int | None) -> User:
    """Used by admins and by the complaint workflow. Does not commit when called inside another use-case."""
    # Yöneticiler askıya alınamaz: sistemin kendini kilitlemesini önler.
    if user.role == UserRole.ADMIN:
        raise AppError("account.invalid_state", 409)
    user.status = AccountStatus.SUSPENDED
    user.review_note = reason
    ctx_of(db).bus.publish(
        db, events.ACCOUNT_SUSPENDED, actor_id=actor_id, entity_type="user", entity_id=user.id, user_id=user.id, reason=reason
    )
    return user


# Yöneticinin doğrudan askıya alması: çekirdeği çağırır ve kendisi commit eder.
def suspend_account_by_admin(db: Session, admin: User, user_id: int, reason: str) -> User:
    user = suspend_account(db, get_user(db, user_id), reason, admin.id)
    db.commit()
    return user


# Askıdaki hesabı yeniden etkinleştirir. Yalnızca SUSPENDED durumdaki hesap için geçerli.
def reinstate_account(db: Session, admin: User, user_id: int) -> User:
    user = get_user(db, user_id)
    if user.status != AccountStatus.SUSPENDED:
        raise AppError("account.invalid_state", 409)
    user.status = AccountStatus.ACTIVE
    ctx_of(db).bus.publish(
        db, events.ACCOUNT_REINSTATED, actor_id=admin.id, entity_type="user", entity_id=user.id, user_id=user.id
    )
    db.commit()
    return user

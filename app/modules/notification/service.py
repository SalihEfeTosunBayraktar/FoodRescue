"""Notification use-cases.

Ders notu (Open/Closed): yeni bir bildirim türü eklemek için bu dosyaya dokunmayız; yalnızca
messages.NOTIFICATIONS'a bir şablon ve subscribers.py'ye bir eşleme ekleriz.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config.messages import MAIL_SUBJECT_PREFIX, NOTIFICATIONS
from app.core.clock import utcnow
from app.core.context import ctx_of
from app.core.errors import AppError
from app.modules.identity.models import User
from app.modules.notification.models import Notification


# Tek giriş noktası: şablonu doldurur, kutuya ekler ve e-postayı (şimdilik log'a) gönderir. commit
# ETMEZ: çağıran işlemin parçasıdır.
def notify(db: Session, user_id: int, kind: str, **params) -> Notification:
    """Create an in-app notification and hand a copy to the mailer. Does not commit."""
    # Şablonlar messages.py içindedir; kodda gömülü metin yok.
    title_tpl, body_tpl = NOTIFICATIONS[kind]
    title, body = title_tpl.format(**params), body_tpl.format(**params)
    # Başlık ve gövde GÖNDERİM ANINDA doldurulur ve saklanır; şablon sonradan değişse bile eski
    # bildirimler değişmez.
    item = Notification(user_id=user_id, kind=kind, title=title, body=body)
    db.add(item)
    # db.get: birincil anahtarla tek satır okuma; oturum önbelleğinde varsa sorgu bile atmaz.
    recipient = db.get(User, user_id)
    if recipient:
        # E-posta arayüzü soyuttur: bugün log'a yazar, yarın SMTP olur; bu satır değişmez.
        ctx_of(db).mailer.send(recipient.email, MAIL_SUBJECT_PREFIX + title, body)
    return item


# Kullanıcının son bildirimleri ve okunmamış sayısı.
def list_for(db: Session, user: User, limit: int = 50) -> tuple[int, list[Notification]]:
    # ORDER BY id DESC LIMIT 50: en yeniler önce, sınırsız büyümez.
    items = list(
        db.scalars(
            select(Notification).where(Notification.user_id == user.id).order_by(Notification.id.desc()).limit(limit)
        )
    )
    # SELECT COUNT(*) ... WHERE user_id=? AND read_at IS NULL. `IS NULL` yazılır, `= NULL` hiçbir
    # satırı eşleştirmez.
    unread = db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == user.id, Notification.read_at.is_(None)
        )
    )
    return unread, items


# Tek bildirimi okundu yapar.
def mark_read(db: Session, user: User, notification_id: int) -> Notification:
    item = db.get(Notification, notification_id)
    # Başkasının bildirimi için de 404 döneriz (403 değil): 'böyle bir kayıt var ama senin değil'
    # bilgisini bile vermeyiz.
    if not item or item.user_id != user.id:
        raise AppError("notification.not_found", 404)
    if item.read_at is None:
        item.read_at = utcnow()
        db.commit()
    return item


# Toplu okundu işaretleme.
def mark_all_read(db: Session, user: User) -> int:
    now = utcnow()
    items = list(
        db.scalars(select(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None)))
    )
    for item in items:
        item.read_at = now
    db.commit()
    return len(items)

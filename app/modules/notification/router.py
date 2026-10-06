from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.identity.deps import current_user
from app.modules.identity.models import User
from app.modules.notification import service
from app.modules.notification.schemas import NotificationList, NotificationOut

# Tüm yollar /api/v1/notifications ile başlar.
router = APIRouter(prefix="/api/v1/notifications", tags=["notification"])


# Giriş yapmış herkes (rol fark etmez) kendi kutusunu okuyabilir.
@router.get("", response_model=NotificationList)
def list_notifications(user: User = Depends(current_user), db: Session = Depends(get_db)):
    unread, items = service.list_for(db, user)
    return NotificationList(unread=unread, items=items)


# Toplu okundu.
@router.post("/read-all")
def read_all(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"updated": service.mark_all_read(db, user)}


# Tek okundu. Kayıt başkasınındır -> 404.
@router.post("/{notification_id}/read", response_model=NotificationOut)
def read_one(notification_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return service.mark_read(db, user, notification_id)

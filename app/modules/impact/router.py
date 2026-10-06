from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.identity.deps import active_user, require_admin
from app.modules.identity.models import User, UserRole
from app.modules.impact import service
from app.modules.impact.models import ComplaintStatus
from app.modules.impact.schemas import (
    AuditOut,
    ComplaintIn,
    ComplaintOut,
    DonorImpactOut,
    OverviewOut,
    ResolveIn,
    SummaryOut,
)

# Herkese açık istatistik (kişisel veri yok).
public_router = APIRouter(prefix="/api/v1/impact", tags=["impact"])
# Şikâyet gönderme: yararlanıcı ve barınak.
complaint_router = APIRouter(prefix="/api/v1/complaints", tags=["impact"])
# Yönetici: genel bakış, şikâyetler, denetim kaydı.
admin_router = APIRouter(prefix="/api/v1/admin", tags=["impact-admin"])


# Ana sayfa sayaçları; giriş gerekmez.
@public_router.get("/summary", response_model=SummaryOut)
def summary(db: Session = Depends(get_db)):
    return service.summary(db)


# Bağışçının kendi etki panosu.
@public_router.get("/mine", response_model=DonorImpactOut)
def mine(donor: User = Depends(active_user(UserRole.DONOR)), db: Session = Depends(get_db)):
    return service.donor_impact(db, donor)


# Şikâyet gönderme: yalnızca onaylı yararlanıcı/barınak.
@complaint_router.post("", response_model=ComplaintOut, status_code=201)
def file_complaint(
    payload: ComplaintIn,
    user: User = Depends(active_user(UserRole.BENEFICIARY, UserRole.SHELTER)),
    db: Session = Depends(get_db),
):
    return service.to_complaint_out(service.file_complaint(db, user, payload))


# Yönetici sayaçları.
@admin_router.get("/overview", response_model=OverviewOut)
def overview(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return service.overview(db)


# Şikâyet listesi (durum süzgeciyle).
@admin_router.get("/complaints", response_model=list[ComplaintOut])
def list_complaints(status: ComplaintStatus | None = None, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    return [service.to_complaint_out(c) for c in service.list_complaints(db, status)]


# Şikâyeti sonuçlandır.
@admin_router.post("/complaints/{complaint_id}/resolve", response_model=ComplaintOut)
def resolve_complaint(
    complaint_id: int, payload: ResolveIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    return service.to_complaint_out(
        service.resolve_complaint(db, admin, complaint_id, payload.action == "DISMISS", payload.note)
    )


# Denetim kaydı. limit/offset Query ile sınırlandırılır (en fazla 500).
@admin_router.get("/audit", response_model=list[AuditOut])
def audit(
    action: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return service.list_audit(db, action, limit, offset)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.notification import Notification, NotificationType
from app.models.user import User
from app.core.dependencies import get_current_user, require_admin


# ─── 🎓 STUDENT (shared with any logged-in user) ───
user_router = APIRouter(prefix="/api/notifications", tags=["🎓 Student"])


@user_router.get("/")
def my_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )


@user_router.put("/{nid}/read")
def mark_read(
    nid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    n = (
        db.query(Notification)
        .filter(Notification.id == nid, Notification.user_id == current_user.id)
        .first()
    )
    if not n:
        raise HTTPException(404, "Notification not found")
    n.is_read = True
    db.commit()
    return {"ok": True}


# ─── 🛡️ ADMIN ───
admin_router = APIRouter(prefix="/api/admin/notifications", tags=["🛡️ Admin"])


@admin_router.post("/broadcast")
def broadcast(
    title: str,
    message: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    users = db.query(User).all()
    for u in users:
        db.add(
            Notification(
                user_id=u.id,
                title=title,
                message=message,
                type=NotificationType.system,
            )
        )
    db.commit()
    return {"sent_to": len(users)}
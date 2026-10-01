from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.notification import Notification, NotificationType
from app.models.user import User
from app.core.dependencies import get_current_user, require_admin


# ═══════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════

class BroadcastRequest(BaseModel):
    title: str
    message: str


# ═══════════════════════════════════════════════════════════
# 🔔 USER ROUTER (any logged-in user)
# ═══════════════════════════════════════════════════════════

router = APIRouter(prefix="/api/notifications", tags=["🔔 Notifications"])


@router.get("/")
def my_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get my notifications."""
    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "type": n.type.value if n.type else "system",
            "is_read": n.is_read,
            "created_at": n.created_at,
        }
        for n in notifications
    ]


@router.put("/{nid}/read")
def mark_read(
    nid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a notification as read."""
    n = (
        db.query(Notification)
        .filter(
            Notification.id == nid,
            Notification.user_id == current_user.id,
        )
        .first()
    )
    if not n:
        raise HTTPException(404, "Notification not found")
    n.is_read = True
    db.commit()
    return {"ok": True}


@router.put("/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark all my notifications as read."""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return {"ok": True}


@router.delete("/{nid}", status_code=204)
def delete_notification(
    nid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a notification."""
    n = (
        db.query(Notification)
        .filter(
            Notification.id == nid,
            Notification.user_id == current_user.id,
        )
        .first()
    )
    if not n:
        raise HTTPException(404, "Notification not found")
    db.delete(n)
    db.commit()


# ═══════════════════════════════════════════════════════════
# 🛡️ ADMIN ROUTER
# ═══════════════════════════════════════════════════════════

admin_router = APIRouter(
    prefix="/api/admin/notifications",
    tags=["🛡️ Admin"],
)


@admin_router.post("/broadcast")
def broadcast_notification(
    payload: BroadcastRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Admin: send notification to ALL users."""
    users = db.query(User).all()

    if not users:
        return {"sent_to": 0}

    for u in users:
        notif = Notification(
            user_id=u.id,
            title=payload.title,
            message=payload.message,
            type=NotificationType.system,
            is_read=False,
        )
        db.add(notif)

    db.commit()
    return {"sent_to": len(users), "title": payload.title}
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.database import get_db
from app.models.payment import Payment, PaymentStatus
from app.models.user import User
from app.core.dependencies import require_admin, require_student


class PaymentCreate(BaseModel):
    course_id: int
    amount: float
    currency: str = "USD"
    gateway: str = "stripe"


# ─── 🎓 STUDENT ───
student_router = APIRouter(prefix="/api/payments", tags=["🎓 Student"])


@student_router.post("/", status_code=201)
def create_payment(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
    p = Payment(
        student_id=current_user.id,
        **payload.model_dump(),
        status=PaymentStatus.success,
        transaction_id=f"TXN-{int(datetime.utcnow().timestamp())}",
        paid_at=datetime.utcnow(),
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@student_router.get("/my")
def my_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
    return db.query(Payment).filter(Payment.student_id == current_user.id).all()


# ─── 🛡️ ADMIN ───
admin_router = APIRouter(prefix="/api/admin/payments", tags=["🛡️ Admin"])


@admin_router.get("/")
def all_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    q = db.query(Payment)
    if status:
        q = q.filter(Payment.status == status)
    return q.order_by(Payment.created_at.desc()).offset(skip).limit(limit).all()


@admin_router.post("/{payment_id}/refund")
def refund(
    payment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    p = db.query(Payment).filter(Payment.id == payment_id).first()
    if not p:
        raise HTTPException(404, "Payment not found")
    p.status = PaymentStatus.refunded
    db.commit()
    db.refresh(p)
    return p
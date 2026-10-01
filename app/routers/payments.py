import razorpay
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel

from app.database import get_db
from app.config import settings          # ⭐ ADD THIS
from app.models.payment import Payment, PaymentStatus
from app.models.course import Course
from app.models.user import User
from app.core.dependencies import require_student, require_admin


# ═══════════════════════════════════════════════════════════
# RAZORPAY CLIENT SETUP — FROM SETTINGS (not os.getenv)
# ═══════════════════════════════════════════════════════════
RAZORPAY_KEY_ID = settings.RAZORPAY_KEY_ID
RAZORPAY_KEY_SECRET = settings.RAZORPAY_KEY_SECRET

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

print(f"🔑 Razorpay configured")
print(f"   KEY ID: {RAZORPAY_KEY_ID}")
print(f"   SECRET length: {len(RAZORPAY_KEY_SECRET)}")


# ═══════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════
class OrderCreate(BaseModel):
    course_id: int
    amount: float


class PaymentVerify(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    course_id: int
    amount: float


# ═══════════════════════════════════════════════════════════
# 🎓 STUDENT ROUTES
# ═══════════════════════════════════════════════════════════
student_router = APIRouter(prefix="/api/payments", tags=["🎓 Student"])


@student_router.post("/create-order")
def create_razorpay_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
    """Create a Razorpay test order for a course."""
    print(f"📥 Create order: course_id={payload.course_id}, amount={payload.amount}")

    # Verify course
    course = db.query(Course).filter(Course.id == payload.course_id).first()
    if not course:
        raise HTTPException(404, "Course not found")

    # Verify amount
    if abs(float(course.price) - payload.amount) > 0.01:
        raise HTTPException(400, "Amount mismatch with course price")

    amount_in_subunits = int(payload.amount * 100)

    order_data = {
        "amount": amount_in_subunits,
        "currency": "INR",
        "receipt": f"course_{payload.course_id}_user_{current_user.id}",
        "notes": {
            "course_id": str(payload.course_id),
            "student_id": str(current_user.id),
            "course_title": course.title,
        },
    }

    try:
        order = client.order.create(data=order_data)
        print(f"✅ Order created: {order['id']}")
        return {
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": order["currency"],
            "key_id": RAZORPAY_KEY_ID,
        }
    except Exception as e:
        print(f"❌ Razorpay error: {type(e).__name__}: {str(e)}")
        print(f"❌ Order data: {order_data}")
        raise HTTPException(500, f"Order creation failed: {str(e)}")


@student_router.post("/verify")
def verify_payment(
    payload: PaymentVerify,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
    """Verify Razorpay signature and save payment."""
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": payload.razorpay_order_id,
            "razorpay_payment_id": payload.razorpay_payment_id,
            "razorpay_signature": payload.razorpay_signature,
        })
    except razorpay.errors.SignatureVerificationError:
        raise HTTPException(400, "Payment signature verification failed")

    payment = Payment(
        student_id=current_user.id,
        course_id=payload.course_id,
        amount=payload.amount,
        currency="INR",
        gateway="razorpay",
        transaction_id=payload.razorpay_payment_id,
        status=PaymentStatus.success,
        paid_at=datetime.utcnow(),
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    return {
        "id": payment.id,
        "status": "success",
        "transaction_id": payment.transaction_id,
        "amount": float(payment.amount),
        "course_id": payment.course_id,
    }


@student_router.get("/my")
def my_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
    """Student: my payment history."""
    payments = (
        db.query(Payment)
        .filter(Payment.student_id == current_user.id)
        .order_by(Payment.created_at.desc())
        .all()
    )
    return [
        {
            "id": p.id,
            "course_id": p.course_id,
            "course_title": p.course.title if p.course else None,
            "amount": float(p.amount),
            "currency": p.currency,
            "gateway": p.gateway,
            "transaction_id": p.transaction_id,
            "status": p.status.value if p.status else "pending",
            "paid_at": p.paid_at,
            "created_at": p.created_at,
        }
        for p in payments
    ]


# ═══════════════════════════════════════════════════════════
# 🛡️ ADMIN ROUTES
# ═══════════════════════════════════════════════════════════
admin_router = APIRouter(prefix="/api/admin/payments", tags=["🛡️ Admin"])


@admin_router.get("/")
def all_payments(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Admin: list all payments."""
    payments = db.query(Payment).order_by(Payment.created_at.desc()).all()
    return [
        {
            "id": p.id,
            "student_id": p.student_id,
            "student_name": p.student.full_name if p.student else None,
            "course_id": p.course_id,
            "course_title": p.course.title if p.course else None,
            "amount": float(p.amount),
            "currency": p.currency,
            "gateway": p.gateway,
            "transaction_id": p.transaction_id,
            "status": p.status.value if p.status else "pending",
            "paid_at": p.paid_at,
            "created_at": p.created_at,
        }
        for p in payments
    ]


@admin_router.post("/{payment_id}/refund")
def refund_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Admin: refund a payment."""
    p = db.query(Payment).filter(Payment.id == payment_id).first()
    if not p:
        raise HTTPException(404, "Payment not found")

    p.status = PaymentStatus.refunded
    db.commit()
    db.refresh(p)
    return {"ok": True, "id": p.id, "status": p.status.value}


@student_router.get("/debug")
def debug_razorpay(
    current_user: User = Depends(require_student),
):
    """
    Debug endpoint — verify Razorpay keys are working.
    """
    import razorpay as rz
    from app.config import settings
    
    result = {
        "key_id_loaded": settings.RAZORPAY_KEY_ID,
        "key_id_length": len(settings.RAZORPAY_KEY_ID),
        "key_id_valid_prefix": settings.RAZORPAY_KEY_ID.startswith("rzp_test_"),
        "secret_length": len(settings.RAZORPAY_KEY_SECRET),
        "secret_loaded": bool(settings.RAZORPAY_KEY_SECRET),
        "test_order_created": False,
        "test_order_id": None,
        "error": None,
    }

    # Try creating a small test order
    try:
        fresh_client = rz.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        test_order = fresh_client.order.create(data={
            "amount": 100,  # 1 rupee
            "currency": "INR",
            "receipt": f"debug_{current_user.id}_{int(datetime.utcnow().timestamp())}",
        })
        result["test_order_created"] = True
        result["test_order_id"] = test_order["id"]
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {str(e)}"

    return result
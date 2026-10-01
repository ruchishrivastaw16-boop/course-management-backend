from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.course import Course, CourseStatus
from app.models.user import User, UserRole
from app.core.dependencies import (
    get_current_user,
    require_admin,
    require_student,
    require_instructor,
)


# ═══════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════
class EnrollmentResponse(BaseModel):
    id: int
    student_id: int
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    course_id: int
    course_title: Optional[str] = None
    course_slug: Optional[str] = None
    course_thumbnail: Optional[str] = None
    course_category: Optional[str] = None
    course_level: Optional[str] = None
    instructor_name: Optional[str] = None
    status: str
    progress: float
    enrolled_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EnrollmentCreate(BaseModel):
    course_id: int


class ProgressUpdate(BaseModel):
    progress: float = Field(..., ge=0, le=100)


# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════
def _enrich(e: Enrollment) -> dict:
    """
    Enrich enrollment with course + student details.
    Safe fallbacks for missing fields.
    """
    course = e.course
    instructor = course.instructor if course else None

    return {
        "id": e.id,
        "student_id": e.student_id,
        "student_name": e.student.full_name if e.student else None,
        "student_email": e.student.email if e.student else None,
        "course_id": e.course_id,
        "course_title": course.title if course else None,
        "course_slug": course.slug if course else None,
        "course_thumbnail": course.thumbnail if course else None,
        "course_category": course.category if course else None,
        "course_level": course.level.value if course and course.level else None,
        "instructor_name": instructor.full_name if instructor else None,
        "status": e.status.value if e.status else "active",
        "progress": float(e.progress) if e.progress is not None else 0.0,
        "enrolled_at": e.enrolled_at,
        "completed_at": e.completed_at,
    }


# ═══════════════════════════════════════════════════════════
# 🎓 STUDENT — Enrollments
# ═══════════════════════════════════════════════════════════
student_router = APIRouter(prefix="/api/enrollments", tags=["🎓 Student"])


@student_router.post("/", response_model=EnrollmentResponse, status_code=201)
def enroll(
    payload: EnrollmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
    """Student: enroll in a published course."""
    course = db.query(Course).filter(Course.id == payload.course_id).first()
    if not course:
        raise HTTPException(404, "Course not found")
    if course.status != CourseStatus.published:
        raise HTTPException(400, "Course not available")

    existing = (
        db.query(Enrollment)
        .filter(
            Enrollment.student_id == current_user.id,
            Enrollment.course_id == course.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(400, "Already enrolled")

    enrollment = Enrollment(
        student_id=current_user.id,
        course_id=course.id,
        progress=0,
    )
    course.students_count = (course.students_count or 0) + 1
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return _enrich(enrollment)


@student_router.get("/my", response_model=List[EnrollmentResponse])
def my_enrollments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
    """Student: my enrollments with full course details."""
    rows = (
        db.query(Enrollment)
        .filter(Enrollment.student_id == current_user.id)
        .order_by(Enrollment.enrolled_at.desc())
        .all()
    )
    return [_enrich(e) for e in rows]


@student_router.get("/{enrollment_id}", response_model=EnrollmentResponse)
def get_enrollment(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
    """Student: get single enrollment details."""
    e = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not e:
        raise HTTPException(404, "Enrollment not found")
    if e.student_id != current_user.id:
        raise HTTPException(403, "Not your enrollment")
    return _enrich(e)


@student_router.put("/{enrollment_id}/progress", response_model=EnrollmentResponse)
def update_progress(
    enrollment_id: int,
    payload: ProgressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
    """Student: update my enrollment progress."""
    e = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not e:
        raise HTTPException(404, "Enrollment not found")
    if e.student_id != current_user.id:
        raise HTTPException(403, "Not your enrollment")

    e.progress = payload.progress

    # Auto-mark completed if progress reaches 100
    if payload.progress >= 100:
        e.status = EnrollmentStatus.completed
        e.completed_at = datetime.utcnow()
    elif e.status == EnrollmentStatus.completed and payload.progress < 100:
        # Revert if progress drops below 100
        e.status = EnrollmentStatus.active
        e.completed_at = None

    db.commit()
    db.refresh(e)
    return _enrich(e)


@student_router.delete("/{enrollment_id}", status_code=204)
def drop(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
    """Student: drop my enrollment."""
    e = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not e:
        raise HTTPException(404, "Enrollment not found")
    if e.student_id != current_user.id:
        raise HTTPException(403, "Not your enrollment")

    if e.course:
        e.course.students_count = max(0, (e.course.students_count or 1) - 1)
    db.delete(e)
    db.commit()


# ═══════════════════════════════════════════════════════════
# 👨‍🏫 INSTRUCTOR — Enrollments
# ═══════════════════════════════════════════════════════════
instructor_router = APIRouter(
    prefix="/api/instructor/enrollments",
    tags=["👨‍🏫 Instructor"],
)


@instructor_router.get(
    "/all-students",
    summary="Get all students across instructor's courses",
)
def all_my_students(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_instructor),
):
    """Instructor: all enrolled students across my courses."""
    courses = db.query(Course).filter(Course.instructor_id == current_user.id).all()
    course_ids = [c.id for c in courses]

    if not course_ids:
        return []

    enrollments = (
        db.query(Enrollment)
        .filter(Enrollment.course_id.in_(course_ids))
        .order_by(Enrollment.enrolled_at.desc())
        .all()
    )

    return [_enrich(e) for e in enrollments]


@instructor_router.get("/course/{course_id}", response_model=List[EnrollmentResponse])
def course_students(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Instructor: students in my course. Admin: any course."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(404, "Course not found")

    if current_user.role == UserRole.instructor and course.instructor_id != current_user.id:
        raise HTTPException(403, "Not your course")
    if current_user.role not in [UserRole.admin, UserRole.instructor]:
        raise HTTPException(403, "Access denied")

    rows = (
        db.query(Enrollment)
        .filter(Enrollment.course_id == course_id)
        .order_by(Enrollment.enrolled_at.desc())
        .all()
    )
    return [_enrich(e) for e in rows]


@instructor_router.get("/course/{course_id}/stats")
def course_stats(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Instructor: enrollment stats for my course."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(404, "Course not found")

    if current_user.role == UserRole.instructor and course.instructor_id != current_user.id:
        raise HTTPException(403, "Not your course")
    if current_user.role not in [UserRole.admin, UserRole.instructor]:
        raise HTTPException(403, "Access denied")

    rows = db.query(Enrollment).filter(Enrollment.course_id == course_id).all()
    active = sum(1 for r in rows if r.status == EnrollmentStatus.active)
    completed = sum(1 for r in rows if r.status == EnrollmentStatus.completed)
    dropped = sum(1 for r in rows if r.status == EnrollmentStatus.dropped)
    avg = sum(float(r.progress or 0) for r in rows) / len(rows) if rows else 0

    return {
        "total_enrollments": len(rows),
        "active": active,
        "completed": completed,
        "dropped": dropped,
        "avg_progress": round(avg, 2),
    }


# ═══════════════════════════════════════════════════════════
# 🛡️ ADMIN — Enrollments
# ═══════════════════════════════════════════════════════════
admin_router = APIRouter(prefix="/api/admin/enrollments", tags=["🛡️ Admin"])


@admin_router.get("/", response_model=List[EnrollmentResponse])
def all_enrollments(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    course_id: Optional[int] = None,
    student_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Admin: list all enrollments with filters."""
    q = db.query(Enrollment)
    if course_id:
        q = q.filter(Enrollment.course_id == course_id)
    if student_id:
        q = q.filter(Enrollment.student_id == student_id)
    if status:
        q = q.filter(Enrollment.status == status)

    rows = (
        q.order_by(Enrollment.enrolled_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_enrich(e) for e in rows]


@admin_router.get("/{enrollment_id}", response_model=EnrollmentResponse)
def admin_get_enrollment(
    enrollment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Admin: get single enrollment."""
    e = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not e:
        raise HTTPException(404, "Enrollment not found")
    return _enrich(e)


@admin_router.delete("/{enrollment_id}", status_code=204)
def admin_delete(
    enrollment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Admin: delete any enrollment."""
    e = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not e:
        raise HTTPException(404, "Enrollment not found")
    db.delete(e)
    db.commit()
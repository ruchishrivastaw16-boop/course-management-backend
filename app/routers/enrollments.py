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
    course_id: int
    course_title: Optional[str] = None
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
    return {
        "id": e.id,
        "student_id": e.student_id,
        "student_name": e.student.full_name if e.student else None,
        "course_id": e.course_id,
        "course_title": e.course.title if e.course else None,
        "status": e.status.value,
        "progress": float(e.progress or 0),
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

    enrollment = Enrollment(student_id=current_user.id, course_id=course.id)
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
    rows = (
        db.query(Enrollment)
        .filter(Enrollment.student_id == current_user.id)
        .order_by(Enrollment.enrolled_at.desc())
        .all()
    )
    return [_enrich(e) for e in rows]


@student_router.put("/{enrollment_id}/progress", response_model=EnrollmentResponse)
def update_progress(
    enrollment_id: int,
    payload: ProgressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
    e = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not e:
        raise HTTPException(404, "Enrollment not found")
    if e.student_id != current_user.id:
        raise HTTPException(403, "Not your enrollment")

    e.progress = payload.progress
    if payload.progress >= 100:
        e.status = EnrollmentStatus.completed
        e.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(e)
    return _enrich(e)


@student_router.delete("/{enrollment_id}", status_code=204)
def drop(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
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
    """
    Instructor: Get all enrolled students across all my courses.
    """
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

    result = []
    for e in enrollments:
        result.append({
            "id": e.id,
            "student_id": e.student_id,
            "student_name": e.student.full_name if e.student else None,
            "student_email": e.student.email if e.student else None,
            "course_id": e.course_id,
            "course_title": e.course.title if e.course else None,
            "status": e.status.value,
            "progress": float(e.progress or 0),
            "enrolled_at": e.enrolled_at,
            "completed_at": e.completed_at,
        })
    return result


@instructor_router.get("/course/{course_id}", response_model=List[EnrollmentResponse])
def course_students(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    q = db.query(Enrollment)
    if course_id:
        q = q.filter(Enrollment.course_id == course_id)
    if student_id:
        q = q.filter(Enrollment.student_id == student_id)
    rows = q.order_by(Enrollment.enrolled_at.desc()).offset(skip).limit(limit).all()
    return [_enrich(e) for e in rows]


@admin_router.delete("/{enrollment_id}", status_code=204)
def admin_delete(
    enrollment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    e = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not e:
        raise HTTPException(404, "Enrollment not found")
    db.delete(e)
    db.commit()
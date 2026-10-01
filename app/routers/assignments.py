from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.database import get_db
from app.models.assignment import Assignment
from app.models.course import Course
from app.models.user import User, UserRole
from app.models.enrollment import Enrollment
from app.models.submission import Submission, SubmissionStatus
from app.core.dependencies import (
    get_current_user,
    require_instructor,
    require_student,
    require_admin,
)


# ═══════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════

class AssignmentCreate(BaseModel):
    course_id: int
    title: str
    description: Optional[str] = None
    max_score: int = 100
    due_date: Optional[datetime] = None
    attachment_url: Optional[str] = None


class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    max_score: Optional[int] = None
    due_date: Optional[datetime] = None
    attachment_url: Optional[str] = None


class SubmissionCreate(BaseModel):
    assignment_id: int
    file_url: Optional[str] = None
    text_answer: Optional[str] = None


class GradeCreate(BaseModel):
    grade: float
    feedback: Optional[str] = None


# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════

def _enrich_assignment(a: Assignment, submission: Optional[Submission] = None) -> dict:
    """Convert Assignment to dict with submission info."""
    return {
        "id": a.id,
        "course_id": a.course_id,
        "course_title": a.course.title if a.course else None,
        "title": a.title,
        "description": a.description,
        "max_score": a.max_score,
        "due_date": a.due_date,
        "attachment_url": a.attachment_url,
        "created_at": a.created_at,
        "submission_id": submission.id if submission else None,
        "submission_status": submission.status.value if submission else None,
        "grade": float(submission.grade) if submission and submission.grade is not None else None,
        "feedback": submission.feedback if submission else None,
        "submitted_at": submission.submitted_at if submission else None,
        "file_url": submission.file_url if submission else None,
        "text_answer": submission.text_answer if submission else None,
    }


# ═══════════════════════════════════════════════════════════
# 🌐 PUBLIC / STUDENT ROUTES
# ═══════════════════════════════════════════════════════════

public_router = APIRouter(prefix="/api/assignments", tags=["🌐 Public"])


@public_router.get("/my", summary="Student's assignments from enrolled courses")
def my_assignments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Student: Get all assignments from courses they're enrolled in.
    Includes submission status if already submitted.
    """
    # 1. Get student's enrolled courses
    enrollments = (
        db.query(Enrollment)
        .filter(Enrollment.student_id == current_user.id)
        .all()
    )
    course_ids = [e.course_id for e in enrollments]

    if not course_ids:
        return []

    # 2. Get all assignments from those courses
    assignments = (
        db.query(Assignment)
        .filter(Assignment.course_id.in_(course_ids))
        .order_by(Assignment.due_date.asc())
        .all()
    )

    # 3. For each assignment, check submission status
    result = []
    for a in assignments:
        submission = (
            db.query(Submission)
            .filter(
                Submission.assignment_id == a.id,
                Submission.student_id == current_user.id,
            )
            .first()
        )
        result.append(_enrich_assignment(a, submission))

    return result


@public_router.get("/course/{course_id}")
def course_assignments(
    course_id: int,
    db: Session = Depends(get_db),
):
    """Public: list assignments for a specific course."""
    assignments = (
        db.query(Assignment)
        .filter(Assignment.course_id == course_id)
        .order_by(Assignment.due_date.asc())
        .all()
    )
    return [_enrich_assignment(a) for a in assignments]


@public_router.get("/{assignment_id}")
def get_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
):
    """Get single assignment details."""
    a = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not a:
        raise HTTPException(404, "Assignment not found")
    return _enrich_assignment(a)


# ═══════════════════════════════════════════════════════════
# 👨‍🏫 INSTRUCTOR ROUTES
# ═══════════════════════════════════════════════════════════

instructor_router = APIRouter(
    prefix="/api/instructor/assignments",
    tags=["👨‍🏫 Instructor"],
)


@instructor_router.post("/", status_code=201)
def create_assignment(
    payload: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_instructor),
):
    """Instructor: create assignment for own course."""
    course = db.query(Course).filter(Course.id == payload.course_id).first()
    if not course or course.instructor_id != current_user.id:
        raise HTTPException(404, "Course not found or not yours")

    assignment = Assignment(**payload.model_dump())
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return _enrich_assignment(assignment)


@instructor_router.get("/course/{course_id}")
def instructor_course_assignments(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_instructor),
):
    """Instructor: list assignments for own course."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course or course.instructor_id != current_user.id:
        raise HTTPException(404, "Course not found or not yours")

    assignments = (
        db.query(Assignment)
        .filter(Assignment.course_id == course_id)
        .order_by(Assignment.due_date.asc())
        .all()
    )
    return [_enrich_assignment(a) for a in assignments]


@instructor_router.put("/{assignment_id}")
def update_assignment(
    assignment_id: int,
    payload: AssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_instructor),
):
    """Instructor: update own assignment."""
    a = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not a or a.course.instructor_id != current_user.id:
        raise HTTPException(404, "Assignment not found or not yours")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(a, k, v)
    db.commit()
    db.refresh(a)
    return _enrich_assignment(a)


@instructor_router.delete("/{assignment_id}", status_code=204)
def delete_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_instructor),
):
    """Instructor: delete own assignment."""
    a = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not a or a.course.instructor_id != current_user.id:
        raise HTTPException(404, "Assignment not found or not yours")
    db.delete(a)
    db.commit()


@instructor_router.get("/submissions/{assignment_id}")
def get_submissions(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_instructor),
):
    """Instructor: view all submissions for own assignment."""
    a = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not a or a.course.instructor_id != current_user.id:
        raise HTTPException(404, "Assignment not found or not yours")

    submissions = (
        db.query(Submission)
        .filter(Submission.assignment_id == assignment_id)
        .all()
    )

    result = []
    for s in submissions:
        result.append({
            "id": s.id,
            "assignment_id": s.assignment_id,
            "student_id": s.student_id,
            "student_name": s.student.full_name if s.student else None,
            "student_email": s.student.email if s.student else None,
            "file_url": s.file_url,
            "text_answer": s.text_answer,
            "grade": float(s.grade) if s.grade is not None else None,
            "feedback": s.feedback,
            "status": s.status.value,
            "submitted_at": s.submitted_at,
            "graded_at": s.graded_at,
        })
    return result


@instructor_router.put("/submissions/{submission_id}/grade")
def grade_submission(
    submission_id: int,
    payload: GradeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_instructor),
):
    """Instructor: grade a student's submission."""
    s = db.query(Submission).filter(Submission.id == submission_id).first()
    if not s or s.assignment.course.instructor_id != current_user.id:
        raise HTTPException(404, "Submission not found or not yours")

    s.grade = payload.grade
    s.feedback = payload.feedback
    s.status = SubmissionStatus.graded
    s.graded_at = datetime.utcnow()
    db.commit()
    db.refresh(s)
    return {
        "id": s.id,
        "grade": float(s.grade),
        "feedback": s.feedback,
        "status": s.status.value,
        "graded_at": s.graded_at,
    }


# ═══════════════════════════════════════════════════════════
# 🎓 STUDENT SUBMISSION ROUTES
# ═══════════════════════════════════════════════════════════

submission_router = APIRouter(prefix="/api/submissions", tags=["🎓 Student"])


@submission_router.post("/", status_code=201)
def submit_assignment(
    payload: SubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
    """Student: submit an assignment."""
    a = db.query(Assignment).filter(Assignment.id == payload.assignment_id).first()
    if not a:
        raise HTTPException(404, "Assignment not found")

    # Check student is enrolled in this course
    enrolled = (
        db.query(Enrollment)
        .filter(
            Enrollment.student_id == current_user.id,
            Enrollment.course_id == a.course_id,
        )
        .first()
    )
    if not enrolled:
        raise HTTPException(403, "Not enrolled in this course")

    # Check if already submitted
    existing = (
        db.query(Submission)
        .filter(
            Submission.assignment_id == payload.assignment_id,
            Submission.student_id == current_user.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(400, "Already submitted")

    submission = Submission(
        student_id=current_user.id,
        **payload.model_dump(),
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return _enrich_assignment(a, submission)


@submission_router.get("/my")
def my_submissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
    """Student: view own submissions."""
    submissions = (
        db.query(Submission)
        .filter(Submission.student_id == current_user.id)
        .order_by(Submission.submitted_at.desc())
        .all()
    )

    result = []
    for s in submissions:
        result.append({
            "id": s.id,
            "assignment_id": s.assignment_id,
            "assignment_title": s.assignment.title if s.assignment else None,
            "max_score": s.assignment.max_score if s.assignment else None,
            "file_url": s.file_url,
            "text_answer": s.text_answer,
            "grade": float(s.grade) if s.grade is not None else None,
            "feedback": s.feedback,
            "status": s.status.value,
            "submitted_at": s.submitted_at,
            "graded_at": s.graded_at,
        })
    return result


# ═══════════════════════════════════════════════════════════
# 🛡️ ADMIN ROUTES
# ═══════════════════════════════════════════════════════════

admin_router = APIRouter(prefix="/api/admin/assignments", tags=["🛡️ Admin"])


@admin_router.get("/")
def all_assignments(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Admin: view all assignments."""
    assignments = db.query(Assignment).all()
    return [_enrich_assignment(a) for a in assignments]


@admin_router.delete("/{assignment_id}", status_code=204)
def admin_delete_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Admin: delete any assignment."""
    a = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not a:
        raise HTTPException(404, "Assignment not found")
    db.delete(a)
    db.commit()
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.database import get_db
from app.models.submission import Submission, SubmissionStatus
from app.models.assignment import Assignment
from app.models.user import User
from app.core.dependencies import require_instructor, require_student, require_admin


class SubmissionCreate(BaseModel):
    assignment_id: int
    file_url: Optional[str] = None
    text_answer: Optional[str] = None


class GradeCreate(BaseModel):
    grade: float
    feedback: Optional[str] = None


# ─── 🎓 STUDENT ───
student_router = APIRouter(prefix="/api/submissions", tags=["🎓 Student"])


@student_router.post("/", status_code=201)
def submit(
    payload: SubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
    a = db.query(Assignment).filter(Assignment.id == payload.assignment_id).first()
    if not a:
        raise HTTPException(404, "Assignment not found")
    s = Submission(student_id=current_user.id, **payload.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@student_router.get("/my")
def my_submissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
    return db.query(Submission).filter(Submission.student_id == current_user.id).all()


# ─── 👨‍🏫 INSTRUCTOR — Grading ───
instructor_router = APIRouter(
    prefix="/api/instructor/submissions", tags=["👨‍🏫 Instructor"]
)


@instructor_router.get("/assignment/{assignment_id}")
def assignment_submissions(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_instructor),
):
    a = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not a or a.course.instructor_id != current_user.id:
        raise HTTPException(404, "Assignment not found or not yours")
    return db.query(Submission).filter(Submission.assignment_id == assignment_id).all()


@instructor_router.put("/{submission_id}/grade")
def grade(
    submission_id: int,
    payload: GradeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_instructor),
):
    s = db.query(Submission).filter(Submission.id == submission_id).first()
    if not s or s.assignment.course.instructor_id != current_user.id:
        raise HTTPException(404, "Submission not found or not yours")
    s.grade = payload.grade
    s.feedback = payload.feedback
    s.status = SubmissionStatus.graded
    s.graded_at = datetime.utcnow()
    db.commit()
    db.refresh(s)
    return s


# ─── 🛡️ ADMIN ───
admin_router = APIRouter(prefix="/api/admin/submissions", tags=["🛡️ Admin"])


@admin_router.get("/")
def all_submissions(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return db.query(Submission).all()
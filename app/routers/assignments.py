from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.database import get_db
from app.models.assignment import Assignment
from app.models.course import Course
from app.models.user import User
from app.core.dependencies import require_instructor, require_admin


class AssignmentCreate(BaseModel):
    course_id: int
    title: str
    description: Optional[str] = None
    max_score: int = 100
    due_date: Optional[datetime] = None


# ─── 🌐 PUBLIC (students can view) ───
public_router = APIRouter(prefix="/api/assignments", tags=["🌐 Public"])


@public_router.get("/course/{course_id}")
def public_assignments(course_id: int, db: Session = Depends(get_db)):
    return db.query(Assignment).filter(Assignment.course_id == course_id).all()


# ─── 👨‍🏫 INSTRUCTOR ───
instructor_router = APIRouter(
    prefix="/api/instructor/assignments", tags=["👨‍🏫 Instructor"]
)


@instructor_router.post("/", status_code=201)
def create_assignment(
    payload: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_instructor),
):
    course = db.query(Course).filter(Course.id == payload.course_id).first()
    if not course or course.instructor_id != current_user.id:
        raise HTTPException(404, "Course not found or not yours")
    a = Assignment(**payload.model_dump())
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


@instructor_router.get("/course/{course_id}")
def my_assignments(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_instructor),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course or course.instructor_id != current_user.id:
        raise HTTPException(404, "Course not found or not yours")
    return db.query(Assignment).filter(Assignment.course_id == course_id).all()


@instructor_router.put("/{assignment_id}")
def update_assignment(
    assignment_id: int,
    payload: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_instructor),
):
    a = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not a or a.course.instructor_id != current_user.id:
        raise HTTPException(404, "Assignment not found or not yours")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(a, k, v)
    db.commit()
    db.refresh(a)
    return a


@instructor_router.delete("/{assignment_id}", status_code=204)
def delete_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_instructor),
):
    a = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not a or a.course.instructor_id != current_user.id:
        raise HTTPException(404, "Assignment not found or not yours")
    db.delete(a)
    db.commit()


# ─── 🛡️ ADMIN (delete any assignment) ───
admin_router = APIRouter(prefix="/api/admin/assignments", tags=["🛡️ Admin"])


@admin_router.delete("/{assignment_id}", status_code=204)
def admin_delete_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    a = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not a:
        raise HTTPException(404, "Assignment not found")
    db.delete(a)
    db.commit()
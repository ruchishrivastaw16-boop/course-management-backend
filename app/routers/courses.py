from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.course import Course, CourseStatus
from app.models.module import Module
from app.models.lesson import Lesson
from app.models.user import User
from app.schemas.course import (
    CourseCreate, CourseUpdate, CourseResponse, CourseDetailResponse,
    ModuleCreate, ModuleResponse, LessonCreate, LessonResponse,
)
from app.core.dependencies import get_current_user, require_instructor, require_admin


def _enrich(course: Course) -> dict:
    d = CourseResponse.model_validate(course).model_dump()
    d["instructor_name"] = course.instructor.full_name if course.instructor else None
    return d


# ═══════════════════════════════════════════════════════════
# 🌐 PUBLIC ROUTER
# ═══════════════════════════════════════════════════════════
public_router = APIRouter(prefix="/api/courses", tags=["🌐 Public"])


@public_router.get("/", response_model=List[CourseResponse])
def list_courses(
    category: Optional[str] = None,
    level: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Course).filter(Course.status == CourseStatus.published)
    if category:
        q = q.filter(Course.category == category)
    if level:
        q = q.filter(Course.level == level)
    if search:
        q = q.filter(Course.title.ilike(f"%{search}%"))
    return [_enrich(c) for c in q.all()]


@public_router.get("/{slug}", response_model=CourseDetailResponse)
def get_course(slug: str, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.slug == slug).first()
    if not course:
        raise HTTPException(404, "Course not found")
    data = _enrich(course)
    data["modules"] = [
        ModuleResponse.model_validate(m).model_dump() for m in course.modules
    ]
    return data


# ═══════════════════════════════════════════════════════════
# 👨‍🏫 INSTRUCTOR ROUTER
# ═══════════════════════════════════════════════════════════
instructor_router = APIRouter(
    prefix="/api/instructor/courses",
    tags=["👨‍🏫 Instructor"],
)


# ─── List ───
@instructor_router.get("/my-courses", response_model=List[CourseResponse])
def my_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_instructor),
):
    courses = db.query(Course).filter(Course.instructor_id == current_user.id).all()
    return [_enrich(c) for c in courses]


# ─── Create ───
@instructor_router.post("/", response_model=CourseResponse, status_code=201)
def create_course(
    payload: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_instructor),
):
    if db.query(Course).filter(Course.slug == payload.slug).first():
        raise HTTPException(400, "Slug already exists")
    course = Course(
        **payload.model_dump(),
        instructor_id=current_user.id,
        status=CourseStatus.pending,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return _enrich(course)


# ─── Update ───
@instructor_router.put("/{course_id}", response_model=CourseResponse)
def update_course(
    course_id: int,
    payload: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_instructor),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(404, "Course not found")
    if course.instructor_id != current_user.id:
        raise HTTPException(403, "Not your course")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(course, k, v)
    db.commit()
    db.refresh(course)
    return _enrich(course)


# ─── Delete ───
@instructor_router.delete("/{course_id}", status_code=204)
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_instructor),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(404, "Course not found")
    if course.instructor_id != current_user.id:
        raise HTTPException(403, "Not your course")
    db.delete(course)
    db.commit()


# ─── Add Module (instructor, own course) ───
@instructor_router.post(
    "/{course_id}/modules",
    response_model=ModuleResponse,
    status_code=201,
)
def add_module(
    course_id: int,
    payload: ModuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_instructor),
):
    """Instructor: add module to own course."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course or course.instructor_id != current_user.id:
        raise HTTPException(404, "Course not found or not yours")

    module = Module(course_id=course_id, **payload.model_dump())
    db.add(module)
    db.commit()
    db.refresh(module)
    return module


# ─── Add Lesson (instructor, own module) ───
@instructor_router.post(
    "/modules/{module_id}/lessons",
    response_model=LessonResponse,
    status_code=201,
)
def add_lesson(
    module_id: int,
    payload: LessonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_instructor),
):
    """Instructor: add lesson to own module."""
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module or module.course.instructor_id != current_user.id:
        raise HTTPException(404, "Module not found or not yours")

    lesson = Lesson(module_id=module_id, **payload.model_dump())
    db.add(lesson)
    module.course.lessons_count = (module.course.lessons_count or 0) + 1
    db.commit()
    db.refresh(lesson)
    return lesson


# ═══════════════════════════════════════════════════════════
# 🛡️ ADMIN ROUTER
# ═══════════════════════════════════════════════════════════
admin_router = APIRouter(prefix="/api/admin/courses", tags=["🛡️ Admin"])


# ─── List ───
@admin_router.get("/pending", response_model=List[CourseResponse])
def pending_courses(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    courses = db.query(Course).filter(Course.status == CourseStatus.pending).all()
    return [_enrich(c) for c in courses]


@admin_router.get("/all", response_model=List[CourseResponse])
def all_courses(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    courses = db.query(Course).all()
    return [_enrich(c) for c in courses]


# ─── Approve / Reject ───
@admin_router.post("/{course_id}/approve", response_model=CourseResponse)
def approve_course(
    course_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(404, "Course not found")
    course.status = CourseStatus.published
    db.commit()
    db.refresh(course)
    return _enrich(course)


@admin_router.post("/{course_id}/reject", response_model=CourseResponse)
def reject_course(
    course_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(404, "Course not found")
    course.status = CourseStatus.rejected
    db.commit()
    db.refresh(course)
    return _enrich(course)


# ─── Delete Any ───
@admin_router.delete("/{course_id}", status_code=204)
def admin_delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(404, "Course not found")
    db.delete(course)
    db.commit()


# ─── ADMIN: Add Module (emergency override, any course) ───
@admin_router.post(
    "/{course_id}/modules",
    response_model=ModuleResponse,
    status_code=201,
)
def admin_add_module(
    course_id: int,
    payload: ModuleCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Admin: add module to any course (emergency override)."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(404, "Course not found")

    module = Module(course_id=course_id, **payload.model_dump())
    db.add(module)
    db.commit()
    db.refresh(module)
    return module


# ─── ADMIN: Add Lesson (emergency override, any module) ───
@admin_router.post(
    "/modules/{module_id}/lessons",
    response_model=LessonResponse,
    status_code=201,
)
def admin_add_lesson(
    module_id: int,
    payload: LessonCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Admin: add lesson to any module (emergency override)."""
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(404, "Module not found")

    lesson = Lesson(module_id=module_id, **payload.model_dump())
    db.add(lesson)
    module.course.lessons_count = (module.course.lessons_count or 0) + 1
    db.commit()
    db.refresh(lesson)
    return lesson
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.course import CourseStatus, CourseLevel

class LessonCreate(BaseModel):
    title: str
    type: str = "video"
    content: Optional[str] = None
    resource_url: Optional[str] = None
    duration_minutes: int = 0
    order_index: int = 0
    is_preview: bool = False

class LessonResponse(LessonCreate):
    id: int
    class Config:
        from_attributes = True

class ModuleCreate(BaseModel):
    title: str
    description: Optional[str] = None
    order_index: int = 0

class ModuleResponse(ModuleCreate):
    id: int
    lessons: List[LessonResponse] = []
    class Config:
        from_attributes = True

class CourseCreate(BaseModel):
    title: str = Field(..., min_length=3)
    slug: str
    description: Optional[str] = None
    category: Optional[str] = None
    level: CourseLevel = CourseLevel.beginner
    price: float = 0
    is_free: bool = True
    duration_hours: int = 0
    thumbnail: Optional[str] = None

class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    level: Optional[CourseLevel] = None
    price: Optional[float] = None
    is_free: Optional[bool] = None
    thumbnail: Optional[str] = None
    status: Optional[CourseStatus] = None

class CourseResponse(BaseModel):
    id: int
    title: str
    slug: str
    description: Optional[str]
    category: Optional[str]
    level: CourseLevel
    status: CourseStatus
    price: float
    is_free: bool
    duration_hours: int
    thumbnail: Optional[str]
    rating: float
    students_count: int
    lessons_count: int
    instructor_id: int
    instructor_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class CourseDetailResponse(CourseResponse):
    modules: List[ModuleResponse] = []
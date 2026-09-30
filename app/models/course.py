from sqlalchemy import Column, BigInteger, String, Text, Enum, Boolean, DateTime, DECIMAL, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class CourseStatus(str, enum.Enum):
    draft = "draft"
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    published = "published"
    archived = "archived"

class CourseLevel(str, enum.Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"

class Course(Base):
    __tablename__ = "courses"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    instructor_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(Text)
    category = Column(String(100))
    level = Column(Enum(CourseLevel), default=CourseLevel.beginner)
    status = Column(Enum(CourseStatus), default=CourseStatus.pending)
    price = Column(DECIMAL(10, 2), default=0)
    is_free = Column(Boolean, default=True)
    duration_hours = Column(Integer, default=0)
    lessons_count = Column(Integer, default=0)
    thumbnail = Column(String(500))
    rating = Column(DECIMAL(3, 2), default=0)
    students_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    instructor = relationship("User", back_populates="courses", foreign_keys=[instructor_id])
    modules = relationship("Module", back_populates="course", cascade="all, delete-orphan")
    enrollments = relationship("Enrollment", back_populates="course")
    assignments = relationship("Assignment", back_populates="course", cascade="all, delete-orphan")
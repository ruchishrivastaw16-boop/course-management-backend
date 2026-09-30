from sqlalchemy import Column, BigInteger, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    course_id = Column(BigInteger, ForeignKey("courses.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    max_score = Column(Integer, default=100)
    due_date = Column(DateTime, nullable=True)
    attachment_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    course = relationship("Course", back_populates="assignments")
    submissions = relationship("Submission", back_populates="assignment", cascade="all, delete-orphan")
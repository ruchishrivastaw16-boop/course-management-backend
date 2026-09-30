from sqlalchemy import Column, BigInteger, Text, DECIMAL, Enum, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class SubmissionStatus(str, enum.Enum):
    submitted = "submitted"
    graded = "graded"
    late = "late"
    resubmit = "resubmit"

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    assignment_id = Column(BigInteger, ForeignKey("assignments.id"), nullable=False)
    student_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    file_url = Column(String(500), nullable=True)
    text_answer = Column(Text, nullable=True)
    grade = Column(DECIMAL(5, 2), nullable=True)
    feedback = Column(Text, nullable=True)
    status = Column(Enum(SubmissionStatus), default=SubmissionStatus.submitted)
    submitted_at = Column(DateTime, server_default=func.now())
    graded_at = Column(DateTime, nullable=True)

    assignment = relationship("Assignment", back_populates="submissions")
    student = relationship("User", back_populates="submissions")
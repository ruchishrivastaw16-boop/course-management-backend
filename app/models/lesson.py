from sqlalchemy import Column, BigInteger, String, Text, Integer, Enum, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class LessonType(str, enum.Enum):
    video = "video"
    pdf = "pdf"
    text = "text"
    quiz = "quiz"

class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    module_id = Column(BigInteger, ForeignKey("modules.id"), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text)
    type = Column(Enum(LessonType), default=LessonType.video)
    resource_url = Column(String(500))
    duration_minutes = Column(Integer, default=0)
    order_index = Column(Integer, default=0)
    is_preview = Column(Boolean, default=False)

    module = relationship("Module", back_populates="lessons")
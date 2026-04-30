"""Subject model — the top-level workspace entity."""
import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Integer, Date, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=True)
    color: Mapped[str] = mapped_column(String(7), default="#7c5cff")  # hex color
    icon: Mapped[str] = mapped_column(String(50), default="book")
    credits: Mapped[int] = mapped_column(Integer, default=3)  # 1-6, higher = more important
    exam_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    units = relationship("SyllabusUnit", back_populates="subject", cascade="all, delete-orphan")
    uploads = relationship("Upload", back_populates="subject", cascade="all, delete-orphan")
    marking_schemes = relationship("MarkingScheme", back_populates="subject", cascade="all, delete-orphan")
    deadlines = relationship("Deadline", back_populates="subject", cascade="all, delete-orphan")
    quiz_sessions = relationship("QuizSession", back_populates="subject", cascade="all, delete-orphan")
    study_plans = relationship("StudyPlan", back_populates="subject", cascade="all, delete-orphan")

"""Study plan model — daily scheduled topic blocks."""
import uuid
from datetime import date, datetime

from sqlalchemy import String, Float, Date, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class StudyPlan(Base):
    __tablename__ = "study_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subject_id: Mapped[str] = mapped_column(String(36), ForeignKey("subjects.id"), nullable=False)
    plan_date: Mapped[date] = mapped_column(Date, nullable=False)
    daily_schedule: Mapped[str] = mapped_column(Text, nullable=True)  # JSON: [{topic_id, duration_min, priority}]
    completion_pct: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    subject = relationship("Subject", back_populates="study_plans")

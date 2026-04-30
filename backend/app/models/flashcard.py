"""Flashcard model with Leitner spaced repetition fields."""
import uuid
from datetime import datetime, timedelta

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Flashcard(Base):
    __tablename__ = "flashcards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    topic_id: Mapped[str] = mapped_column(String(36), ForeignKey("syllabus_topics.id"), nullable=False)
    front: Mapped[str] = mapped_column(Text, nullable=False)
    back: Mapped[str] = mapped_column(Text, nullable=False)
    leitner_box: Mapped[int] = mapped_column(Integer, default=1)  # 1-5
    next_review: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    topic = relationship("SyllabusTopic", back_populates="flashcards")

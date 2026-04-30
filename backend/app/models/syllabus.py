"""Syllabus models — units and topics parsed from syllabus documents."""
import uuid
from typing import Optional

from sqlalchemy import String, Integer, Float, Boolean, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SyllabusUnit(Base):
    __tablename__ = "syllabus_units"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subject_id: Mapped[str] = mapped_column(String(36), ForeignKey("subjects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    unit_number: Mapped[int] = mapped_column(Integer, nullable=False)
    coverage_pct: Mapped[float] = mapped_column(Float, default=0.0)

    subject = relationship("Subject", back_populates="units")
    topics = relationship("SyllabusTopic", back_populates="unit", cascade="all, delete-orphan")


class SyllabusTopic(Base):
    __tablename__ = "syllabus_topics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    unit_id: Mapped[str] = mapped_column(String(36), ForeignKey("syllabus_units.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    topic_order: Mapped[int] = mapped_column(Integer, default=0)
    is_covered: Mapped[bool] = mapped_column(Boolean, default=False)
    importance_score: Mapped[float] = mapped_column(Float, default=0.5)
    pyq_frequency: Mapped[float] = mapped_column(Float, default=0.0)
    quiz_accuracy: Mapped[float] = mapped_column(Float, default=0.0)
    content_cache: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Pre-processed content for fast generation

    unit = relationship("SyllabusUnit", back_populates="topics")
    content_chunks = relationship("ContentChunk", back_populates="topic")
    flashcards = relationship("Flashcard", back_populates="topic", cascade="all, delete-orphan")
    pyq_patterns = relationship("PYQPattern", back_populates="topic", cascade="all, delete-orphan")

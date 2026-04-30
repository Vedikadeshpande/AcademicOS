"""Upload and ContentChunk models for file processing pipeline."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Upload(Base):
    __tablename__ = "uploads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subject_id: Mapped[str] = mapped_column(String(36), ForeignKey("subjects.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)  # pdf, ppt, pyq
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="processing")  # processing, done, error
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    subject = relationship("Subject", back_populates="uploads")
    chunks = relationship("ContentChunk", back_populates="upload", cascade="all, delete-orphan")


class ContentChunk(Base):
    __tablename__ = "content_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    upload_id: Mapped[str] = mapped_column(String(36), ForeignKey("uploads.id"), nullable=False)
    topic_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("syllabus_topics.id"), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_page: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    embedding_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # FAISS vector ID

    upload = relationship("Upload", back_populates="chunks")
    topic = relationship("SyllabusTopic", back_populates="content_chunks")


class MarkingScheme(Base):
    __tablename__ = "marking_schemes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subject_id: Mapped[str] = mapped_column(String(36), ForeignKey("subjects.id"), nullable=False)
    marks: Mapped[int] = mapped_column(Integer, nullable=False)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False)
    question_type: Mapped[str] = mapped_column(String(20), nullable=False)  # short, long, mcq

    subject = relationship("Subject", back_populates="marking_schemes")


class Deadline(Base):
    __tablename__ = "deadlines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subject_id: Mapped[str] = mapped_column(String(36), ForeignKey("subjects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    deadline_type: Mapped[str] = mapped_column(String(20), nullable=False)  # exam, assignment, quiz
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_completed: Mapped[bool] = mapped_column(default=False)

    subject = relationship("Subject", back_populates="deadlines")


class PYQPattern(Base):
    __tablename__ = "pyq_patterns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    topic_id: Mapped[str] = mapped_column(String(36), ForeignKey("syllabus_topics.id"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=True)
    frequency: Mapped[int] = mapped_column(Integer, default=0)
    recurrence_score: Mapped[float] = mapped_column(Float, default=0.0)
    keywords: Mapped[str] = mapped_column(Text, nullable=True)

    topic = relationship("SyllabusTopic", back_populates="pyq_patterns")

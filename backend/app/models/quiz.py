"""Quiz models — sessions, questions, and answers."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Float, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subject_id: Mapped[str] = mapped_column(String(36), ForeignKey("subjects.id"), nullable=False)
    quiz_type: Mapped[str] = mapped_column(String(20), nullable=False)  # topic, mock, pyq_based
    total_questions: Mapped[int] = mapped_column(Integer, default=0)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0)
    score_pct: Mapped[float] = mapped_column(Float, default=0.0)
    taken_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    subject = relationship("Subject", back_populates="quiz_sessions")
    questions = relationship("QuizQuestion", back_populates="session", cascade="all, delete-orphan")


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("quiz_sessions.id"), nullable=False)
    topic_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("syllabus_topics.id"), nullable=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(20), nullable=False)  # mcq, short, long
    marks: Mapped[int] = mapped_column(Integer, default=1)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=True)
    options: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string for MCQ options

    session = relationship("QuizSession", back_populates="questions")
    answers = relationship("QuizAnswer", back_populates="question", cascade="all, delete-orphan")


class QuizAnswer(Base):
    __tablename__ = "quiz_answers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id: Mapped[str] = mapped_column(String(36), ForeignKey("quiz_questions.id"), nullable=False)
    user_answer: Mapped[str] = mapped_column(Text, nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    question = relationship("QuizQuestion", back_populates="answers")


class QuestionPool(Base):
    """Pre-generated questions stored after file upload for instant serving."""
    __tablename__ = "question_pool"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    topic_id: Mapped[str] = mapped_column(String(36), ForeignKey("syllabus_topics.id"), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[str] = mapped_column(Text, nullable=False)  # JSON: {"A":"..","B":"..","C":"..","D":".."}
    correct_answer: Mapped[str] = mapped_column(String(5), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=True)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


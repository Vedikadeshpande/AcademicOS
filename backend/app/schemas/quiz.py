"""Pydantic schemas for Quiz API."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class QuizStartRequest(BaseModel):
    subject_id: str
    quiz_type: str = Field("topic", pattern=r"^(topic|short|mock|pyq_based)$")
    topic_ids: list[str] = []
    num_questions: int = Field(10, ge=1, le=50)
    difficulty: str = Field("medium", pattern=r"^(easy|medium|hard)$")


class ExamPaperRequest(BaseModel):
    subject_id: str
    exam_type: str = Field("end_sem", pattern=r"^(mid_sem|end_sem)$")


class QuizQuestionResponse(BaseModel):
    id: str
    question_text: str
    question_type: str
    marks: int
    options: Optional[str] = None  # JSON for MCQ
    topic_title: Optional[str] = None

    class Config:
        from_attributes = True


class QuizSubmitRequest(BaseModel):
    answers: list["AnswerSubmit"]


class AnswerSubmit(BaseModel):
    question_id: str
    user_answer: str


class QuizResultResponse(BaseModel):
    session_id: str
    total_questions: int
    correct_answers: int
    score_pct: float
    results: list["QuestionResult"] = []


class QuestionResult(BaseModel):
    question_id: str
    question_text: str
    user_answer: str
    correct_answer: Optional[str]
    is_correct: bool
    awarded_marks: Optional[int] = None
    max_marks: Optional[int] = None
    feedback: Optional[str] = None
    good_points: list[str] = []
    missing_points: list[str] = []
    mistakes: list[str] = []
    suggestions: list[str] = []


class AnalyticsResponse(BaseModel):
    coverage_pct: float
    avg_quiz_accuracy: float
    readiness_pct: float
    risk_level: str
    days_until_exam: Optional[int]
    total_quizzes_taken: int
    flashcard_mastery_pct: float
    topic_breakdown: list["TopicAnalytics"] = []


class TopicAnalytics(BaseModel):
    topic_id: str
    topic_title: str
    is_covered: bool
    quiz_accuracy: float
    pyq_frequency: float

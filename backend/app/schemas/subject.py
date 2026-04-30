"""Pydantic schemas for Subject API."""
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional


class SubjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    code: Optional[str] = Field(None, max_length=50)
    color: str = Field("#7c5cff", pattern=r"^#[0-9a-fA-F]{6}$")
    icon: str = Field("book", max_length=50)
    credits: int = Field(3, ge=1, le=6)
    exam_date: Optional[date] = None


class SubjectUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    code: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    icon: Optional[str] = Field(None, max_length=50)
    credits: Optional[int] = Field(None, ge=1, le=6)
    exam_date: Optional[date] = None


class SubjectResponse(BaseModel):
    id: str
    name: str
    code: Optional[str]
    color: str
    icon: str
    credits: int = 3
    exam_date: Optional[date]
    created_at: datetime
    total_units: int = 0
    total_topics: int = 0
    coverage_pct: float = 0.0
    upload_count: int = 0

    class Config:
        from_attributes = True


class MarkingSchemeCreate(BaseModel):
    marks: int = Field(..., gt=0)
    question_count: int = Field(..., gt=0)
    question_type: str = Field(..., pattern=r"^(short|long|mcq)$")


class MarkingSchemeResponse(BaseModel):
    id: str
    marks: int
    question_count: int
    question_type: str

    class Config:
        from_attributes = True


class DeadlineCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    deadline_type: str = Field(..., pattern=r"^(exam|assignment|quiz)$")
    due_date: datetime


class DeadlineResponse(BaseModel):
    id: str
    title: str
    deadline_type: str
    due_date: datetime
    is_completed: bool

    class Config:
        from_attributes = True


class DeadlineWithSubjectResponse(BaseModel):
    id: str
    title: str
    deadline_type: str
    due_date: datetime
    is_completed: bool
    subject_id: str
    subject_name: str
    subject_color: str

    class Config:
        from_attributes = True


"""Pydantic schemas for Syllabus API."""
from pydantic import BaseModel, Field
from typing import Optional


class SyllabusUnitCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    unit_number: int = Field(..., ge=1)


class SyllabusUnitResponse(BaseModel):
    id: str
    title: str
    unit_number: int
    coverage_pct: float
    topics: list["SyllabusTopicResponse"] = []

    class Config:
        from_attributes = True


class SyllabusTopicCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    topic_order: int = Field(0, ge=0)


class SyllabusTopicResponse(BaseModel):
    id: str
    title: str
    topic_order: int
    is_covered: bool
    importance_score: float
    pyq_frequency: float
    quiz_accuracy: float

    class Config:
        from_attributes = True


class SyllabusParseRequest(BaseModel):
    """Request to parse raw syllabus text into units and topics."""
    raw_text: Optional[str] = None
    upload_id: Optional[str] = None


class CoverageResponse(BaseModel):
    total_topics: int
    covered_topics: int
    coverage_pct: float
    uncovered_topics: list[str] = []

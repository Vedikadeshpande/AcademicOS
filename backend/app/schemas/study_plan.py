"""Pydantic schemas for Study Plan API."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class StudyPlanGenerateRequest(BaseModel):
    daily_hours: float = Field(3.0, ge=0.5, le=16.0)
    subject_ids: list[str] = []  # Empty = all subjects with exam dates


class StudyTaskItem(BaseModel):
    topic_id: str
    topic_title: str
    subject_id: str
    subject_name: str
    subject_color: str
    duration_min: int
    priority: float
    is_completed: bool = False


class StudyDayPlan(BaseModel):
    plan_id: str
    plan_date: date
    tasks: list[StudyTaskItem] = []
    completion_pct: float = 0.0


class StudyPlanResponse(BaseModel):
    days: list[StudyDayPlan] = []
    total_days: int = 0
    daily_hours: float = 3.0

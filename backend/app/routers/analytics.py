"""Analytics endpoint — readiness, risk, topic breakdown."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date

from app.database import get_db
from app.models.subject import Subject
from app.models.syllabus import SyllabusUnit, SyllabusTopic
from app.models.quiz import QuizSession
from app.models.flashcard import Flashcard
from app.schemas.quiz import AnalyticsResponse, TopicAnalytics

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/{subject_id}", response_model=AnalyticsResponse)
async def get_analytics(subject_id: str, db: AsyncSession = Depends(get_db)):
    # Verify subject
    result = await db.execute(select(Subject).where(Subject.id == subject_id))
    subject = result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    # Coverage
    topics_result = await db.execute(
        select(SyllabusTopic).join(SyllabusUnit).where(SyllabusUnit.subject_id == subject_id)
    )
    topics = topics_result.scalars().all()
    total_topics = len(topics)
    covered = sum(1 for t in topics if t.is_covered)
    coverage_pct = (covered / total_topics * 100) if total_topics > 0 else 0.0

    # Quiz accuracy
    quiz_result = await db.execute(
        select(QuizSession).where(QuizSession.subject_id == subject_id)
    )
    quizzes = quiz_result.scalars().all()
    total_quizzes = len(quizzes)
    avg_accuracy = (sum(q.score_pct for q in quizzes) / total_quizzes) if total_quizzes > 0 else 0.0

    # Days until exam
    days_left = None
    if subject.exam_date:
        days_left = (subject.exam_date - date.today()).days
        days_left = max(days_left, 0)

    # Time comfort score (0-100)
    time_score = min((days_left or 0) / 30.0, 1.0) * 100

    # Readiness
    readiness = coverage_pct * 0.3 + avg_accuracy * 0.4 + time_score * 0.3

    # Risk level
    if readiness >= 70:
        risk = "Low"
    elif readiness >= 40:
        risk = "Medium"
    else:
        risk = "High"

    # Flashcard mastery
    fc_result = await db.execute(
        select(Flashcard).join(SyllabusTopic).join(SyllabusUnit).where(SyllabusUnit.subject_id == subject_id)
    )
    flashcards = fc_result.scalars().all()
    total_fc = len(flashcards)
    mastered = sum(1 for f in flashcards if f.leitner_box >= 4)
    fc_mastery = (mastered / total_fc * 100) if total_fc > 0 else 0.0

    # Topic breakdown
    topic_breakdown = [
        TopicAnalytics(
            topic_id=t.id,
            topic_title=t.title,
            is_covered=t.is_covered,
            quiz_accuracy=t.quiz_accuracy,
            pyq_frequency=t.pyq_frequency,
        )
        for t in topics
    ]

    return AnalyticsResponse(
        coverage_pct=round(coverage_pct, 1),
        avg_quiz_accuracy=round(avg_accuracy, 1),
        readiness_pct=round(readiness, 1),
        risk_level=risk,
        days_until_exam=days_left,
        total_quizzes_taken=total_quizzes,
        flashcard_mastery_pct=round(fc_mastery, 1),
        topic_breakdown=topic_breakdown,
    )

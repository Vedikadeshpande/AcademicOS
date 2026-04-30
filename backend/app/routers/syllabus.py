"""Syllabus management endpoints — parse, view, manage units/topics."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.subject import Subject
from app.models.syllabus import SyllabusUnit, SyllabusTopic
from app.schemas.syllabus import (
    SyllabusUnitCreate, SyllabusUnitResponse,
    SyllabusTopicCreate, SyllabusTopicResponse,
    SyllabusParseRequest, CoverageResponse,
)

router = APIRouter(prefix="/api/syllabus", tags=["syllabus"])


@router.get("/{subject_id}/units", response_model=list[SyllabusUnitResponse])
async def list_units(subject_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SyllabusUnit)
        .where(SyllabusUnit.subject_id == subject_id)
        .options(selectinload(SyllabusUnit.topics))
        .order_by(SyllabusUnit.unit_number)
    )
    units = result.scalars().all()
    return [SyllabusUnitResponse.model_validate(u) for u in units]


@router.post("/{subject_id}/units", response_model=SyllabusUnitResponse, status_code=201)
async def create_unit(
    subject_id: str, data: SyllabusUnitCreate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Subject).where(Subject.id == subject_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Subject not found")

    unit = SyllabusUnit(subject_id=subject_id, **data.model_dump())
    db.add(unit)
    await db.commit()
    await db.refresh(unit)
    return SyllabusUnitResponse(
        id=unit.id, title=unit.title, unit_number=unit.unit_number,
        coverage_pct=unit.coverage_pct, topics=[],
    )


@router.post("/{subject_id}/units/{unit_id}/topics", response_model=SyllabusTopicResponse, status_code=201)
async def create_topic(
    subject_id: str, unit_id: str, data: SyllabusTopicCreate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SyllabusUnit).where(SyllabusUnit.id == unit_id, SyllabusUnit.subject_id == subject_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Unit not found")

    topic = SyllabusTopic(unit_id=unit_id, **data.model_dump())
    db.add(topic)
    await db.commit()
    await db.refresh(topic)
    return SyllabusTopicResponse.model_validate(topic)


@router.post("/{subject_id}/parse", response_model=list[SyllabusUnitResponse])
async def parse_syllabus(
    subject_id: str, data: SyllabusParseRequest, db: AsyncSession = Depends(get_db)
):
    """Parse raw syllabus text or an uploaded file into structured units/topics."""
    from app.services.syllabus_parser import parse_syllabus_text

    result = await db.execute(select(Subject).where(Subject.id == subject_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Subject not found")

    raw_text = data.raw_text
    if not raw_text and data.upload_id:
        from app.services.file_processor import extract_text_from_upload
        raw_text = await extract_text_from_upload(data.upload_id, db)

    if not raw_text:
        raise HTTPException(status_code=400, detail="Provide raw_text or upload_id")

    parsed = parse_syllabus_text(raw_text)

    # Store parsed units and topics
    created_units = []
    for unit_data in parsed:
        unit = SyllabusUnit(
            subject_id=subject_id,
            title=unit_data["title"],
            unit_number=unit_data["unit_number"],
        )
        db.add(unit)
        await db.flush()

        topics = []
        for i, topic_title in enumerate(unit_data.get("topics", [])):
            topic = SyllabusTopic(unit_id=unit.id, title=topic_title, topic_order=i)
            db.add(topic)
            topics.append(topic)

        await db.flush()
        created_units.append(SyllabusUnitResponse(
            id=unit.id, title=unit.title, unit_number=unit.unit_number,
            coverage_pct=0.0,
            topics=[SyllabusTopicResponse.model_validate(t) for t in topics],
        ))

    await db.commit()
    return created_units


@router.get("/{subject_id}/coverage", response_model=CoverageResponse)
async def get_coverage(subject_id: str, db: AsyncSession = Depends(get_db)):
    """Get coverage analysis for a subject."""
    result = await db.execute(
        select(SyllabusTopic)
        .join(SyllabusUnit)
        .where(SyllabusUnit.subject_id == subject_id)
    )
    topics = result.scalars().all()

    total = len(topics)
    covered = sum(1 for t in topics if t.is_covered)
    uncovered = [t.title for t in topics if not t.is_covered]

    return CoverageResponse(
        total_topics=total,
        covered_topics=covered,
        coverage_pct=round((covered / total * 100) if total > 0 else 0.0, 1),
        uncovered_topics=uncovered,
    )


@router.patch("/topics/{topic_id}/toggle-covered")
async def toggle_topic_covered(topic_id: str, db: AsyncSession = Depends(get_db)):
    """Toggle a topic's is_covered status (manual marking)."""
    result = await db.execute(select(SyllabusTopic).where(SyllabusTopic.id == topic_id))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    topic.is_covered = not topic.is_covered
    await db.flush()

    # Recalculate unit coverage
    unit_result = await db.execute(
        select(SyllabusTopic).where(SyllabusTopic.unit_id == topic.unit_id)
    )
    unit_topics = unit_result.scalars().all()
    total = len(unit_topics)
    covered = sum(1 for t in unit_topics if t.is_covered)

    unit = await db.execute(select(SyllabusUnit).where(SyllabusUnit.id == topic.unit_id))
    unit_obj = unit.scalar_one()
    unit_obj.coverage_pct = round((covered / total * 100) if total > 0 else 0.0, 1)

    await db.commit()
    return {"topic_id": topic_id, "is_covered": topic.is_covered, "unit_coverage_pct": unit_obj.coverage_pct}


@router.post("/{subject_id}/recalculate-coverage")
async def recalculate_coverage(subject_id: str, db: AsyncSession = Depends(get_db)):
    """Auto-detect topic coverage from flashcard + quiz activity.
    A topic is considered covered if:
      1) It has at least 1 flashcard generated, AND
      2) It has at least 2 quiz questions answered with ≥60% accuracy
    """
    from app.models.flashcard import Flashcard
    from app.models.quiz import QuizQuestion, QuizAnswer

    topics_result = await db.execute(
        select(SyllabusTopic).join(SyllabusUnit).where(SyllabusUnit.subject_id == subject_id)
    )
    topics = topics_result.scalars().all()

    updated = 0
    for topic in topics:
        if topic.is_covered:
            continue  # Don't un-cover manually marked topics

        # Check flashcards
        fc_result = await db.execute(
            select(func.count(Flashcard.id)).where(Flashcard.topic_id == topic.id)
        )
        fc_count = fc_result.scalar() or 0

        # Check quiz accuracy
        q_result = await db.execute(
            select(QuizQuestion).where(QuizQuestion.topic_id == topic.id)
        )
        questions = q_result.scalars().all()
        q_ids = [q.id for q in questions]

        quiz_ok = False
        if len(q_ids) >= 2:
            ans_result = await db.execute(
                select(QuizAnswer).where(QuizAnswer.question_id.in_(q_ids))
            )
            answers = ans_result.scalars().all()
            if answers:
                correct = sum(1 for a in answers if a.is_correct)
                accuracy = correct / len(answers)
                quiz_ok = accuracy >= 0.6

        if fc_count >= 1 and quiz_ok:
            topic.is_covered = True
            updated += 1

    # Recalculate unit coverages
    units_result = await db.execute(
        select(SyllabusUnit).where(SyllabusUnit.subject_id == subject_id)
        .options(selectinload(SyllabusUnit.topics))
    )
    units = units_result.scalars().all()
    for unit in units:
        total = len(unit.topics)
        covered = sum(1 for t in unit.topics if t.is_covered)
        unit.coverage_pct = round((covered / total * 100) if total > 0 else 0.0, 1)

    await db.commit()
    return {"updated_topics": updated}


"""Subject CRUD endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.database import get_db
from app.models.subject import Subject
from app.models.syllabus import SyllabusUnit, SyllabusTopic
from app.models.upload import Upload, MarkingScheme, Deadline
from app.schemas.subject import (
    SubjectCreate, SubjectUpdate, SubjectResponse,
    MarkingSchemeCreate, MarkingSchemeResponse,
    DeadlineCreate, DeadlineResponse,
)

router = APIRouter(prefix="/api/subjects", tags=["subjects"])


@router.get("/", response_model=list[SubjectResponse])
async def list_subjects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Subject).order_by(Subject.created_at.desc()))
    subjects = result.scalars().all()

    responses = []
    for s in subjects:
        # Count units and topics
        units_result = await db.execute(
            select(func.count(SyllabusUnit.id)).where(SyllabusUnit.subject_id == s.id)
        )
        total_units = units_result.scalar() or 0

        topics_result = await db.execute(
            select(func.count(SyllabusTopic.id))
            .join(SyllabusUnit)
            .where(SyllabusUnit.subject_id == s.id)
        )
        total_topics = topics_result.scalar() or 0

        covered_result = await db.execute(
            select(func.count(SyllabusTopic.id))
            .join(SyllabusUnit)
            .where(SyllabusUnit.subject_id == s.id, SyllabusTopic.is_covered == True)
        )
        covered = covered_result.scalar() or 0

        uploads_result = await db.execute(
            select(func.count(Upload.id)).where(Upload.subject_id == s.id)
        )
        upload_count = uploads_result.scalar() or 0

        coverage_pct = (covered / total_topics * 100) if total_topics > 0 else 0.0

        responses.append(SubjectResponse(
            id=s.id, name=s.name, code=s.code, color=s.color,
            icon=s.icon, credits=s.credits, exam_date=s.exam_date, created_at=s.created_at,
            total_units=total_units, total_topics=total_topics,
            coverage_pct=round(coverage_pct, 1), upload_count=upload_count,
        ))

    return responses


@router.post("/", response_model=SubjectResponse, status_code=201)
async def create_subject(data: SubjectCreate, db: AsyncSession = Depends(get_db)):
    try:
        subject = Subject(**data.model_dump())
        db.add(subject)
        await db.commit()
        await db.refresh(subject)
        print(f"[Subject] Created subject: {subject.id} - {subject.name}")
        return SubjectResponse(
            id=subject.id, name=subject.name, code=subject.code,
            color=subject.color, icon=subject.icon, credits=subject.credits,
            exam_date=subject.exam_date, created_at=subject.created_at,
        )
    except Exception as e:
        print(f"[Subject] Error creating subject: {e}")
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/deadlines/all", response_model=list["DeadlineWithSubjectResponse"])
async def list_all_deadlines(db: AsyncSession = Depends(get_db)):
    """Get all deadlines across all subjects, sorted by due date."""
    from app.schemas.subject import DeadlineWithSubjectResponse
    result = await db.execute(
        select(Deadline).order_by(Deadline.due_date.asc())
    )
    deadlines = result.scalars().all()

    responses = []
    for d in deadlines:
        subj_result = await db.execute(select(Subject).where(Subject.id == d.subject_id))
        subj = subj_result.scalar_one_or_none()
        responses.append(DeadlineWithSubjectResponse(
            id=d.id, title=d.title, deadline_type=d.deadline_type,
            due_date=d.due_date, is_completed=d.is_completed,
            subject_id=d.subject_id,
            subject_name=subj.name if subj else "Unknown",
            subject_color=subj.color if subj else "#7c5cff",
        ))
    return responses


@router.get("/{subject_id}", response_model=SubjectResponse)
async def get_subject(subject_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Subject).where(Subject.id == subject_id))
    subject = result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    # Get counts
    topics_result = await db.execute(
        select(func.count(SyllabusTopic.id))
        .join(SyllabusUnit)
        .where(SyllabusUnit.subject_id == subject_id)
    )
    total_topics = topics_result.scalar() or 0

    covered_result = await db.execute(
        select(func.count(SyllabusTopic.id))
        .join(SyllabusUnit)
        .where(SyllabusUnit.subject_id == subject_id, SyllabusTopic.is_covered == True)
    )
    covered = covered_result.scalar() or 0

    units_result = await db.execute(
        select(func.count(SyllabusUnit.id)).where(SyllabusUnit.subject_id == subject_id)
    )
    total_units = units_result.scalar() or 0

    uploads_result = await db.execute(
        select(func.count(Upload.id)).where(Upload.subject_id == subject_id)
    )
    upload_count = uploads_result.scalar() or 0

    coverage_pct = (covered / total_topics * 100) if total_topics > 0 else 0.0

    return SubjectResponse(
        id=subject.id, name=subject.name, code=subject.code,
        color=subject.color, icon=subject.icon, credits=subject.credits,
        exam_date=subject.exam_date, created_at=subject.created_at, total_units=total_units,
        total_topics=total_topics, coverage_pct=round(coverage_pct, 1),
        upload_count=upload_count,
    )


@router.patch("/{subject_id}", response_model=SubjectResponse)
async def update_subject(subject_id: str, data: SubjectUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Subject).where(Subject.id == subject_id))
    subject = result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(subject, key, value)

    await db.commit()
    await db.refresh(subject)
    return SubjectResponse(
        id=subject.id, name=subject.name, code=subject.code,
        color=subject.color, icon=subject.icon, credits=subject.credits,
        exam_date=subject.exam_date, created_at=subject.created_at,
    )


@router.delete("/{subject_id}", status_code=204)
async def delete_subject(subject_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Subject).where(Subject.id == subject_id))
    subject = result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    await db.delete(subject)
    await db.commit()


# ── Marking Schemes ──

@router.post("/{subject_id}/marking-schemes", response_model=MarkingSchemeResponse, status_code=201)
async def create_marking_scheme(
    subject_id: str, data: MarkingSchemeCreate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Subject).where(Subject.id == subject_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Subject not found")

    scheme = MarkingScheme(subject_id=subject_id, **data.model_dump())
    db.add(scheme)
    await db.commit()
    await db.refresh(scheme)
    return MarkingSchemeResponse.model_validate(scheme)


@router.get("/{subject_id}/marking-schemes", response_model=list[MarkingSchemeResponse])
async def list_marking_schemes(subject_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MarkingScheme).where(MarkingScheme.subject_id == subject_id)
    )
    return [MarkingSchemeResponse.model_validate(s) for s in result.scalars().all()]


@router.delete("/{subject_id}/marking-schemes/{scheme_id}", status_code=204)
async def delete_marking_scheme(subject_id: str, scheme_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MarkingScheme).where(MarkingScheme.id == scheme_id, MarkingScheme.subject_id == subject_id)
    )
    scheme = result.scalar_one_or_none()
    if not scheme:
        raise HTTPException(status_code=404, detail="Marking scheme not found")
    await db.delete(scheme)
    await db.commit()


# ── Deadlines ──

@router.post("/{subject_id}/deadlines", response_model=DeadlineResponse, status_code=201)
async def create_deadline(
    subject_id: str, data: DeadlineCreate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Subject).where(Subject.id == subject_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Subject not found")

    deadline = Deadline(subject_id=subject_id, **data.model_dump())
    db.add(deadline)
    await db.commit()
    await db.refresh(deadline)
    return DeadlineResponse.model_validate(deadline)




@router.get("/{subject_id}/deadlines", response_model=list[DeadlineResponse])
async def list_deadlines(subject_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Deadline)
        .where(Deadline.subject_id == subject_id)
        .order_by(Deadline.due_date.asc())
    )
    return [DeadlineResponse.model_validate(d) for d in result.scalars().all()]


@router.patch("/{subject_id}/deadlines/{deadline_id}/toggle", response_model=DeadlineResponse)
async def toggle_deadline(subject_id: str, deadline_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Deadline).where(Deadline.id == deadline_id, Deadline.subject_id == subject_id)
    )
    deadline = result.scalar_one_or_none()
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")
    deadline.is_completed = not deadline.is_completed
    await db.commit()
    return DeadlineResponse.model_validate(deadline)


@router.delete("/{subject_id}/deadlines/{deadline_id}", status_code=204)
async def delete_deadline(subject_id: str, deadline_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Deadline).where(Deadline.id == deadline_id, Deadline.subject_id == subject_id)
    )
    deadline = result.scalar_one_or_none()
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")
    await db.delete(deadline)
    await db.commit()


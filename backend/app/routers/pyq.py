"""PYQ analysis endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.subject import Subject
from app.services.pyq_analyzer import analyze_pyq

router = APIRouter(prefix="/api/pyq", tags=["pyq"])


@router.post("/analyze/{subject_id}")
async def analyze(subject_id: str, db: AsyncSession = Depends(get_db)):
    """Analyze PYQ papers for a subject."""
    result = await db.execute(select(Subject).where(Subject.id == subject_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Subject not found")

    analysis = await analyze_pyq(subject_id, db)
    return analysis

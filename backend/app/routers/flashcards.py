"""Flashcard endpoints — generate, review, and manage flashcards."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.flashcard_service import (
    generate_flashcards_for_topic,
    review_flashcard,
    get_due_flashcards,
    get_all_flashcards,
)
from app.models.syllabus import SyllabusUnit, SyllabusTopic
from sqlalchemy import select

router = APIRouter(prefix="/api/flashcards", tags=["flashcards"])


class GenerateRequest(BaseModel):
    subject_id: str
    scope: str = "topic"  # "all", "unit", "topic"
    unit_id: Optional[str] = None
    topic_id: Optional[str] = None
    count: int = 5  # per-topic count


class ReviewRequest(BaseModel):
    card_id: str
    is_correct: bool


@router.post("/generate")
async def generate_cards(req: GenerateRequest, db: AsyncSession = Depends(get_db)):
    """Generate flashcards — for entire syllabus, unit, or single topic."""

    if req.scope == "topic":
        if not req.topic_id:
            raise HTTPException(status_code=400, detail="topic_id required for topic scope")
        cards = await generate_flashcards_for_topic(req.topic_id, db, count=req.count)
        return {"generated": len(cards), "cards": cards}

    elif req.scope == "unit":
        if not req.unit_id:
            raise HTTPException(status_code=400, detail="unit_id required for unit scope")
        # Get all topics in the unit
        result = await db.execute(
            select(SyllabusTopic.id).where(SyllabusTopic.unit_id == req.unit_id)
        )
        topic_ids = [r[0] for r in result.all()]
        if not topic_ids:
            raise HTTPException(status_code=400, detail="No topics found in this unit")

        all_cards = []
        per_topic = max(1, req.count // len(topic_ids)) or 1
        for tid in topic_ids:
            cards = await generate_flashcards_for_topic(tid, db, count=per_topic)
            all_cards.extend(cards)
        return {"generated": len(all_cards), "cards": all_cards}

    elif req.scope == "all":
        # Get all topics in the subject
        result = await db.execute(
            select(SyllabusTopic.id)
            .join(SyllabusUnit)
            .where(SyllabusUnit.subject_id == req.subject_id)
        )
        topic_ids = [r[0] for r in result.all()]
        if not topic_ids:
            raise HTTPException(status_code=400, detail="No topics found. Parse your syllabus first.")

        all_cards = []
        per_topic = max(1, req.count // len(topic_ids)) or 1
        for tid in topic_ids:
            cards = await generate_flashcards_for_topic(tid, db, count=per_topic)
            all_cards.extend(cards)
        return {"generated": len(all_cards), "cards": all_cards}

    else:
        raise HTTPException(status_code=400, detail="Invalid scope. Use 'all', 'unit', or 'topic'.")


@router.post("/review")
async def review_card(req: ReviewRequest, db: AsyncSession = Depends(get_db)):
    """Review a flashcard — promotes or demotes in Leitner system."""
    result = await review_flashcard(req.card_id, req.is_correct, db)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/due/{subject_id}")
async def due_cards(subject_id: str, limit: int = 20, db: AsyncSession = Depends(get_db)):
    """Get flashcards due for review."""
    cards = await get_due_flashcards(subject_id, db, limit=limit)
    return {"count": len(cards), "cards": cards}


@router.get("/{subject_id}")
async def list_cards(subject_id: str, db: AsyncSession = Depends(get_db)):
    """Get all flashcards for a subject."""
    cards = await get_all_flashcards(subject_id, db)
    return {"count": len(cards), "cards": cards}


@router.delete("/card/{card_id}")
async def delete_card(card_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a single flashcard."""
    from app.models.flashcard import Flashcard
    card = await db.get(Flashcard, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    await db.delete(card)
    await db.commit()
    return {"status": "deleted", "id": card_id}


@router.delete("/clear/{subject_id}")
async def clear_cards(subject_id: str, db: AsyncSession = Depends(get_db)):
    """Delete all flashcards for a subject."""
    from app.models.flashcard import Flashcard
    result = await db.execute(
        select(Flashcard)
        .join(SyllabusTopic)
        .join(SyllabusUnit)
        .where(SyllabusUnit.subject_id == subject_id)
    )
    cards = result.scalars().all()
    count = len(cards)
    for card in cards:
        await db.delete(card)
    await db.commit()
    return {"status": "cleared", "deleted": count}


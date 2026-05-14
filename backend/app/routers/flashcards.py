"""Flashcard endpoints — generate, review, and manage flashcards."""

from typing import Optional
import random

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.services.flashcard_service import (
    generate_flashcards_for_topic,
    review_flashcard,
    get_due_flashcards,
    get_all_flashcards,
)
from app.models.syllabus import SyllabusUnit, SyllabusTopic

router = APIRouter(prefix="/api/flashcards", tags=["flashcards"])


# =========================
# REQUEST MODELS
# =========================

class GenerateRequest(BaseModel):
    subject_id: str
    scope: str = "topic"  # "all", "unit", "topic"
    unit_id: Optional[str] = None
    topic_id: Optional[str] = None
    count: int = 5  # total flashcards requested


class ReviewRequest(BaseModel):
    card_id: str
    is_correct: bool


# =========================
# GENERATE FLASHCARDS
# =========================

@router.post("/generate")
async def generate_cards(
    req: GenerateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Generate flashcards for topic, unit, or entire subject."""

    # ---------------- TOPIC ----------------
    if req.scope == "topic":

        if not req.topic_id:
            raise HTTPException(
                status_code=400,
                detail="topic_id required for topic scope"
            )

        cards = await generate_flashcards_for_topic(
            req.topic_id,
            db,
            count=req.count
        )

        # Retry if under-generated
        attempts = 0

        while len(cards) < req.count and attempts < 3:

            needed = req.count - len(cards)

            extra_cards = await generate_flashcards_for_topic(
                req.topic_id,
                db,
                count=needed
            )

            cards.extend(extra_cards)

            attempts += 1

        cards = cards[:req.count]

        return {
            "generated": len(cards),
            "cards": cards
        }

    # ---------------- UNIT ----------------
    elif req.scope == "unit":

        if not req.unit_id:
            raise HTTPException(
                status_code=400,
                detail="unit_id required for unit scope"
            )

        result = await db.execute(
            select(SyllabusTopic.id).where(
                SyllabusTopic.unit_id == req.unit_id
            )
        )

        topic_ids = [r[0] for r in result.all()]

        if not topic_ids:
            raise HTTPException(
                status_code=400,
                detail="No topics found in this unit"
            )

        random.shuffle(topic_ids)

        all_cards = []

        attempts = 0
        max_attempts = max(req.count * 2, len(topic_ids) * 3)

        while len(all_cards) < req.count and attempts < max_attempts:

            tid = topic_ids[attempts % len(topic_ids)]

            remaining = req.count - len(all_cards)

            batch_size = min(3, remaining)

            try:
                cards = await generate_flashcards_for_topic(
                    tid,
                    db,
                    count=batch_size
                )

                all_cards.extend(cards)

            except Exception as e:
                print(f"Flashcard generation failed for topic {tid}: {e}")

            attempts += 1

        all_cards = all_cards[:req.count]

        return {
            "generated": len(all_cards),
            "cards": all_cards
        }

    # ---------------- ALL SUBJECT ----------------
    elif req.scope == "all":

        result = await db.execute(
            select(SyllabusTopic.id)
            .join(SyllabusUnit)
            .where(SyllabusUnit.subject_id == req.subject_id)
        )

        topic_ids = [r[0] for r in result.all()]

        if not topic_ids:
            raise HTTPException(
                status_code=400,
                detail="No topics found. Parse your syllabus first."
            )

        random.shuffle(topic_ids)

        all_cards = []

        attempts = 0
        max_attempts = max(req.count * 2, len(topic_ids) * 3)

        while len(all_cards) < req.count and attempts < max_attempts:

            tid = topic_ids[attempts % len(topic_ids)]

            remaining = req.count - len(all_cards)

            batch_size = min(3, remaining)

            try:
                cards = await generate_flashcards_for_topic(
                    tid,
                    db,
                    count=batch_size
                )

                all_cards.extend(cards)

            except Exception as e:
                print(f"Flashcard generation failed for topic {tid}: {e}")

            attempts += 1

        all_cards = all_cards[:req.count]

        return {
            "generated": len(all_cards),
            "cards": all_cards
        }

    # ---------------- INVALID ----------------
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid scope. Use 'all', 'unit', or 'topic'."
        )


# =========================
# REVIEW FLASHCARD
# =========================

@router.post("/review")
async def review_card(
    req: ReviewRequest,
    db: AsyncSession = Depends(get_db)
):
    """Review a flashcard using Leitner system."""

    result = await review_flashcard(
        req.card_id,
        req.is_correct,
        db
    )

    if "error" in result:
        raise HTTPException(
            status_code=404,
            detail=result["error"]
        )

    return result


# =========================
# DUE FLASHCARDS
# =========================

@router.get("/due/{subject_id}")
async def due_cards(
    subject_id: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """Get flashcards due for review."""

    cards = await get_due_flashcards(
        subject_id,
        db,
        limit=limit
    )

    return {
        "count": len(cards),
        "cards": cards
    }


# =========================
# ALL FLASHCARDS
# =========================

@router.get("/{subject_id}")
async def list_cards(
    subject_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all flashcards for a subject."""

    cards = await get_all_flashcards(subject_id, db)

    return {
        "count": len(cards),
        "cards": cards
    }


# =========================
# DELETE SINGLE FLASHCARD
# =========================

@router.delete("/card/{card_id}")
async def delete_card(
    card_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete one flashcard."""

    from app.models.flashcard import Flashcard

    card = await db.get(Flashcard, card_id)

    if not card:
        raise HTTPException(
            status_code=404,
            detail="Flashcard not found"
        )

    await db.delete(card)
    await db.commit()

    return {
        "status": "deleted",
        "id": card_id
    }


# =========================
# CLEAR SUBJECT FLASHCARDS
# =========================

@router.delete("/clear/{subject_id}")
async def clear_cards(
    subject_id: str,
    db: AsyncSession = Depends(get_db)
):
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

    return {
        "status": "cleared",
        "deleted": count
    }

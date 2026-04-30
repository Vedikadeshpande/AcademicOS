"""
Pre-generation service — runs in background after file upload.

Generates quiz questions and flashcards using LLM + content,
stores them in QuestionPool / Flashcard tables for instant serving.

This is the NotebookLM approach: process once, serve instantly.
"""
import json
import re
import asyncio
import httpx
from typing import Optional
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.models.syllabus import SyllabusTopic, SyllabusUnit
from app.models.quiz import QuestionPool
from app.models.flashcard import Flashcard


SYSTEM_QUIZ = """You are an expert professor creating exam-quality multiple choice questions.
Rules:
- Questions must test UNDERSTANDING and COMPREHENSION, not trivial recall
- All 4 options must be plausible and similar in length
- Wrong options should be common misconceptions, not obviously wrong
- Include a clear, educational explanation
- Return ONLY a JSON array, no markdown"""

SYSTEM_FLASH = """You are an expert professor creating study flashcards.
Rules:
- Front: A clear, specific question that tests understanding
- Back: A concise but complete answer (2-4 sentences)
- Questions should cover key concepts, definitions, comparisons, and applications
- Return ONLY a JSON array, no markdown"""


async def _call_ollama(prompt: str, system: str, max_tokens: int = 1500, timeout: float = 60.0) -> Optional[str]:
    """Call Ollama with configurable timeout."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            payload = {
                "model": settings.OLLAMA_MODEL,
                "prompt": prompt,
                "system": system,
                "stream": False,
                "options": {"num_predict": max_tokens, "temperature": 0.7}
            }
            resp = await client.post(f"{settings.OLLAMA_BASE_URL}/api/generate", json=payload)
            if resp.status_code == 200:
                return resp.json().get("response", "").strip()
    except Exception as e:
        print(f"[PreGen] Ollama error: {e}")
    return None


def _parse_json_array(raw: str) -> list[dict]:
    """Robustly parse JSON array from LLM output."""
    if not raw:
        return []
    raw = raw.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    
    try:
        items = json.loads(raw)
        if isinstance(items, list):
            return items
    except json.JSONDecodeError:
        pass
    
    match = re.search(r'\[.*\]', raw, re.DOTALL)
    if match:
        try:
            items = json.loads(match.group())
            if isinstance(items, list):
                return items
        except json.JSONDecodeError:
            pass
    return []


async def pregenerate_for_subject(subject_id: str):
    """Background task: pre-generate questions & flashcards for all topics.
    
    Called after file upload completes. Takes as long as needed (background),
    so we use the full Ollama timeout.
    """
    print(f"[PreGen] Starting pre-generation for subject {subject_id}")
    
    async with async_session() as db:
        # Get all topics with their content cache
        result = await db.execute(
            select(SyllabusTopic, SyllabusUnit.title)
            .join(SyllabusUnit)
            .where(SyllabusUnit.subject_id == subject_id)
        )
        rows = result.all()
        if not rows:
            print("[PreGen] No topics found")
            return
        
        for topic, unit_title in rows:
            content = topic.content_cache or ""
            
            # Check how many pool questions exist already
            existing = await db.execute(
                select(QuestionPool)
                .where(QuestionPool.topic_id == topic.id)
            )
            existing_count = len(existing.scalars().all())
            
            if existing_count >= 10:
                print(f"[PreGen] Topic '{topic.title}' already has {existing_count} questions, skipping")
                continue
            
            questions_needed = 10 - existing_count
            
            # ── Generate quiz questions ──
            await _pregenerate_questions(topic, content, questions_needed, db)
            
            # ── Generate flashcards ──
            existing_cards = await db.execute(
                select(Flashcard.front).where(Flashcard.topic_id == topic.id)
            )
            existing_fronts = set(r[0] for r in existing_cards.all())
            
            if len(existing_fronts) < 8:
                await _pregenerate_flashcards(topic, content, 8 - len(existing_fronts), existing_fronts, db)

        await db.commit()
    
    print(f"[PreGen] Completed pre-generation for subject {subject_id}")


async def _pregenerate_questions(topic: SyllabusTopic, content: str, num: int, db: AsyncSession):
    """Generate and store MCQs for a single topic."""
    if num <= 0:
        return
    
    if content:
        prompt = f"""Generate {num} high-quality multiple-choice questions about "{topic.title}" based on this study material:

---
{content[:1200]}
---

Requirements:
- Test comprehension, not just word recall
- Each question should have 4 plausible options (A, B, C, D)
- Wrong options should be common misconceptions or related but incorrect facts
- Include a brief explanation for the correct answer

Return JSON array: [{{"question": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}, "correct": "A", "explanation": "..."}}]"""
    else:
        prompt = f"""Generate {num} high-quality multiple-choice questions about "{topic.title}".

Requirements:
- Test real understanding of the concept — how it works, when to use it, advantages/disadvantages
- Each question should have 4 plausible options
- Wrong options should be common misconceptions
- Include a brief explanation

Return JSON array: [{{"question": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}, "correct": "A", "explanation": "..."}}]"""

    raw = await _call_ollama(prompt, SYSTEM_QUIZ, max_tokens=2000)
    items = _parse_json_array(raw)
    
    stored = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        q_text = item.get("question", "").strip()
        options = item.get("options", {})
        correct = item.get("correct", "").strip().upper()
        explanation = item.get("explanation", "").strip()
        
        if not q_text or not isinstance(options, dict) or len(options) < 4:
            continue
        if correct not in options:
            correct = "A"
        
        pool_entry = QuestionPool(
            topic_id=topic.id,
            question_text=q_text,
            options=json.dumps(options),
            correct_answer=correct,
            explanation=explanation,
        )
        db.add(pool_entry)
        stored += 1
    
    if stored:
        print(f"[PreGen] Stored {stored} questions for '{topic.title}'")


async def _pregenerate_flashcards(
    topic: SyllabusTopic, content: str, num: int, existing_fronts: set, db: AsyncSession
):
    """Generate and store flashcards for a single topic."""
    if num <= 0:
        return
    
    if content:
        prompt = f"""Generate {num} study flashcards about "{topic.title}" based on this material:

---
{content[:1200]}
---

Each flashcard should:
- Front: A clear question testing understanding of a key concept
- Back: A concise but thorough answer (2-4 sentences)

Return JSON array: [{{"front": "What is...?", "back": "It is..."}}]"""
    else:
        prompt = f"""Generate {num} study flashcards about "{topic.title}".

Each flashcard should:
- Front: Test understanding of concepts, definitions, applications, or comparisons
- Back: Clear, educational answer (2-4 sentences)

Return JSON array: [{{"front": "What is...?", "back": "It is..."}}]"""

    raw = await _call_ollama(prompt, SYSTEM_FLASH, max_tokens=1500)
    items = _parse_json_array(raw)
    
    stored = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        front = item.get("front", "").strip()
        back = item.get("back", "").strip()
        if not front or not back or front in existing_fronts:
            continue
        
        card = Flashcard(
            topic_id=topic.id,
            front=front,
            back=back,
            leitner_box=1,
            next_review=datetime.utcnow(),
        )
        db.add(card)
        existing_fronts.add(front)
        stored += 1
    
    if stored:
        print(f"[PreGen] Stored {stored} flashcards for '{topic.title}'")

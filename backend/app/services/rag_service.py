"""
RAG service — Retrieval-Augmented Generation pipeline.

Uses Ollama (free local LLM) when available, with comprehensive
rule-based fallbacks for when Ollama is not running.

All AI is FREE — no paid APIs.
"""
import httpx
import json
import re
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.upload import ContentChunk
from app.services.embedding_service import get_embedding_service


async def check_ollama_available() -> bool:
    """Check if Ollama is running and accessible."""
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False


async def generate_with_ollama(prompt: str, system: str = "", max_tokens: int = 500) -> Optional[str]:
    """Generate text using Ollama local LLM. Returns None if unavailable."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "model": settings.OLLAMA_MODEL,
                "prompt": prompt,
                "system": system or "You are an academic assistant. Be concise and accurate.",
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": 0.7,
                }
            }
            resp = await client.post(f"{settings.OLLAMA_BASE_URL}/api/generate", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("response", "").strip()
    except Exception:
        pass
    return None


async def retrieve_context(query: str, db: AsyncSession, k: int = 5) -> list[str]:
    """Retrieve relevant content chunks using the embedding service."""
    service = get_embedding_service()
    chunk_ids = service.search(query, k=k)

    if not chunk_ids:
        return []

    result = await db.execute(
        select(ContentChunk).where(ContentChunk.id.in_(chunk_ids))
    )
    chunks = result.scalars().all()
    return [c.content for c in chunks]


async def rag_generate(
    query: str,
    task: str,
    db: AsyncSession,
    topic_title: str = "",
    max_context_chunks: int = 5,
) -> str:
    """
    Full RAG pipeline: retrieve context → generate with LLM (or fallback).

    Tasks: 'question', 'summary', 'flashcard', 'explain', 'quiz'
    """
    # 1. Retrieve relevant context
    search_query = f"{topic_title} {query}" if topic_title else query
    context_texts = await retrieve_context(search_query, db, k=max_context_chunks)
    context = "\n\n".join(context_texts) if context_texts else ""

    # 2. Try Ollama LLM generation
    ollama_ok = await check_ollama_available()

    if ollama_ok and context:
        prompt = _build_prompt(task, query, context, topic_title)
        result = await generate_with_ollama(prompt)
        if result:
            return result

    # 3. Fallback: rule-based generation from context
    return _rule_based_generate(task, query, context, topic_title)


def _build_prompt(task: str, query: str, context: str, topic: str) -> str:
    """Build a prompt for the LLM based on the task type."""
    prompts = {
        "question": f"""Based on the following study material about {topic}:

{context}

Generate a thoughtful exam question about this topic. Include the expected answer.
Format: QUESTION: [question text]
ANSWER: [answer text]""",

        "summary": f"""Based on the following study material about {topic}:

{context}

Write a concise revision summary (3-5 bullet points) covering the key concepts.""",

        "flashcard": f"""Based on the following study material about {topic}:

{context}

Generate 3 flashcards for studying. Format each as:
FRONT: [question/term]
BACK: [answer/definition]""",

        "explain": f"""Based on the following study material:

{context}

Explain: {query}
Be clear and concise. Use examples where helpful.""",

        "quiz_mcq": f"""Based on the following study material about {topic}:

{context}

Generate a multiple choice question. Format:
QUESTION: [question]
A) [option]
B) [option]
C) [option]
D) [option]
ANSWER: [correct letter]""",
    }
    return prompts.get(task, prompts["explain"])


def _rule_based_generate(task: str, query: str, context: str, topic: str) -> str:
    """Rule-based fallback generation when Ollama is not available."""
    if not context:
        context = f"Topic: {topic or query}"

    # Extract key sentences from context
    sentences = [s.strip() for s in re.split(r'[.!?]+', context) if len(s.strip()) > 20]
    key_points = sentences[:5] if sentences else [context[:200]]

    if task == "question":
        if key_points:
            return f"Explain the concept of {topic or 'this topic'} with reference to: {key_points[0]}."
        return f"Explain {topic or query} in detail with examples."

    elif task == "summary":
        bullet_points = "\n".join(f"• {p}" for p in key_points[:5])
        return f"**Key Points for {topic}:**\n\n{bullet_points}"

    elif task == "flashcard":
        cards = []
        for i, point in enumerate(key_points[:3]):
            # Create a Q&A from the sentence
            words = point.split()
            if len(words) > 5:
                # Mask a key term to create a question
                cards.append(f"FRONT: What is meant by: {' '.join(words[:8])}...?\nBACK: {point}")
            else:
                cards.append(f"FRONT: Define {point}\nBACK: {point}")
        return "\n\n".join(cards) if cards else f"FRONT: What is {topic}?\nBACK: {context[:200]}"

    elif task == "explain":
        return f"**{topic}**\n\n{context[:500]}"

    elif task == "quiz_mcq":
        if key_points:
            q = key_points[0]
            return f"""QUESTION: Which of the following best describes: {q[:80]}...?
A) {q}
B) This is not related to {topic}
C) None of the above
D) All of the above
ANSWER: A"""

    return context[:300]

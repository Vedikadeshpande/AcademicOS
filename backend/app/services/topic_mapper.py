"""Topic mapper — maps uploaded PPT/PDF content chunks to syllabus topics."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.syllabus import SyllabusUnit, SyllabusTopic
from app.models.upload import ContentChunk
from app.utils.text_cleaning import normalize_for_comparison


async def map_chunks_to_topics(subject_id: str, db: AsyncSession):
    """
    Map content chunks to syllabus topics using keyword matching.

    For each chunk, find the best matching syllabus topic based on
    keyword overlap. Update topic.is_covered and unit.coverage_pct.
    """
    # Get all topics for this subject
    topics_result = await db.execute(
        select(SyllabusTopic)
        .join(SyllabusUnit)
        .where(SyllabusUnit.subject_id == subject_id)
    )
    topics = topics_result.scalars().all()

    if not topics:
        return

    # Get all unmapped chunks for this subject
    from app.models.upload import Upload
    chunks_result = await db.execute(
        select(ContentChunk)
        .join(Upload)
        .where(Upload.subject_id == subject_id, ContentChunk.topic_id == None)
    )
    chunks = chunks_result.scalars().all()

    # Normalize topic titles for comparison
    topic_keywords = {}
    for topic in topics:
        normalized = normalize_for_comparison(topic.title)
        keywords = set(normalized.split())
        topic_keywords[topic.id] = {
            "topic": topic,
            "keywords": keywords,
            "normalized": normalized,
        }

    # Match each chunk to the best topic
    for chunk in chunks:
        chunk_normalized = normalize_for_comparison(chunk.content)
        chunk_words = set(chunk_normalized.split())

        best_match = None
        best_score = 0

        for topic_id, data in topic_keywords.items():
            # Score = number of topic keywords found in chunk / total topic keywords
            if not data["keywords"]:
                continue

            overlap = data["keywords"] & chunk_words
            score = len(overlap) / len(data["keywords"])

            # Also check if topic title appears as substring
            if data["normalized"] in chunk_normalized:
                score += 0.5

            if score > best_score and score >= 0.3:  # Minimum threshold
                best_score = score
                best_match = topic_id

        if best_match:
            chunk.topic_id = best_match

    await db.flush()

    # Update coverage flags
    for topic in topics:
        # Check if any chunks are mapped to this topic
        mapped_result = await db.execute(
            select(ContentChunk).where(ContentChunk.topic_id == topic.id).limit(1)
        )
        topic.is_covered = mapped_result.scalar_one_or_none() is not None

    # Update unit coverage percentages
    units_result = await db.execute(
        select(SyllabusUnit).where(SyllabusUnit.subject_id == subject_id)
    )
    units = units_result.scalars().all()

    for unit in units:
        unit_topics = await db.execute(
            select(SyllabusTopic).where(SyllabusTopic.unit_id == unit.id)
        )
        unit_topics_list = unit_topics.scalars().all()
        if unit_topics_list:
            covered = sum(1 for t in unit_topics_list if t.is_covered)
            unit.coverage_pct = round(covered / len(unit_topics_list) * 100, 1)

    await db.commit()

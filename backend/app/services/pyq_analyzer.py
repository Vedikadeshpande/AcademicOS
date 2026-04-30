"""
PYQ Analyzer — analyzes previous year question papers.

Extracts keyword frequencies, detects topic clustering,
and computes recurrence scores. Uses TF-IDF (free, no API).
"""
import re
from collections import Counter
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.models.syllabus import SyllabusUnit, SyllabusTopic
from app.models.upload import Upload, ContentChunk, PYQPattern


async def analyze_pyq(subject_id: str, db: AsyncSession) -> dict:
    """
    Analyze all PYQ papers for a subject.

    Returns:
        - keyword_freq: top 30 keywords
        - topic_recurrence: {topic_id: recurrence_score}
        - coverage_analysis: which topics appear often in PYQs
    """
    # Get PYQ uploads
    result = await db.execute(
        select(Upload).where(
            Upload.subject_id == subject_id,
            Upload.file_type == "pyq",
            Upload.status == "done",
        )
    )
    pyq_uploads = result.scalars().all()

    if not pyq_uploads:
        return {"keyword_freq": [], "topic_recurrence": {}, "analysis": "No PYQ papers uploaded yet."}

    # Get all chunks from PYQ uploads
    pyq_upload_ids = [u.id for u in pyq_uploads]
    chunks_result = await db.execute(
        select(ContentChunk).where(ContentChunk.upload_id.in_(pyq_upload_ids))
    )
    chunks = chunks_result.scalars().all()
    pyq_texts = [c.content for c in chunks if c.content]

    if not pyq_texts:
        return {"keyword_freq": [], "topic_recurrence": {}, "analysis": "PYQ papers have no extractable content."}

    # Get syllabus topics
    topics_result = await db.execute(
        select(SyllabusTopic)
        .join(SyllabusUnit)
        .where(SyllabusUnit.subject_id == subject_id)
    )
    topics = topics_result.scalars().all()
    topic_titles = [t.title for t in topics]

    # 1. Keyword frequency extraction
    all_text = " ".join(pyq_texts).lower()
    # Remove common words and short words
    words = re.findall(r'\b[a-zA-Z]{4,}\b', all_text)
    stop_words = {
        'this', 'that', 'with', 'from', 'which', 'what', 'your', 'have', 'been',
        'will', 'would', 'could', 'should', 'about', 'each', 'make', 'than',
        'them', 'then', 'they', 'were', 'more', 'some', 'when', 'very', 'also',
        'into', 'only', 'other', 'such', 'most', 'over', 'after', 'before',
        'between', 'under', 'these', 'those', 'through', 'answer', 'marks',
        'question', 'explain', 'describe', 'define', 'write', 'following', 'given',
    }
    filtered = [w for w in words if w not in stop_words]
    keyword_freq = Counter(filtered).most_common(30)

    # 2. Topic matching via TF-IDF
    topic_recurrence = {}
    if topics and pyq_texts:
        try:
            vectorizer = TfidfVectorizer(
                stop_words="english",
                max_features=3000,
                ngram_range=(1, 2),
            )
            corpus = topic_titles + pyq_texts
            tfidf = vectorizer.fit_transform(corpus)

            n_topics = len(topic_titles)
            topic_vectors = tfidf[:n_topics]
            pyq_vectors = tfidf[n_topics:]

            # Each PYQ chunk → closest topic
            sim_matrix = cosine_similarity(pyq_vectors, topic_vectors)

            topic_hits = Counter()
            for row in sim_matrix:
                best_idx = row.argmax()
                if row[best_idx] > 0.1:  # Minimum similarity threshold
                    topic_hits[best_idx] += 1

            # Normalize to 0-1 recurrence scores
            max_hits = max(topic_hits.values()) if topic_hits else 1
            for idx, hits in topic_hits.items():
                if idx < len(topics):
                    score = round(hits / max_hits, 3)
                    topic_recurrence[topics[idx].id] = score

                    # Update the topic's pyq_frequency in DB
                    topics[idx].pyq_frequency = score

                    # Upsert PYQ pattern
                    existing = await db.execute(
                        select(PYQPattern).where(PYQPattern.topic_id == topics[idx].id)
                    )
                    pattern = existing.scalar_one_or_none()
                    if pattern:
                        pattern.frequency = hits
                        pattern.recurrence_score = score
                        pattern.keywords = ",".join([kw for kw, _ in keyword_freq[:10]])
                    else:
                        db.add(PYQPattern(
                            topic_id=topics[idx].id,
                            frequency=hits,
                            recurrence_score=score,
                            keywords=",".join([kw for kw, _ in keyword_freq[:10]]),
                        ))

            await db.commit()
        except Exception as e:
            print(f"PYQ analysis error: {e}")

    # 3. Build analysis summary
    hot_topics = []
    for tid, score in sorted(topic_recurrence.items(), key=lambda x: x[1], reverse=True)[:5]:
        topic = next((t for t in topics if t.id == tid), None)
        if topic:
            hot_topics.append(f"{topic.title} ({score*100:.0f}%)")

    analysis = f"Analyzed {len(pyq_texts)} question segments from {len(pyq_uploads)} papers."
    if hot_topics:
        analysis += f"\n\nMost frequently tested topics:\n" + "\n".join(f"  • {t}" for t in hot_topics)

    return {
        "keyword_freq": [{"word": word, "count": count} for word, count in keyword_freq],
        "topic_recurrence": topic_recurrence,
        "analysis": analysis,
        "papers_analyzed": len(pyq_uploads),
        "segments_analyzed": len(pyq_texts),
    }

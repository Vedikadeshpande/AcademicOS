import json
import re
import httpx
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import tempfile
import os
from sklearn.metrics.pairwise import cosine_similarity

from app.config import settings
from app.models.syllabus import SyllabusTopic
from app.models.upload import ContentChunk
from app.schemas.viva import VivaEvaluateResponse, VivaQuestionResponse
from app.services.embedding_service import get_embedding_service

whisper_model = None  # Lazy load


# ---------------------------
# 🔹 LLM CALL (GROQ API)
# ---------------------------
async def _fast_llm_generate(prompt: str, system: str, max_tokens: int = 1500) -> str:
    """Generate LLM response via Groq Llama3 for ultra-fast generation."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            headers = {
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": settings.GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"},
                "max_tokens": max_tokens,
                "temperature": 0.5
            }
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload
            )
            if resp.status_code == 200:
                print(f"[VivaService] Groq responded successfully with status 200")
                return resp.json()["choices"][0]["message"]["content"].strip()
            else:
                return f"[ERROR: GROQ STATUS {resp.status_code}] {resp.text}"
    except httpx.ConnectError:
        print("[VivaService] LLM error: Connection to Groq failed.")
        return "[ERROR: GROQ CONNECTION FAILED] Could not reach Groq servers."
    except httpx.ReadTimeout:
        print("[VivaService] LLM error: ReadTimeout.")
        return "[ERROR: GROQ TIMEOUT] Groq took too long to respond."
    except Exception as e:
        error_name = type(e).__name__
        print(f"[VivaService] LLM error: {error_name} - {str(e)}")
        return f"[ERROR: GROQ UNKNOWN {error_name}] {str(e)}"


# ---------------------------
# 🔹 SAFE JSON PARSER
# ---------------------------
# ---------------------------
# 🔹 SAFE JSON PARSER
# ---------------------------
def _parse_json(raw: str) -> Dict[str, Any]:
    if not raw or not raw.strip():
        return {}
        
    raw = raw.strip()
    
    # Pre-clean trailing commas
    raw = re.sub(r',\s*\}', '}', raw)
    raw = re.sub(r',\s*\]', ']', raw)

    # 1st attempt: direct loads
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
        
    # 2nd attempt: strip markdown code blocks completely
    cleaned = re.sub(r'^```(?:json)?', '', raw, flags=re.MULTILINE|re.IGNORECASE)
    cleaned = re.sub(r'```$', '', cleaned, flags=re.MULTILINE)
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 3rd attempt: extract anything that looks like a JSON dictionary { ... }
    match = re.search(r'(\{.*\})', cleaned, re.DOTALL)
    if match:
        extracted = match.group(1).strip()
        # Clean trailing commas in the extracted block again
        extracted = re.sub(r',\s*\}', '}', extracted)
        extracted = re.sub(r',\s*\]', ']', extracted)
        
        # Strip control characters that commonly break parsing
        extracted = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', extracted)
        try:
            return json.loads(extracted)
        except json.JSONDecodeError as err:
            print(f"[_parse_json] Failed aggressive parsing: {err}\nExtracted string:\n{extracted}")

    print(f"[_parse_json] Completely failed to parse anything from:\n{raw}")
    return {}


# ---------------------------
# 🔹 CONTEXT (READY FOR VECTOR DB)
# ---------------------------
async def _get_context(topic: SyllabusTopic) -> str:
    """
    Replace this with vector DB retrieval later.
    """
    content = topic.content_cache or ""
    return content[:1200]  # slightly larger context


async def _get_topic_context(topic: SyllabusTopic, db: AsyncSession) -> str:
    """Retrieve the best available topic text for grading short answers."""
    if topic is None:
        return ""

    content = (topic.content_cache or "").strip()
    if content:
        return content[:1400]

    result = await db.execute(select(ContentChunk.content).where(ContentChunk.topic_id == topic.id))
    chunks = [row[0] for row in result.all() if row[0]]
    if not chunks:
        return ""

    combined = "\n".join(chunks)
    return combined[:1400]


def _extract_short_answer_keywords(answer_json: str, topic: SyllabusTopic) -> list[str]:
    """Extract keywords from stored short-answer metadata or fallback to topic title keywords."""
    keywords: list[str] = []
    if answer_json:
        try:
            payload = json.loads(answer_json)
            keywords = [kw.strip() for kw in payload.get("keywords", []) if isinstance(kw, str) and kw.strip()]
        except Exception:
            keywords = []

    if not keywords and topic is not None:
        keywords = [w.lower() for w in re.split(r'[\s/,;()\-]+', topic.title) if len(w) >= 4]

    return keywords[:10]


async def evaluate_short_answer(
    question: str,
    user_answer: str,
    answer_meta: str,
    topic: Optional[SyllabusTopic],
    marks: int,
    db: AsyncSession,
) -> dict[str, object]:
    """Grade a short-answer response using topic context and LLM evaluation."""
    if not user_answer or not user_answer.strip():
        return {
            "awarded_marks": 0,
            "max_marks": marks,
            "analysis": "No answer was provided.",
            "good_points": [],
            "missing_points": ["No answer received."],
            "mistakes": [],
            "suggestions": ["Write a clear response and try again."],
        }

    context = await _get_topic_context(topic, db) if topic else ""
    keywords = _extract_short_answer_keywords(answer_meta, topic)
    hint = ""
    try:
        payload = json.loads(answer_meta or "{}")
        hint = payload.get("hint", "")
    except Exception:
        hint = ""

    hint_text = hint or "Use the relevant course concepts and examples when answering."
    keyword_text = ", ".join(keywords) if keywords else "No explicit keywords available."

    # Rule-based check for uncertainty / filler responses
    uncertain_phrases = [
        "i don't know", "idk", "dont know", "do not know", "not sure",
        "i'm not sure", "im not sure", "no idea", "kinda", "sort of", "maybe",
        "i guess", "i think", "could be", "i'm not a", "i have no clue"
    ]
    lower_answer = user_answer.lower()
    if any(phrase in lower_answer for phrase in uncertain_phrases):
        # If the answer is mostly uncertain wording and contains no clear facts,
        # mark it as unrelated / no answer.
        fact_words = [w for w in re.split(r'[^a-z0-9]+', lower_answer) if w and w not in {
            'i', 'm', 'im', 'dont', 'do', 'not', 'know', 'idk', 'no', 'idea', 'sort', 'of', 'maybe', 'could', 'be', 'think', 'guess', 'kinda', 'man'
        }]
        if len(fact_words) < 4:
            return {
                "awarded_marks": 0,
                "max_marks": marks,
                "analysis": "The answer is mostly uncertainty and does not answer the question.",
                "good_points": [],
                "missing_points": ["The student did not provide a relevant answer."],
                "mistakes": ["Uncertainty / filler response"],
                "suggestions": ["Answer the question directly using the topic concepts."],
            }

    # Quick relevance check using embeddings
    relevance_score = 1.0
    if context and user_answer.strip():
        try:
            service = get_embedding_service()
            # Compute similarity between user answer and context
            if service.is_fitted:
                # Transform both texts
                texts = [user_answer, context]
                tfidf_matrix = service.vectorizer.transform(texts)
                similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
                relevance_score = float(similarity)
            else:
                # Fallback: simple keyword overlap
                user_lower = user_answer.lower()
                context_lower = context.lower()
                user_words = set(user_lower.split())
                context_words = set(context_lower.split())
                overlap = len(user_words & context_words)
                total_user = len(user_words)
                relevance_score = overlap / total_user if total_user > 0 else 0.0
        except Exception:
            relevance_score = 0.5  # Neutral if check fails

    # If relevance is very low, penalize heavily
    if relevance_score < 0.08:
        return {
            "awarded_marks": 0,
            "max_marks": marks,
            "analysis": "The answer appears unrelated to the question or topic.",
            "good_points": [],
            "missing_points": ["Answer does not address the question."],
            "mistakes": ["Irrelevant content"],
            "suggestions": ["Re-read the question and provide a relevant answer."],
        }

    system_prompt = "You are a fair and lenient university professor. Output ONLY valid JSON."
    prompt = f"""
You are grading a short-answer exam response.
Be fair and generous, like a professor who awards partial credit for partially correct thinking.
Avoid penalising minor wording differences.
Do not hallucinate details that are not supported by the source material.

CRITICAL RULES:
- If the student says they do not know, expresses uncertainty, or only writes filler, award 0 marks.
- Only award credit for a real attempt to answer the question with relevant points.
- Do not award marks just because the answer contains topic keywords if the answer is otherwise off-topic or nonsense.
- If the answer is not a direct response to the question, award 0 marks.

Question:
{question}

Guidance:
{hint_text}

Topic context:
{context or 'No additional source content available.'}

Keywords:
{keyword_text}

Student answer:
{user_answer}

Return ONLY valid JSON with these fields:
{{
  "awarded_marks": 0,
  "max_marks": {marks},
  "analysis": "A short professor-style judgement.",
  "good_points": ["string"],
  "missing_points": ["string"],
  "mistakes": ["string"],
  "suggestions": ["string"]
}}
"""

    raw = await _fast_llm_generate(prompt, system_prompt, max_tokens=1000)
    data = _parse_json(raw)

    awarded_marks = data.get("awarded_marks")
    if isinstance(awarded_marks, (float, int)):
        awarded_marks = int(round(awarded_marks))
    else:
        awarded_marks = 0

    awarded_marks = max(0, min(awarded_marks, marks))
    if not data:
        matched = 0
        if keywords:
            answer_lower = user_answer.lower()
            matched = sum(1 for kw in keywords if kw.lower() in answer_lower)
        awarded_marks = min(marks, max(1, matched)) if matched > 0 else 0

    return {
        "awarded_marks": awarded_marks,
        "max_marks": marks,
        "analysis": data.get("analysis", "Your answer has been evaluated."),
        "good_points": data.get("good_points", []),
        "missing_points": data.get("missing_points", []),
        "mistakes": data.get("mistakes", []),
        "suggestions": data.get("suggestions", ["Review the topic and try to include the main points more clearly."])
    }


import random

# ---------------------------
# 🔹 GENERATE QUESTION (INSTANT)
# ---------------------------
async def generate_viva_question(topic_id: str, db: AsyncSession) -> Optional[VivaQuestionResponse]:
    result = await db.execute(select(SyllabusTopic).where(SyllabusTopic.id == topic_id))
    topic = result.scalar_one_or_none()

    if not topic:
        return None

    context = await _get_context(topic)

    # Bypass the heavy local LLM call completely for question generation.
    # On non-GPU machines, generating a question can take 30-90 seconds. 
    # This instant template-based generator provides 0-millisecond latency.
    
    templates = [
        "Could you explain the main concepts and real-world applications of {title}?",
        "What are the core components of {title}, and how do they function together in a practical scenario?",
        "Describe the significance of {title}. What fundamentally changes if it is implemented or understood incorrectly?",
        "If you were to teach {title} to a beginner, how would you define its key principles?",
        "Walk me through the theoretical background of {title}. Why is it such a critical concept?"
    ]
    
    question = random.choice(templates).format(title=topic.title)

    # We feed the syllabus context directly as the ideal answer.
    # The evaluator LLM in Step 2 will use this exact context to accurately cross-reference
    # the student's transcription and generate the missing_points and mistakes!
    ideal_context = context[:3000] if context else f"- Definition of {topic.title}\n- Key aspects and workings\n- Real world usage."
    
    ideal_answer = f"To score well, the student should explain the core facts about {topic.title} found within this source material:\n\n{ideal_context}"

    return VivaQuestionResponse(
        question=question,
        ideal_answer=ideal_answer,
        audio_url=None
    )


# ---------------------------
# 🔹 EVALUATE ANSWER (UPGRADED)
# ---------------------------
async def evaluate_viva_answer(question: str, ideal_answer: str, transcription: str) -> VivaEvaluateResponse:
    # 🚨 Handle empty speech
    if not transcription or not transcription.strip():
        return VivaEvaluateResponse(
            transcription="",
            score=0,
            analysis="The system could not detect any meaningful speech.",
            good_points=[],
            missing_points=["No answer detected"],
            mistakes=[],
            suggestions=["Speak clearly and try again."]
        )

    # 🚨 Handle "I don't know" or pure filler before wasting LLM time
    uncertain_phrases = [
        "i don't know", "idk", "dont know", "do not know", "not sure",
        "i'm not sure", "im not sure", "no idea", "kinda", "sort of", "maybe",
        "i guess", "i think", "could be", "i'm not a", "i have no clue"
    ]
    lower_answer = transcription.lower()
    
    if any(phrase in lower_answer for phrase in uncertain_phrases):
        fact_words = [w for w in re.split(r'[^a-z0-9]+', lower_answer) if w and w not in {
            'i', 'm', 'im', 'dont', 'do', 'not', 'know', 'idk', 'no', 'idea', 'sort', 'of', 'maybe', 'could', 'be', 'think', 'guess', 'kinda', 'man', 'well', 'um', 'uh', 'ah', 'like'
        }]
        
        if len(fact_words) < 5:
            return VivaEvaluateResponse(
                transcription=transcription,
                score=0,
                analysis="It seems you were unsure or unable to answer the question.",
                good_points=[],
                missing_points=["The entire ideal answer was not covered due to an uncertain response."],
                mistakes=["Responded with uncertainty or filler words instead of relevant concepts."],
                suggestions=["Review the material and try answering the question again confidently."]
            )

    system_prompt = "You are a highly analytical university professor evaluating a Viva (oral exam) answer. Output ONLY valid JSON without any formatting or comments."

    prompt = f"""
You are grading a university viva exam.
Your task is to evaluate the student's answer based on the points they covered, the points they missed, mistakes they made, and how they could make it better.

STRICT EVALUATION ALGORITHM:
1. Break down the Ideal Answer into essential key concepts/points.
2. Check the Student Answer specifically for each of those key concepts.
3. If the student adequately explains a concept, add it to "good_points".
4. If the student fails to mention a critical concept, add it to "missing_points".
5. If the student states something factually incorrect or hallucinates information, add it to "mistakes".
6. Based on their performance, give specific "suggestions" on how they could have made their answer better and more complete.

Question:
{question}

Ideal Answer / Expected Concepts:
{ideal_answer}

Student Answer (from speech-to-text):
{transcription}

Return a valid JSON object EXACTLY like this (ensure strict JSON syntax):
{{
  "score": 5,
  "analysis": "A brief paragraph summarizing their performance and conceptual understanding in the second person (e.g. 'You demonstrated...').",
  "good_points": ["Point they successfully covered"],
  "missing_points": ["Point they missed"],
  "mistakes": ["Incorrect statement they made (if any)"],
  "suggestions": ["How they could have improved their answer"]
}}
"""

    raw = await _fast_llm_generate(prompt, system_prompt, max_tokens=1500)
    print(f"[VivaService] raw evaluate response: {raw}")
    
    if raw.startswith("[ERROR: GROQ"):
        return VivaEvaluateResponse(
            transcription=transcription,
            score=0,
            analysis=f"Backend Error: Groq generation failed. Please add your API key. Detailed error: {raw}",
            good_points=[],
            missing_points=[],
            mistakes=["The evaluation model API failed to connect."],
            suggestions=["Update your GROQ_API_KEY in backend/.env", "Restart the backend terminal", "Try again."]
        )

    data = _parse_json(raw)

    score = data.get("score", 5)
    if isinstance(score, float):
        score = int(round(score))
    elif not isinstance(score, int):
        score = 5

    # Enforce score bounds
    score = max(0, min(10, score))

    return VivaEvaluateResponse(
        transcription=transcription,
        score=score,
        analysis=data.get("analysis", "Your answer has been graded."),
        good_points=data.get("good_points", []),
        missing_points=data.get("missing_points", []),
        mistakes=data.get("mistakes", []),
        suggestions=data.get("suggestions", ["Revise the expected concepts and practice speaking your answer structurally."])
    )


# ---------------------------
# 🔹 WHISPER TRANSCRIPTION
# ---------------------------
async def transcribe_audio(audio_data: bytes) -> str:
    global whisper_model

    if whisper_model is None:
        from faster_whisper import WhisperModel
        import imageio_ffmpeg

        # Ensure ffmpeg works by aliasing the crazy platform name to 'ffmpeg.exe'
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        ffmpeg_dir = os.path.dirname(ffmpeg_exe)
        ffmpeg_alias = os.path.join(ffmpeg_dir, "ffmpeg.exe")
        
        if not os.path.exists(ffmpeg_alias):
            import shutil
            shutil.copy(ffmpeg_exe, ffmpeg_alias)
            
        os.environ["PATH"] += os.pathsep + ffmpeg_dir

        print("[VivaService] Loading Faster-Whisper 'base.en' model...")
        whisper_model = WhisperModel("base.en", device="cpu", compute_type="int8")

    print(f"Audio size: {len(audio_data)} bytes")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
        tmp.write(audio_data)
        tmp_path = tmp.name

    wav_path = tmp_path.replace(".webm", ".wav")

    try:
        if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
            print("Audio file empty or missing")

        import subprocess
        subprocess.run([
            "ffmpeg", "-i", tmp_path,
            "-ar", "16000",
            "-ac", "1",
            wav_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        segments, info = whisper_model.transcribe(wav_path, beam_size=5)
        text = " ".join([segment.text for segment in segments])
        return text.strip()

    except Exception as e:
        print(f"[VivaService] Whisper transcription failed: {e}")
        return ""

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        if os.path.exists(wav_path):
            os.remove(wav_path)
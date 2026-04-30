"""Quiz endpoints — generate, take, and score quizzes."""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.subject import Subject
from app.models.quiz import QuizSession, QuizQuestion, QuizAnswer
from app.models.syllabus import SyllabusTopic, SyllabusUnit
from app.schemas.quiz import QuizStartRequest, QuizQuestionResponse, QuizSubmitRequest, QuizResultResponse, QuestionResult, ExamPaperRequest
from app.services.question_generator import generate_questions, generate_mock_paper, generate_exam_paper
from app.services.viva_service import evaluate_short_answer

router = APIRouter(prefix="/api/quizzes", tags=["quizzes"])


@router.post("/generate")
async def start_quiz(req: QuizStartRequest, db: AsyncSession = Depends(get_db)):
    """Generate a new quiz for a subject."""
    result = await db.execute(select(Subject).where(Subject.id == req.subject_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Subject not found")

    q_type = "mixed"
    if req.quiz_type == "topic":
        q_type = "mcq"
    elif req.quiz_type == "short":
        q_type = "short"

    questions = await generate_questions(
        subject_id=req.subject_id,
        db=db,
        num_questions=req.num_questions,
        question_type=q_type,
        difficulty=req.difficulty,
        topic_ids=req.topic_ids if req.topic_ids else None,
    )

    if not questions:
        raise HTTPException(status_code=400, detail="No topics available to generate questions from")

    # Create quiz session
    session = QuizSession(
        subject_id=req.subject_id,
        quiz_type=req.quiz_type,
        total_questions=len(questions),
    )
    db.add(session)
    await db.flush()

    # Create question records
    question_responses = []
    for q in questions:
        quiz_q = QuizQuestion(
            session_id=session.id,
            topic_id=q["topic_id"],
            question_text=q["question_text"],
            question_type=q["question_type"],
            marks=q["marks"],
            correct_answer=q["correct_answer"],
            options=q.get("options"),
        )
        db.add(quiz_q)
        await db.flush()

        question_responses.append({
            "id": quiz_q.id,
            "question_text": quiz_q.question_text,
            "question_type": quiz_q.question_type,
            "marks": quiz_q.marks,
            "options": quiz_q.options,
            "topic_title": q.get("topic_title", ""),
            "explanation": q.get("explanation", ""),
        })

    await db.commit()

    return {
        "session_id": session.id,
        "total_questions": len(question_responses),
        "questions": question_responses,
    }


@router.post("/mock-paper")
async def generate_mock(
    subject_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Generate a full mock exam paper."""
    result = await db.execute(select(Subject).where(Subject.id == subject_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Subject not found")

    # Get marking scheme
    from app.models.upload import MarkingScheme
    schemes_result = await db.execute(
        select(MarkingScheme).where(MarkingScheme.subject_id == subject_id)
    )
    schemes = schemes_result.scalars().all()

    marking_scheme = None
    if schemes:
        marking_scheme = [
            {"marks": s.marks, "count": s.question_count, "type": s.question_type}
            for s in schemes
        ]

    questions = await generate_mock_paper(subject_id, db, marking_scheme)

    # Create session
    session = QuizSession(
        subject_id=subject_id,
        quiz_type="mock",
        total_questions=len(questions),
    )
    db.add(session)
    await db.flush()

    question_responses = []
    for q in questions:
        quiz_q = QuizQuestion(
            session_id=session.id,
            topic_id=q["topic_id"],
            question_text=q["question_text"],
            question_type=q["question_type"],
            marks=q["marks"],
            correct_answer=q["correct_answer"],
            options=q.get("options"),
        )
        db.add(quiz_q)
        await db.flush()

        question_responses.append({
            "id": quiz_q.id,
            "question_text": quiz_q.question_text,
            "question_type": quiz_q.question_type,
            "marks": quiz_q.marks,
            "options": quiz_q.options,
            "topic_title": q.get("topic_title", ""),
            "explanation": q.get("explanation", ""),
        })

    await db.commit()

    total_marks = sum(q["marks"] for q in question_responses)
    return {
        "session_id": session.id,
        "total_questions": len(question_responses),
        "total_marks": total_marks,
        "questions": question_responses,
    }

@router.post("/generate-exam-paper")
async def generate_exam_paper_endpoint(
    req: ExamPaperRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate a full exam paper based on Bloom's taxonomy."""
    result = await db.execute(select(Subject).where(Subject.id == req.subject_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Subject not found")

    questions = await generate_exam_paper(req.subject_id, db, req.exam_type)

    if not questions:
        raise HTTPException(status_code=400, detail="Failed to generate exam paper or no topics available.")

    # Create session
    session = QuizSession(
        subject_id=req.subject_id,
        quiz_type=f"exam_{req.exam_type}",
        total_questions=len(questions),
    )
    db.add(session)
    await db.flush()

    question_responses = []
    for q in questions:
        quiz_q = QuizQuestion(
            session_id=session.id,
            topic_id=q["topic_id"],
            question_text=q["question_text"],
            question_type=q["question_type"],
            marks=q["marks"],
            correct_answer=q["correct_answer"],
            options=q.get("options"),
        )
        db.add(quiz_q)
        await db.flush()

        question_responses.append({
            "id": quiz_q.id,
            "question_text": quiz_q.question_text,
            "question_type": quiz_q.question_type,
            "marks": quiz_q.marks,
            "options": quiz_q.options,
            "topic_title": q.get("topic_title", ""),
            "explanation": q.get("explanation", ""),
        })

    await db.commit()

    total_marks = sum(q["marks"] for q in question_responses)
    return {
        "session_id": session.id,
        "total_questions": len(question_responses),
        "total_marks": total_marks,
        "questions": question_responses,
    }


@router.post("/submit/{session_id}")
async def submit_quiz(session_id: str, req: QuizSubmitRequest, db: AsyncSession = Depends(get_db)):
    """Submit quiz answers and get results."""
    session = await db.get(QuizSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Quiz session not found")

    # Get questions
    questions_result = await db.execute(
        select(QuizQuestion).where(QuizQuestion.session_id == session_id)
    )
    questions = {q.id: q for q in questions_result.scalars().all()}

    topic_ids = {q.topic_id for q in questions.values() if q.topic_id}
    topics = {}
    if topic_ids:
        topic_result = await db.execute(select(SyllabusTopic).where(SyllabusTopic.id.in_(topic_ids)))
        topics = {t.id: t for t in topic_result.scalars().all()}

    correct_count = 0
    results = []
    total_awarded_marks = 0
    total_possible_marks = 0

    for answer in req.answers:
        q = questions.get(answer.question_id)
        if not q:
            continue

        is_correct = False
        display_answer = q.correct_answer  # What to show the user
        total_possible_marks += q.marks

        if q.correct_answer:
            user_clean = answer.user_answer.strip().lower()

            if q.question_type == "mcq":
                # MCQ: match the letter (A, B, C, D)
                correct_letter = q.correct_answer.strip().upper()
                user_letter = user_clean.upper()[:1] if user_clean else ""
                is_correct = user_letter == correct_letter
                total_awarded_marks += q.marks if is_correct else 0
                # Show the correct letter
                display_answer = correct_letter

            elif q.question_type == "short":
                # Short answer: use LLM evaluation, backed by topic content and stored hints.
                topic = topics.get(q.topic_id)
                evaluation = await evaluate_short_answer(
                    q.question_text,
                    answer.user_answer,
                    q.correct_answer or "",
                    topic,
                    q.marks,
                    db,
                )

                awarded = evaluation.get("awarded_marks", 0)
                max_marks = evaluation.get("max_marks", q.marks)
                is_correct = awarded == max_marks
                total_awarded_marks += awarded

                display_answer = evaluation.get("analysis", "Short answer evaluated.")
            else:
                # For other question types with a stored correct_answer, keep existing fallback behavior.
                total_awarded_marks += q.marks if q.correct_answer.strip().lower() in user_clean else 0

        if is_correct:
            correct_count += 1

        # Save answer
        qa = QuizAnswer(
            question_id=q.id,
            user_answer=answer.user_answer,
            is_correct=is_correct,
        )
        db.add(qa)

        awarded_marks = None
        good_points = []
        missing_points = []
        mistakes = []
        suggestions = []
        
        if q.question_type == "short":
            if 'evaluation' in locals():
                awarded_marks = evaluation.get("awarded_marks", 0)
                feedback = evaluation.get("analysis", display_answer)
                good_points = evaluation.get("good_points", [])
                missing_points = evaluation.get("missing_points", [])
                mistakes = evaluation.get("mistakes", [])
                suggestions = evaluation.get("suggestions", [])
            if q.correct_answer:
                try:
                    display_answer = json.loads(q.correct_answer).get("hint", display_answer)
                except Exception:
                    display_answer = display_answer

        if q.question_type == "mcq" and is_correct:
            awarded_marks = q.marks

        results.append(QuestionResult(
            question_id=q.id,
            question_text=q.question_text,
            user_answer=answer.user_answer,
            correct_answer=display_answer,
            is_correct=is_correct,
            awarded_marks=awarded_marks,
            max_marks=q.marks,
            feedback=feedback,
            good_points=good_points,
            missing_points=missing_points,
            mistakes=mistakes,
            suggestions=suggestions,
        ))

    # Update session
    session.correct_answers = correct_count
    if total_possible_marks > 0:
        session.score_pct = (total_awarded_marks / total_possible_marks * 100)
    else:
        session.score_pct = (correct_count / len(results) * 100) if results else 0

    # Round score before saving
    session.score_pct = round(session.score_pct, 1)

    # Update topic quiz accuracy
    for answer in req.answers:
        q = questions.get(answer.question_id)
        if q and q.topic_id:
            topic = await db.get(SyllabusTopic, q.topic_id)
            if topic:
                # Running average of quiz accuracy
                total_attempts = topic.quiz_accuracy * 10 + (1 if any(
                    r.question_id == q.id and r.is_correct for r in results
                ) else 0)
                topic.quiz_accuracy = total_attempts / 11  # Smooth average

    await db.commit()

    return QuizResultResponse(
        session_id=session.id,
        total_questions=len(results),
        correct_answers=correct_count,
        score_pct=round(session.score_pct, 1),
        results=results,
    )


@router.get("/history/{subject_id}")
async def quiz_history(subject_id: str, db: AsyncSession = Depends(get_db)):
    """Get quiz history for a subject."""
    result = await db.execute(
        select(QuizSession)
        .where(QuizSession.subject_id == subject_id)
        .order_by(QuizSession.taken_at.desc())
        .limit(20)
    )
    sessions = result.scalars().all()

    return [
        {
            "id": s.id,
            "quiz_type": s.quiz_type,
            "total_questions": s.total_questions,
            "correct_answers": s.correct_answers,
            "score_pct": round(s.score_pct, 1),
            "taken_at": s.taken_at.isoformat(),
        }
        for s in sessions
    ]

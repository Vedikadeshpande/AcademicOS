from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.schemas.viva import VivaQuestionRequest, VivaQuestionResponse, VivaEvaluateResponse
from app.services.viva_service import generate_viva_question, evaluate_viva_answer, transcribe_audio

router = APIRouter(prefix="/viva", tags=["Viva"])

@router.post("-question", response_model=VivaQuestionResponse)
async def get_viva_question(
    request: VivaQuestionRequest,
    db: AsyncSession = Depends(get_db)
):
    """Generates a Viva Question based on a topic."""
    res = await generate_viva_question(request.topic_id, db)
    if not res:
        raise HTTPException(status_code=404, detail="Topic not found or error generating question")
    return res

@router.post("-evaluate", response_model=VivaEvaluateResponse)
async def evaluate_viva(
    audio: UploadFile = File(...),
    question: str = Form(...),
    ideal_answer: str = Form(...),
    transcription: Optional[str] = Form(None) # Allows frontend to send SpeechRecognition text if Whisper isn't setup
):
    """Evaluates an audio answer or text transcription."""
    actual_transcription = ""
    # If the browser Speech API completely missed it or if it's too short, run the deep local ML model over the audio!
    if not transcription or len(transcription.strip()) < 5:
        audio_bytes = await audio.read()
        try:
            actual_transcription = await transcribe_audio(audio_bytes)
        except Exception:
            pass
    else:
        actual_transcription = transcription.strip()
        
    if not actual_transcription:
        actual_transcription = "[System: The AI was completely unable to hear or interpret the audio provided. Ensure your microphone is active.]"

    evaluation = await evaluate_viva_answer(question, ideal_answer, actual_transcription)
    return evaluation

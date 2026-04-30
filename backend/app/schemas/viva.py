from pydantic import BaseModel
from typing import List, Optional

class VivaQuestionRequest(BaseModel):
    topic_id: str

class VivaQuestionResponse(BaseModel):
    question: str
    audio_url: Optional[str] = None
    ideal_answer: str # Hidden from user

class VivaEvaluateResponse(BaseModel):
    transcription: str
    score: int
    analysis: str
    good_points: List[str]
    missing_points: List[str]
    mistakes: List[str]
    suggestions: List[str]

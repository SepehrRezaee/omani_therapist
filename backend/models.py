# backend/models.py

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict

class StartSessionResponse(BaseModel):
    session_id: str = Field(..., description="Unique session UUID")
    consent_text: str = Field(..., description="Consent prompt in Omani Arabic")

class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Existing session ID")

class ChatResponse(BaseModel):
    transcript: str = Field(..., description="User speech transcribed to text")
    emotion: str = Field(..., description="Detected emotion label (e.g. 'حزن')")
    crisis_flag: bool = Field(..., description="True if a crisis is detected")
    bot_audio_url: HttpUrl = Field(..., description="URL for the bot reply audio")

class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Error details for client display")

class SessionTurn(BaseModel):
    timestamp: str
    transcript: str
    emotion: str
    bot_response: str
    crisis_flag: bool
    audio_path: str
    bot_audio_path: str

class ExportedSession(BaseModel):
    session_id: str
    turns: List[SessionTurn]

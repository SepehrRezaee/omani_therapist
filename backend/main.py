# backend/main.py

import os
import uuid
import shutil
import logging
from datetime import datetime
from typing import Annotated

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, status
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.models import StartSessionResponse, ChatResponse
from backend.db import log_conversation, get_history, get_user_insights
from backend.speech_utils import transcribe_audio, synthesize_speech
from backend.therapy_core import analyze_emotion, is_crisis, generate_response, get_consent_text
from backend.evolution_core import analyze_session_for_insights

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omani-therapist")

settings = get_settings()

app = FastAPI(
    title="Omani Voice Therapist API",
    description="Privacy-first voice-only therapist for Omani Arabic speakers",
    version="1.0.0",
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

# --- Ensure Data Dirs Exist ---
USER_DIR = os.path.join(settings.DATA_DIR, "user_inputs")
BOT_DIR = os.path.join(settings.DATA_DIR, "bot_outputs")
os.makedirs(USER_DIR, exist_ok=True)
os.makedirs(BOT_DIR, exist_ok=True)

MAX_AUDIO_MB = 5

@app.post("/start_session/", response_model=StartSessionResponse, status_code=status.HTTP_201_CREATED)
def start_session():
    """Start a new anonymous session and return consent text."""
    session_id = str(uuid.uuid4())
    logger.info(f"Started new session: {session_id}")
    return StartSessionResponse(
        session_id=session_id,
        consent_text=get_consent_text()
    )

@app.post("/chat/", response_model=ChatResponse)
async def chat(
        session_id: Annotated[str, Form(...)],
        audio: Annotated[UploadFile, File(...)]
):
    """Process a single voice chat turn."""
    # --- Validate Audio Format and Size ---
    if audio.content_type not in ("audio/wav", "audio/x-wav"):
        logger.warning("Received unsupported audio format: %s", audio.content_type)
        raise HTTPException(status_code=415, detail="Unsupported audio format")

    # Limit file size (security & cost control)
    audio_bytes = await audio.read()
    if len(audio_bytes) > MAX_AUDIO_MB * 1024 * 1024:
        logger.warning("Audio file too large: %.2f MB", len(audio_bytes)/1e6)
        raise HTTPException(status_code=413, detail="Audio file too large (max 5MB)")

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    user_filename = f"{session_id}_{timestamp}.wav"
    user_path = os.path.join(USER_DIR, user_filename)
    with open(user_path, "wb") as f:
        f.write(audio_bytes)

    history = get_history(session_id)

    # --- Transcribe ---
    transcript = transcribe_audio(user_path)
    if not transcript:
        logger.error("Transcription failed for session %s", session_id)
        raise HTTPException(status_code=500, detail="Transcription failed")

    # --- Emotion & Crisis Analysis ---
    emotion = analyze_emotion(transcript, history)
    crisis = is_crisis(transcript, emotion, history)

    # --- Response Generation ---
    if crisis:
        bot_text = "🚨 نلاحظ حالة نفسية حرجة، يُرجى التواصل مع مختص فورًا."
    else:
        # Fetch user insights (using default_user for now as we don't have auth yet)
        user_insights = get_user_insights("default_user")
        bot_text = generate_response(
            transcript, emotion, history,
            user_insights=user_insights,
            lang_hint="Omani Arabic",
            code_switching=True
        )

    # --- Synthesize Bot Speech ---
    tts_tmp = synthesize_speech(bot_text)
    if not tts_tmp or not os.path.isfile(tts_tmp):
        logger.error("Speech synthesis failed for session %s", session_id)
        raise HTTPException(status_code=500, detail="Speech synthesis failed")

    bot_filename = f"{session_id}_{timestamp}_reply.wav"
    bot_path = os.path.join(BOT_DIR, bot_filename)
    try:
        shutil.move(tts_tmp, bot_path)
    except Exception as e:
        logger.exception("Failed to move TTS file from %s to %s", tts_tmp, bot_path)
        raise HTTPException(status_code=500, detail="Internal file error")

    # --- Log Conversation Turn ---
    try:
        log_conversation(
            session_id, transcript, emotion,
            bot_text, int(crisis),
            user_path, bot_path
        )
    except Exception as e:
        logger.warning("Logging failed for session %s: %s", session_id, e)

    # --- Return Result ---
    return ChatResponse(
        transcript=transcript,
        emotion=emotion,
        crisis_flag=bool(crisis),
        bot_audio_url=f"{settings.FRONTEND_URL}/api/audio/{session_id}/{timestamp}/"
    )

@app.get("/audio/{session_id}/{timestamp}/")
def serve_audio(session_id: str, timestamp: str):
    """Serve bot audio for playback."""
    bot_filename = f"{session_id}_{timestamp}_reply.wav"
    path = os.path.join(BOT_DIR, bot_filename)
    if not os.path.isfile(path):
        logger.warning("Audio not found: %s", path)
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(path, media_type="audio/wav")


from fastapi import BackgroundTasks

@app.post("/end_session/")
def end_session(session_id: str = Form(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    """
    End the session and trigger self-evolution analysis in the background.
    """
    logger.info(f"Ending session {session_id} and triggering evolution.")
    background_tasks.add_task(analyze_session_for_insights, session_id, "default_user")
    return {"status": "ok", "message": "Session ended, evolution triggered."}


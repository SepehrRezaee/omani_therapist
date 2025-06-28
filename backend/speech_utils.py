# backend/speech_utils.py

import os
import wave
import time
import logging
from tempfile import NamedTemporaryFile
from google import genai
from google.genai import types

from backend.config import get_settings

settings = get_settings()

# --- Logging setup ---
logger = logging.getLogger("speech_utils")
logger.setLevel(logging.INFO)

# --- Gemini Client ---
client = genai.Client(api_key=settings.GEMINI_API_KEY)

# --- Constants ---
TTS_VOICE = "Kore"  # Or "Sulafat" for Omani dialect if supported
TTS_MODEL = "gemini-2.5-flash-preview-tts"
STT_MODEL = "gemini-2.5-flash"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


# --- Helper: Save raw PCM to .wav ---
def _save_wave(data: bytes, output_path: str, channels=1, rate=24000, width=2):
    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(width)
        wf.setframerate(rate)
        wf.writeframes(data)


# --- Robust STT ---
def transcribe_audio(audio_path: str, prompt: str = "يرجى تحويل هذا الملف الصوتي إلى نص باللهجة العمانية فقط.") -> str:
    """
    Convert speech audio to Omani Arabic text using Gemini API with retries and logging.
    Returns '' on persistent failure.
    """
    if not os.path.exists(audio_path):
        logger.error(f"[STT] Audio file missing: {audio_path}")
        return ""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            start = time.time()
            myfile = client.files.upload(file=audio_path)
            response = client.models.generate_content(
                model=STT_MODEL,
                contents=[prompt, myfile]
            )
            logger.info(f"[STT] Success (attempt {attempt}) in {time.time() - start:.2f}s")
            return response.text.strip()
        except Exception as e:
            logger.error(f"[STT] Error (attempt {attempt}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
    return ""


# --- Robust TTS ---
def synthesize_speech(text: str, voice: str = TTS_VOICE) -> str:
    """
    Convert text to Omani Arabic speech using Gemini TTS with retries and logging.
    Returns path to WAV file or '' on persistent failure.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            start = time.time()
            response = client.models.generate_content(
                model=TTS_MODEL,
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice
                            )
                        )
                    )
                )
            )
            # Get PCM bytes
            pcm = response.candidates[0].content.parts[0].inline_data.data
            tmp = NamedTemporaryFile(delete=False, suffix=".wav")
            _save_wave(pcm, tmp.name)
            logger.info(f"[TTS] Success (attempt {attempt}) in {time.time() - start:.2f}s")
            return tmp.name
        except Exception as e:
            logger.error(f"[TTS] Error (attempt {attempt}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
    return ""

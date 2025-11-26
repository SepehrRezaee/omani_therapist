# backend/therapy_core.py

import logging
from typing import List, Tuple

from google import genai
from google.genai import types

from backend.config import get_settings

settings = get_settings()
logger = logging.getLogger("therapy_core")
logger.setLevel(logging.INFO)

client = genai.Client(api_key=settings.GEMINI_API_KEY)


# --- Consent Text ---
def get_consent_text() -> str:
    """Returns a clear, dialect-appropriate consent disclaimer."""
    return (
        "أوافق على تسجيل الجلسة وحفظها بشكل خاص حسب سياسة الخصوصية. "
        "هذا التطبيق ليس بديلاً عن المساعدة الطبية أو الطارئة."
    )


# --- Emotion Analysis ---
def emotion_prompt(history: List[Tuple[str, str]], transcript: str) -> str:
    history_txt = "\n".join([f"مستخدم: {h[0]}\nمعالج: {h[1]}" for h in history])
    return (
        f"هذه محادثة بين مستخدم عماني ومعالج افتراضي باللهجة العمانية:\n"
        f"{history_txt}\n"
        f"رسالة المستخدم الأخيرة:\n{transcript.strip()}\n"
        f"ما هي العاطفة الأساسية لهذه الرسالة؟ أجب بكلمة واحدة أو كلمتين (مثال: قلق، حزن، تفاؤل، توتر...)."
    )


def analyze_emotion(transcript: str, history: List[Tuple[str, str]] = []) -> str:
    prompt = emotion_prompt(history, transcript)
    try:
        response = call_gemini_api(prompt, max_tokens=8, temperature=0)
        if not response:
            logger.warning("[Emotion] Empty LLM response; returning 'محايد'")
            return "محايد"
        return response.strip().split()[0]
    except Exception as e:
        logger.error(f"[Emotion] Error: {e}")
        return "محايد"


# --- Crisis Analysis ---
def crisis_prompt(history: List[Tuple[str, str]], transcript: str) -> str:
    history_txt = "\n".join([f"مستخدم: {h[0]}\nمعالج: {h[1]}" for h in history])
    return (
        f"محادثة بين مستخدم عماني ومعالج نفسي:\n{history_txt}\n"
        f"رسالة المستخدم الأخيرة:\n{transcript.strip()}\n"
        f"هل هناك أي علامات على وجود أزمة نفسية خطيرة (انتحار، إيذاء الذات، انهيار، خطر على الحياة)؟ أجب (نعم) أو (لا) فقط."
    )


def is_crisis(transcript: str, emotion: str = None, history: List[Tuple[str, str]] = []) -> bool:
    prompt = crisis_prompt(history, transcript)
    try:
        response = call_gemini_api(prompt, max_tokens=2, temperature=0)
        if not response:
            logger.warning("[Crisis] Empty LLM response; returning False")
            return False
        return "نعم" in response.strip()
    except Exception as e:
        logger.error(f"[Crisis] Error: {e}")
        return False


# --- Response Generation ---
def system_prompt(history: List[Tuple[str, str]], user_insights: str = "") -> str:
    history_txt = "\n".join([f"مستخدم: {h[0]}\nمعالج: {h[1]}" for h in history])
    insights_txt = f"\nملاحظات عن المستخدم:\n{user_insights}\n" if user_insights else ""
    return (
        "أنت معالج افتراضي عماني تستمع للمستخدم وتستخدم أساليب علمية "
        "مثل العلاج السلوكي المعرفي وتراعي الدين والعادات المحلية.\n"
        f"{insights_txt}"
        f"{history_txt}\n"
        "رد بإيجاز، تعاطف، وعلاجات عملية باللهجة العمانية."
    )


def evaluator_prompt(user_message: str, generated_response: str, history: List[Tuple[str, str]] = []) -> str:
    history_txt = "\n".join([f"مستخدم: {h[0]}\nمعالج: {h[1]}" for h in history])
    return (
        f"راجع الرد التالي من معالج افتراضي عماني:\n"
        f"{history_txt}\n"
        f"سؤال المستخدم: {user_message}\n"
        f"رد المعالج: {generated_response}\n\n"
        f"هل الرد مختصر، واضح، ودقيق باللهجة العمانية؟ إذا يحتاج تحسين، اكتبه من جديد مختصر وبلسان عماني. إذا جيد، أعده كما هو."
    )


def generate_response(
        transcript: str,
        emotion: str,
        history: List[Tuple[str, str]] = [],
        user_insights: str = "",
        lang_hint: str = "Omani Arabic",
        code_switching: bool = True
) -> str:
    user_message = transcript.strip()
    prompt = (
        f"{system_prompt(history, user_insights)}\n"
        f"سؤال المستخدم: {user_message}\n"
        f"العاطفة المتوقعة: {emotion}\n"
        f"جواب المعالج:"
    )
    try:
        raw_response = call_gemini_api(prompt, max_tokens=128, temperature=0.45)
        if not raw_response:
            logger.warning("[Response] Empty LLM response; returning default")
            return "أشكرك على تواصلك. أنصحك بمراجعة مختص إذا كنت تمر بأزمة."
        eval_prompt = evaluator_prompt(user_message, raw_response, history)
        final_response = call_gemini_api(eval_prompt, max_tokens=128, temperature=0.25)
        return final_response.strip() if final_response else raw_response.strip()
    except Exception as e:
        logger.error(f"[Response] Error: {e}")
        return "عذراً، حصل خلل فني. حاول مرة ثانية أو تواصل مع مختص."


# --- Gemini API Utility ---
def call_gemini_api(
        prompt: str,
        max_tokens: int = 128,
        temperature: float = 0.4,
        model: str = "gemini-2.0-flash"
) -> str:
    """
    Handles communication with Gemini API and error logging.
    """
    try:
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={settings.GEMINI_API_KEY}"
        import requests
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}
        }
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=60)
        if not resp.ok:
            logger.error(f"[Gemini API] {resp.status_code}: {resp.text}")
            return ""
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        logger.error(f"[Gemini API] Request failed: {e}")
        return ""

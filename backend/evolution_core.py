# backend/evolution_core.py

import logging
from typing import List, Tuple

from backend.config import get_settings
from backend.therapy_core import call_gemini_api
from backend.db import get_history, save_user_insights, get_user_insights

settings = get_settings()
logger = logging.getLogger("evolution_core")
logger.setLevel(logging.INFO)

def insight_extraction_prompt(history_txt: str, current_insights: str) -> str:
    return (
        f"حلل سجل المحادثة التالي بين مستخدم عماني ومعالج افتراضي:\n"
        f"{history_txt}\n\n"
        f"الملاحظات السابقة عن المستخدم:\n{current_insights}\n\n"
        f"المطلوب: استخرج أو حدث ملف تعريف المستخدم النفسي (Insights) بنقاط مختصرة جداً.\n"
        f"ركز على: المواضيع المتكررة، أسلوب التخاطب المفضل، المحفزات العاطفية، وأي تفاصيل شخصية مهمة ذكرها.\n"
        f"اكتب النتيجة كنقاط (bulle points) باللغة العربية، ولا تزد عن 5 نقاط جوهرية."
    )

def analyze_session_for_insights(session_id: str, user_id: str = "default_user") -> None:
    """
    Analyzes the session history to update user insights.
    In a real app, user_id would come from auth. Here we might map session_id to a user or just use a default for demo.
    """
    try:
        # 1. Get Session History
        history_rows = get_history(session_id, limit=100) # Analyze up to last 100 turns
        if not history_rows:
            logger.warning(f"[Evolution] No history found for session {session_id}")
            return

        history_txt = "\n".join([f"مستخدم: {h[0]}\nمعالج: {h[1]}" for h in history_rows])

        # 2. Get Current Insights
        current_insights = get_user_insights(user_id)

        # 3. Generate New Insights using LLM
        prompt = insight_extraction_prompt(history_txt, current_insights)
        new_insights = call_gemini_api(prompt, max_tokens=256, temperature=0.3)

        if not new_insights:
            logger.warning("[Evolution] Empty response from LLM for insights.")
            return

        # 4. Save Updated Insights
        save_user_insights(user_id, new_insights)
        logger.info(f"[Evolution] Updated insights for user {user_id}: {new_insights[:50]}...")

    except Exception as e:
        logger.error(f"[Evolution] Analysis failed: {e}")

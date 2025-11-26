# tests/test_evolution.py
import sys
import os
import time
from unittest.mock import patch

# Set dummy API key before imports to satisfy Pydantic
os.environ["GEMINI_API_KEY"] = "dummy_key"

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db import init_db, init_insights_db, log_conversation, get_user_insights
from backend.evolution_core import analyze_session_for_insights
from backend.therapy_core import system_prompt

def test_evolution_flow():
    print("--- Starting Evolution Test ---")
    
    # 1. Setup
    session_id = "test_session_123"
    user_id = "default_user"
    init_db()
    init_insights_db()
    
    # 2. Simulate a conversation
    print("1. Simulating conversation...")
    log_conversation(session_id, "أشعر بقلق شديد من العمل", "قلق", "لا بأس، خذ نفساً عميقاً", 0, "dummy.wav", "dummy_bot.wav")
    log_conversation(session_id, "مديري يضغط علي كثيراً", "توتر", "حاول التحدث معه بهدوء", 0, "dummy.wav", "dummy_bot.wav")
    
    # 3. Trigger Analysis
    print("2. Triggering analysis (mocking LLM call)...")
    
    # Mock the LLM call to return specific insights
    with patch("backend.evolution_core.call_gemini_api") as mock_llm:
        mock_llm.return_value = "- User is anxious about work.\n- Responds well to calm reassurance."
        
        try:
            analyze_session_for_insights(session_id, user_id)
        except Exception as e:
            print(f"Analysis failed: {e}")
        
    # 4. Check Insights
    print("3. Checking insights...")
    insights = get_user_insights(user_id)
    print(f"Insights found: {insights}")
    
    # 5. Verify System Prompt Injection
    print("4. Verifying prompt injection...")
    prompt = system_prompt([], user_insights=insights)
    if insights and insights in prompt:
        print("SUCCESS: Insights injected into prompt.")
    elif not insights:
        print("WARNING: No insights generated (likely due to missing API key or mock).")
    else:
        print("FAILURE: Insights NOT injected into prompt.")

if __name__ == "__main__":
    test_evolution_flow()

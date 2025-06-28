# backend/db.py

import os
import sqlite3
from datetime import datetime
from typing import List, Tuple, Optional
import logging

from backend.config import get_settings

settings = get_settings()
logger = logging.getLogger("db")
logger.setLevel(logging.INFO)

DATA_DIR = settings.DATA_DIR
DB_PATH = os.path.join(DATA_DIR, "session_logs.db")
os.makedirs(DATA_DIR, exist_ok=True)


# --- DB Initialization ---
def init_db():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                transcript TEXT NOT NULL,
                emotion TEXT NOT NULL,
                bot_response TEXT NOT NULL,
                crisis_flag INTEGER NOT NULL,
                audio_path TEXT NOT NULL,
                bot_audio_path TEXT NOT NULL
            )""")
            conn.commit()
        logger.info("[DB] Initialized and table ready.")
    except Exception as e:
        logger.error(f"[DB] Initialization failed: {e}")


init_db()


# --- Conversation Logging ---
def log_conversation(
        session_id: str,
        transcript: str,
        emotion: str,
        bot_response: str,
        crisis_flag: int,
        audio_path: str,
        bot_audio_path: str
) -> None:
    """Log a conversation turn. Returns None on success; logs errors."""
    try:
        timestamp = datetime.utcnow().isoformat()
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO sessions (
                    session_id, timestamp, transcript, emotion,
                    bot_response, crisis_flag, audio_path, bot_audio_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, timestamp, transcript, emotion,
                bot_response, crisis_flag, audio_path, bot_audio_path
            ))
            conn.commit()
        logger.info(f"[DB] Logged turn for session {session_id}.")
    except Exception as e:
        logger.error(f"[DB] Logging failed: {e}")


# --- Retrieve History ---
def get_history(session_id: str, limit: int = 50) -> List[Tuple[str, str]]:
    """
    Retrieve conversation turns for the given session, ordered by timestamp.
    Returns List of (transcript, bot_response).
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT transcript, bot_response
                FROM sessions
                WHERE session_id = ?
                ORDER BY timestamp ASC
                LIMIT ?
            """, (session_id, limit))
            rows = cur.fetchall()
        logger.info(f"[DB] Retrieved {len(rows)} turns for session {session_id}.")
        return rows
    except Exception as e:
        logger.error(f"[DB] get_history failed: {e}")
        return []


# --- Optional: Export Session (for Analytics) ---
def export_session(session_id: str) -> Optional[List[dict]]:
    """Export full session data as a list of dicts (for future analytics/UI)."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM sessions
                WHERE session_id = ?
                ORDER BY timestamp ASC
            """, (session_id,))
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
        result = [dict(zip(cols, row)) for row in rows]
        logger.info(f"[DB] Exported session {session_id}, {len(result)} rows.")
        return result
    except Exception as e:
        logger.error(f"[DB] export_session failed: {e}")
        return None

# backend/config.py

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, HttpUrl
from typing import List


class Settings(BaseSettings):
    GEMINI_API_KEY: str = Field(..., description="Google Gemini API key")
    FRONTEND_URL: HttpUrl = Field("http://localhost:8501", description="Streamlit frontend URL")
    DATA_DIR: str = Field("data", description="Base directory for storing audio and DB files")
    ALLOWED_ORIGINS: List[str] = Field(["http://localhost:8501"], description="CORS allowed origins")
    APP_ENV: str = Field("dev", description="Application environment: dev, staging, prod")
    DEBUG: bool = Field(False, description="Enable debug logging and verbose error reporting")
    LOG_LEVEL: str = Field("INFO", description="Python logging level")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


@lru_cache
def get_settings() -> Settings:
    """
    Cached getter for app settings, loaded once per process.
    Use anywhere: `from config import get_settings; settings = get_settings()`
    """
    return Settings()

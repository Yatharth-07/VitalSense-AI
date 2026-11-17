from __future__ import annotations

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "VitalSense AI"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "127.0.0.1"

    # Database
    DATABASE_URL: str = "sqlite:///./vitalsense.db"

    # AI Integration
    AI_PROVIDER: str = "mock"  # "mock" | "gemini" | "external"
    AI_API_KEY: Optional[str] = None
    AI_API_URL: str = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    AI_REQUEST_TIMEOUT: float = 8.0

    # Clinical Validation Ranges (Permissive numeric validation limits)
    GLUCOSE_MIN: float = 10.0
    GLUCOSE_MAX: float = 1000.0
    HAEMOGLOBIN_MIN: float = 1.0
    HAEMOGLOBIN_MAX: float = 35.0
    CHOLESTEROL_MIN: float = 20.0
    CHOLESTEROL_MAX: float = 1500.0

    # Frontend connection
    API_BASE_URL: str = "http://127.0.0.1:8000/api"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

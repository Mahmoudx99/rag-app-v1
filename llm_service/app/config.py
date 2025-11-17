"""
LLM Service Configuration
"""
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """LLM Service settings with environment variable support"""

    # Service settings
    SERVICE_NAME: str = "LLM Service"
    SERVICE_VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8001

    # LLM Provider settings
    LLM_PROVIDER: str = "gemini"  # gemini, openai, ollama
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gemini-2.0-flash"
    LLM_BASE_URL: Optional[str] = None  # For local models like Ollama

    # Generation settings
    LLM_MAX_TOKENS: int = 4096
    LLM_TEMPERATURE: float = 0.7
    LLM_TOP_P: float = 0.9
    LLM_TOP_K: int = 40

    # Timeout settings
    LLM_TIMEOUT: int = 60  # seconds

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

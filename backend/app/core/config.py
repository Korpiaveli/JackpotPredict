"""
Configuration module for JackpotPredict.

Manages LLM API settings with support for:
- Local inference (TabbyAPI with Qwen 2.5 32B)
- Google Gemini API (RECOMMENDED - 1,500 free requests/day)
- OpenAI API (alternative - $5 free credits)
- Ollama fallback

Settings are loaded from environment variables and .env file.
"""

from typing import Literal, Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable loading."""

    # LLM Mode: "local" | "gemini" | "openai"
    LLM_MODE: Literal["local", "gemini", "openai"] = "local"

    # Google Gemini API (RECOMMENDED - 1,500 free requests/day)
    # Get key at: https://aistudio.google.com/app/apikey
    GEMINI_API_KEY: str = ""
    GEMINI_API_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # OpenAI API (alternative - $5 free credits)
    # Get key at: https://platform.openai.com/api-keys
    OPENAI_API_KEY: str = ""
    OPENAI_API_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Local inference (TabbyAPI)
    TABBY_API_URL: str = "http://127.0.0.1:5000/v1"
    TABBY_MODEL: str = "Qwen2.5-32B-Instruct-4.0bpw-exl2"

    # Ollama fallback
    OLLAMA_API_URL: str = "http://127.0.0.1:11434/v1"
    OLLAMA_MODEL: str = "qwen2.5:14b"

    # Inference settings
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 200
    LLM_TIMEOUT: int = 30  # seconds

    # Enable hybrid mode (LLM + Bayesian)
    ENABLE_HYBRID: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Cloud API configurations for easy access
CLOUD_CONFIGS = {
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-2.0-flash",
        "api_key_env": "GEMINI_API_KEY",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "api_key_env": "OPENAI_API_KEY",
    },
}


def get_active_llm_config() -> dict:
    """
    Get the active LLM configuration based on settings.

    Returns:
        dict with keys: base_url, model, api_key, mode
    """
    settings = get_settings()
    mode = settings.LLM_MODE

    if mode == "gemini" and settings.GEMINI_API_KEY:
        return {
            "base_url": settings.GEMINI_API_URL,
            "model": settings.GEMINI_MODEL,
            "api_key": settings.GEMINI_API_KEY,
            "mode": "gemini",
            "is_cloud": True,
        }
    elif mode == "openai" and settings.OPENAI_API_KEY:
        return {
            "base_url": settings.OPENAI_API_URL,
            "model": settings.OPENAI_MODEL,
            "api_key": settings.OPENAI_API_KEY,
            "mode": "openai",
            "is_cloud": True,
        }
    else:
        # Default to local TabbyAPI
        return {
            "base_url": settings.TABBY_API_URL,
            "model": settings.TABBY_MODEL,
            "api_key": None,  # No auth for local
            "mode": "local",
            "is_cloud": False,
        }


def get_fallback_config() -> dict:
    """
    Get Ollama fallback configuration.

    Returns:
        dict with keys: base_url, model, api_key, mode
    """
    settings = get_settings()
    return {
        "base_url": settings.OLLAMA_API_URL,
        "model": settings.OLLAMA_MODEL,
        "api_key": None,
        "mode": "ollama",
        "is_cloud": False,
    }

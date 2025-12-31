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
from pathlib import Path

# Get the absolute path to .env file (relative to this config.py file)
_ENV_FILE = Path(__file__).parent.parent.parent / ".env"


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

    # OpenAI Validator Settings (parallel validation with Gemini)
    OPENAI_VALIDATOR_ENABLED: bool = True
    VALIDATOR_TIMEOUT: int = 8  # seconds - shorter than main LLM timeout

    # Groq API (Llama 3.3 70B - FREE tier)
    # Get key at: https://console.groq.com/keys
    GROQ_API_KEY: str = ""
    GROQ_API_URL: str = "https://api.groq.com/openai/v1"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Anthropic API (Claude 3.5 Sonnet for Oracle meta-synthesizer)
    # Get key at: https://console.anthropic.com/settings/keys
    ANTHROPIC_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"

    # Agent orchestration settings
    AGENT_TIMEOUT: int = 5  # seconds per agent
    ENABLE_MOA: bool = True  # Enable Mixture of Agents

    class Config:
        env_file = str(_ENV_FILE)
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
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "api_key_env": "GROQ_API_KEY",
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


def get_openai_validator_config() -> dict:
    """
    Get OpenAI validator configuration for parallel validation.

    Returns:
        dict with keys: base_url, model, api_key, enabled, timeout
    """
    settings = get_settings()
    return {
        "base_url": settings.OPENAI_API_URL,
        "model": settings.OPENAI_MODEL,
        "api_key": settings.OPENAI_API_KEY,
        "enabled": settings.OPENAI_VALIDATOR_ENABLED and bool(settings.OPENAI_API_KEY),
        "timeout": settings.VALIDATOR_TIMEOUT,
    }


def get_groq_config() -> dict:
    """
    Get Groq API configuration for Llama 3.3 70B.

    Returns:
        dict with keys: base_url, model, api_key, enabled, timeout
    """
    settings = get_settings()
    return {
        "base_url": settings.GROQ_API_URL,
        "model": settings.GROQ_MODEL,
        "api_key": settings.GROQ_API_KEY,
        "enabled": bool(settings.GROQ_API_KEY),
        "timeout": settings.AGENT_TIMEOUT,
    }


def get_oracle_config() -> dict:
    """
    Get Anthropic API configuration for Oracle (Claude 3.5 Sonnet).

    Returns:
        dict with keys: model, api_key, enabled, timeout
    """
    settings = get_settings()
    return {
        "model": settings.CLAUDE_MODEL,
        "api_key": settings.ANTHROPIC_API_KEY,
        "enabled": bool(settings.ANTHROPIC_API_KEY),
        "timeout": settings.AGENT_TIMEOUT,
    }


def get_agent_configs() -> dict:
    """
    Get configurations for all 5 specialized agents.

    Returns:
        dict mapping agent_name to config dict
    """
    settings = get_settings()

    return {
        "lateral": {
            "base_url": settings.OPENAI_API_URL,
            "model": settings.OPENAI_MODEL,
            "api_key": settings.OPENAI_API_KEY,
            "temperature": 0.2,
            "timeout": settings.AGENT_TIMEOUT,
        },
        "wordsmith": {
            "base_url": settings.OPENAI_API_URL,
            "model": settings.OPENAI_MODEL,
            "api_key": settings.OPENAI_API_KEY,
            "temperature": 0.2,
            "timeout": settings.AGENT_TIMEOUT,
        },
        "popculture": {
            "base_url": settings.GEMINI_API_URL,
            "model": settings.GEMINI_MODEL,
            "api_key": settings.GEMINI_API_KEY,
            "temperature": 0.2,
            "timeout": settings.AGENT_TIMEOUT,
        },
        "literal": {
            "base_url": settings.GROQ_API_URL,
            "model": settings.GROQ_MODEL,
            "api_key": settings.GROQ_API_KEY,
            "temperature": 0.1,
            "timeout": settings.AGENT_TIMEOUT,
        },
        "wildcard": {
            "base_url": settings.OPENAI_API_URL,
            "model": settings.OPENAI_MODEL,
            "api_key": settings.OPENAI_API_KEY,
            "temperature": 0.9,
            "timeout": settings.AGENT_TIMEOUT,
        },
    }

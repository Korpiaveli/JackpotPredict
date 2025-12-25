"""
LLM Providers for JackpotPredict.

Supports multiple cloud and local providers:
- OpenAI (GPT-4o-mini)
- Google Gemini (Flash)
- Groq (Llama 3.3 70B)
"""

from .groq_provider import GroqProvider

__all__ = ["GroqProvider"]

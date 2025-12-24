"""
Groq Provider - Ultra-fast inference with Llama 3.3 70B.

Groq provides free tier access to Llama 3.3 70B with extremely low latency.
Used by the Literal agent for trap detection and face-value interpretation.

API Docs: https://console.groq.com/docs/quickstart
"""

import logging
from typing import Optional, List, Dict, Any
import httpx

from app.core.config import get_groq_config

logger = logging.getLogger(__name__)


class GroqProvider:
    """
    Groq API provider for Llama 3.3 70B inference.

    Features:
    - OpenAI-compatible API
    - Ultra-fast inference (~200ms typical)
    - Free tier: 30 requests/minute, 14,400/day
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 5
    ):
        """
        Initialize Groq provider.

        Args:
            api_key: Groq API key (or from env)
            base_url: API base URL (or from config)
            model: Model name (or from config)
            timeout: Request timeout in seconds
        """
        config = get_groq_config()

        self.api_key = api_key or config["api_key"]
        self.base_url = (base_url or config["base_url"]).rstrip("/")
        self.model = model or config["model"]
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def is_available(self) -> bool:
        """Check if Groq is configured with API key."""
        return bool(self.api_key)

    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy-initialize the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
            )
        return self._client

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 150,
    ) -> Optional[str]:
        """
        Make a chat completion request to Groq.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum response tokens

        Returns:
            Response content string or None if failed
        """
        if not self.is_available:
            logger.warning("[Groq] API key not configured")
            return None

        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            return data["choices"][0]["message"]["content"].strip()

        except httpx.TimeoutException:
            logger.warning(f"[Groq] Timeout after {self.timeout}s")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"[Groq] HTTP error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"[Groq] Error: {e}")
            return None

    async def health_check(self) -> bool:
        """
        Verify Groq API is reachable.

        Returns:
            True if API responds, False otherwise
        """
        if not self.is_available:
            return False

        try:
            # Simple models list request
            response = await self.client.get(f"{self.base_url}/models")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"[Groq] Health check failed: {e}")
            return False

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton instance for convenience
_groq_provider: Optional[GroqProvider] = None


def get_groq_provider() -> GroqProvider:
    """Get or create singleton Groq provider instance."""
    global _groq_provider
    if _groq_provider is None:
        _groq_provider = GroqProvider()
    return _groq_provider

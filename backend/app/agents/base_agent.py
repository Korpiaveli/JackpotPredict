"""
Base Agent - Abstract interface for all specialized prediction agents.

Each agent implements a unique reasoning style optimized for different clue types.
All agents return predictions in a standardized format for voting.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
import logging
import time
import httpx

logger = logging.getLogger(__name__)


@dataclass
class AgentPrediction:
    """Standardized prediction from any agent."""
    answer: str
    confidence: float  # 0.0 to 1.0
    reasoning: str  # Brief 2-4 word explanation
    agent_name: str
    latency_ms: float


class BaseAgent(ABC):
    """
    Abstract base class for specialized prediction agents.

    Each agent has:
    - A unique name and emoji
    - A specialized system prompt
    - A specific LLM provider (OpenAI, Gemini, Groq)
    - A temperature setting
    """

    # Override in subclasses
    AGENT_NAME: str = "base"
    AGENT_EMOJI: str = ""
    TEMPERATURE: float = 0.2

    def __init__(self, api_key: str, base_url: str, model: str, timeout: int = 5):
        """
        Initialize agent with LLM configuration.

        Args:
            api_key: API key for the LLM provider
            base_url: Base URL for the API (OpenAI-compatible)
            model: Model name/ID
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

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

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the specialized system prompt for this agent."""
        pass

    def format_clues_message(self, clues: List[str], category_hint: Optional[str] = None) -> str:
        """Format clues for the user message."""
        lines = []

        if category_hint:
            lines.append(f"[Category hint: {category_hint.upper()}]")
            lines.append("")

        lines.append("CLUES REVEALED:")
        for i, clue in enumerate(clues, 1):
            lines.append(f'  Clue {i}: "{clue}"')

        lines.append("")
        lines.append(f"We are on Clue {len(clues)} of 5.")
        lines.append("Provide your prediction.")

        return "\n".join(lines)

    async def predict(
        self,
        clues: List[str],
        category_hint: Optional[str] = None
    ) -> Optional[AgentPrediction]:
        """
        Make a prediction based on the clues.

        Args:
            clues: List of clues revealed so far
            category_hint: Optional category hint (person/place/thing)

        Returns:
            AgentPrediction or None if failed
        """
        start_time = time.time()

        try:
            # Build request
            messages = [
                {"role": "system", "content": self.get_system_prompt()},
                {"role": "user", "content": self.format_clues_message(clues, category_hint)}
            ]

            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": self.TEMPERATURE,
                "max_tokens": 150,
            }

            # Make request
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()

            # Parse response
            prediction = self.parse_response(content)
            if prediction:
                prediction.latency_ms = (time.time() - start_time) * 1000
                prediction.agent_name = self.AGENT_NAME
                return prediction

            logger.warning(f"[{self.AGENT_NAME}] Failed to parse response: {content[:100]}")
            return None

        except httpx.TimeoutException:
            logger.warning(f"[{self.AGENT_NAME}] Timeout after {self.timeout}s")
            return None
        except Exception as e:
            logger.error(f"[{self.AGENT_NAME}] Error: {e}")
            return None

    def parse_response(self, content: str) -> Optional[AgentPrediction]:
        """
        Parse the LLM response into an AgentPrediction.

        Expected format:
        ANSWER: <answer>
        CONFIDENCE: <0-100>
        REASONING: <brief explanation>

        Returns:
            AgentPrediction or None if parsing fails
        """
        import re

        try:
            # Extract answer
            answer_match = re.search(r'ANSWER:\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
            if not answer_match:
                return None
            answer = answer_match.group(1).strip()

            # Extract confidence
            conf_match = re.search(r'CONFIDENCE:\s*(\d+(?:\.\d+)?)', content, re.IGNORECASE)
            confidence = float(conf_match.group(1)) / 100 if conf_match else 0.5
            confidence = max(0.0, min(1.0, confidence))  # Clamp to 0-1

            # Extract reasoning
            reason_match = re.search(r'REASONING:\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
            reasoning = reason_match.group(1).strip()[:50] if reason_match else "No reasoning"

            return AgentPrediction(
                answer=answer,
                confidence=confidence,
                reasoning=reasoning,
                agent_name=self.AGENT_NAME,
                latency_ms=0.0  # Will be set by caller
            )

        except Exception as e:
            logger.error(f"[{self.AGENT_NAME}] Parse error: {e}")
            return None

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

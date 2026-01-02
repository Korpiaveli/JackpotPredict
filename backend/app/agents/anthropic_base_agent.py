"""
Anthropic Base Agent - Base class for agents using Claude models via Anthropic API.

Uses the native Anthropic SDK instead of OpenAI-compatible endpoints.
"""

from abc import abstractmethod
from typing import List, Optional
import logging
import time
import re

from anthropic import AsyncAnthropic

from .base_agent import AgentPrediction

logger = logging.getLogger(__name__)


class AnthropicBaseAgent:
    """
    Base class for agents using Anthropic's Claude models.

    Uses the native Anthropic SDK (not OpenAI-compatible format).
    """

    AGENT_NAME: str = "anthropic_base"
    AGENT_EMOJI: str = ""
    TEMPERATURE: float = 0.2

    def __init__(self, api_key: str, model: str, timeout: int = 5):
        """
        Initialize agent with Anthropic configuration.

        Args:
            api_key: Anthropic API key
            model: Model name (e.g., "claude-3-5-haiku-20241022")
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self._client: Optional[AsyncAnthropic] = None

    @property
    def client(self) -> AsyncAnthropic:
        """Lazy-initialize the Anthropic client."""
        if self._client is None:
            self._client = AsyncAnthropic(
                api_key=self.api_key,
                timeout=self.timeout
            )
        return self._client

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the specialized system prompt for this agent."""
        pass

    def format_clues_message(
        self,
        clues: List[str],
        category_hint: Optional[str] = None,
        prior_context: Optional[str] = None,
        theme: Optional[str] = None
    ) -> str:
        """Format clues for the user message."""
        lines = []

        if theme:
            lines.append(f"TONIGHT'S THEME/SPONSOR: {theme}")
            lines.append("(The answer may or may not relate to this theme - use as a hint only)")
            lines.append("")

        if prior_context:
            lines.append(prior_context)
            lines.append("")

        if category_hint:
            lines.append(f"[Category hint: {category_hint.upper()}]")
            lines.append("")

        lines.append("CLUES REVEALED:")
        for i, clue in enumerate(clues, 1):
            lines.append(f'  Clue {i}: "{clue}"')

        lines.append("")
        lines.append(f"We are on Clue {len(clues)} of 5.")

        if prior_context:
            lines.append("Consider prior analysis. Confirm, refine, or challenge your position.")
        else:
            lines.append("Provide your prediction.")

        return "\n".join(lines)

    async def predict(
        self,
        clues: List[str],
        category_hint: Optional[str] = None,
        prior_context: Optional[str] = None,
        theme: Optional[str] = None
    ) -> Optional[AgentPrediction]:
        """
        Make a prediction using Claude via Anthropic API.

        Args:
            clues: List of clues revealed so far
            category_hint: Optional category hint
            prior_context: Optional context from prior analysis
            theme: Optional theme/sponsor context

        Returns:
            AgentPrediction or None if failed
        """
        start_time = time.time()

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=150,
                temperature=self.TEMPERATURE,
                system=self.get_system_prompt(),
                messages=[{
                    "role": "user",
                    "content": self.format_clues_message(clues, category_hint, prior_context, theme)
                }]
            )

            content = response.content[0].text.strip()
            logger.debug(f"[{self.AGENT_NAME}] Raw response: {content[:200]}")

            prediction = self.parse_response(content)
            if prediction:
                prediction.latency_ms = (time.time() - start_time) * 1000
                prediction.agent_name = self.AGENT_NAME
                return prediction

            logger.warning(f"[{self.AGENT_NAME}] Failed to parse response: {content}")
            return None

        except Exception as e:
            logger.error(f"[{self.AGENT_NAME}] Error ({type(e).__name__}): {e}")
            return None

    def parse_response(self, content: str) -> Optional[AgentPrediction]:
        """
        Parse the LLM response into an AgentPrediction.

        Expected format:
        ANSWER: <answer>
        CONFIDENCE: <0-100>
        REASONING: <brief explanation>
        """
        try:
            answer_match = re.search(r"ANSWER:\s*(.+?)(?:\n|$)", content, re.IGNORECASE)
            conf_match = re.search(r"CONFIDENCE:\s*(\d+)", content, re.IGNORECASE)
            reason_match = re.search(r"REASONING:\s*(.+?)(?:\n|$)", content, re.IGNORECASE)

            if not answer_match or not conf_match:
                return None

            answer = answer_match.group(1).strip().strip('"\'')
            confidence = int(conf_match.group(1)) / 100.0
            confidence = max(0.0, min(1.0, confidence))
            reasoning = reason_match.group(1).strip() if reason_match else "No reasoning"

            return AgentPrediction(
                answer=answer,
                confidence=confidence,
                reasoning=reasoning[:50],
                agent_name=self.AGENT_NAME,
                latency_ms=0.0
            )

        except Exception as e:
            logger.error(f"[{self.AGENT_NAME}] Parse error: {e}")
            return None

    async def close(self):
        """Close the client."""
        self._client = None

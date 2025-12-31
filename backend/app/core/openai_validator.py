"""
OpenAI Validator - Secondary AI validation for Gemini predictions.

This module provides parallel validation of Gemini's predictions using
GPT-4o-mini. It uses a simpler, validation-focused prompt rather than
full trivia analysis.

The validator:
1. Checks if Gemini's top prediction makes sense given the clues
2. Provides an alternative prediction if it disagrees
3. Returns a confidence score for its assessment
"""

import asyncio
import json
import logging
from typing import Optional, List
from dataclasses import dataclass

from openai import AsyncOpenAI

from app.core.config import get_openai_validator_config

logger = logging.getLogger(__name__)


# Simplified validation prompt - focused on validation, not full prediction
VALIDATOR_PROMPT = """You are validating a trivia answer for Netflix's "Best Guess Live" game.

The game reveals 5 progressive clues about a Person, Place, or Thing.
Players must guess exactly - spelling matters!

CLUES REVEALED SO FAR:
{clues}

THE PRIMARY AI PREDICTS: "{prediction}"
(confidence: {confidence}%)

YOUR TASK:
1. Does this prediction make sense given the clues?
2. If you disagree, what would YOU guess instead?

Think about:
- Do the clues point to this answer?
- Are there wordplay/puns that support or contradict this?
- Is there a better answer that fits ALL clues?

RESPOND IN JSON ONLY (no markdown):
{{
  "agrees": true or false,
  "alternative": "Your guess if you disagree, or null if you agree",
  "confidence": 0.0 to 1.0 (how confident are you in your assessment),
  "reasoning": "Brief explanation (max 50 words)"
}}"""


@dataclass
class ValidationResult:
    """Result from OpenAI validation."""
    agrees: bool
    alternative: Optional[str]
    confidence: float
    reasoning: str
    raw_response: str = ""
    error: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        """Check if validation completed successfully."""
        return self.error is None


class OpenAIValidator:
    """
    Secondary AI validator using GPT-4o-mini.

    Validates Gemini's predictions by checking if they make sense
    given the clues, and provides alternatives when it disagrees.
    """

    TEMPERATURE = 0.1  # Low for consistency
    MAX_TOKENS = 200   # Short responses only

    def __init__(self):
        config = get_openai_validator_config()
        self.enabled = config["enabled"]
        self.api_key = config["api_key"]
        self.base_url = config["base_url"]
        self.model = config["model"]
        self.timeout = config["timeout"]
        self._client: Optional[AsyncOpenAI] = None
        self._available: Optional[bool] = None

    async def _get_client(self) -> Optional[AsyncOpenAI]:
        """Get or create AsyncOpenAI client."""
        if not self.enabled or not self.api_key:
            return None
        if self._client is None:
            self._client = AsyncOpenAI(
                base_url=self.base_url,
                api_key=self.api_key
            )
        return self._client

    async def is_available(self) -> bool:
        """Check if OpenAI validator is available."""
        if self._available is not None:
            return self._available

        if not self.enabled or not self.api_key:
            logger.info("OpenAI validator disabled or no API key")
            self._available = False
            return False

        try:
            client = await self._get_client()
            if client:
                self._available = True
                logger.info("OpenAI validator available")
                return True
        except Exception as e:
            logger.warning(f"OpenAI validator not available: {e}")
            self._available = False

        return False

    async def validate(
        self,
        clues: List[str],
        prediction: str,
        confidence: float
    ) -> ValidationResult:
        """
        Validate a prediction using GPT-4o-mini.

        Args:
            clues: List of clues seen so far
            prediction: Gemini's top prediction
            confidence: Gemini's confidence (0-1)

        Returns:
            ValidationResult with agreement status and optional alternative
        """
        if not await self.is_available():
            return ValidationResult(
                agrees=True,  # Default to agreement if unavailable
                alternative=None,
                confidence=0.0,
                reasoning="Validator unavailable",
                error="OpenAI validator not available"
            )

        client = await self._get_client()
        if not client:
            return ValidationResult(
                agrees=True,
                alternative=None,
                confidence=0.0,
                reasoning="No client",
                error="Client initialization failed"
            )

        # Format clues for prompt
        clues_text = "\n".join(f"  Clue {i+1}: \"{c}\"" for i, c in enumerate(clues))

        prompt = VALIDATOR_PROMPT.format(
            clues=clues_text,
            prediction=prediction,
            confidence=int(confidence * 100)
        )

        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=self.MAX_TOKENS,
                    temperature=self.TEMPERATURE
                ),
                timeout=self.timeout
            )

            if response.choices:
                text = response.choices[0].message.content
                logger.debug(f"OpenAI validation response: {text[:200]}")
                return self._parse_response(text)

        except asyncio.TimeoutError:
            logger.warning(f"OpenAI validation timed out after {self.timeout}s")
            return ValidationResult(
                agrees=True,
                alternative=None,
                confidence=0.0,
                reasoning="Validation timed out",
                error="Timeout"
            )
        except Exception as e:
            logger.error(f"OpenAI validation error: {e}")
            return ValidationResult(
                agrees=True,
                alternative=None,
                confidence=0.0,
                reasoning=str(e),
                error=str(e)
            )

        return ValidationResult(
            agrees=True,
            alternative=None,
            confidence=0.0,
            reasoning="No response",
            error="Empty response"
        )

    def _parse_response(self, text: str) -> ValidationResult:
        """Parse JSON response from validator."""
        try:
            # Clean up response - remove markdown code blocks if present
            clean_text = text.strip()
            if clean_text.startswith("```"):
                # Remove markdown code block
                lines = clean_text.split("\n")
                clean_text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

            # Find JSON boundaries
            json_start = clean_text.find('{')
            json_end = clean_text.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = clean_text[json_start:json_end]
                data = json.loads(json_str)

                return ValidationResult(
                    agrees=data.get("agrees", True),
                    alternative=data.get("alternative"),
                    confidence=min(1.0, max(0.0, float(data.get("confidence", 0.5)))),
                    reasoning=str(data.get("reasoning", ""))[:200],
                    raw_response=text
                )

        except json.JSONDecodeError as e:
            logger.warning(f"Validator JSON parse error: {e}")
            logger.debug(f"Raw response: {text}")
        except Exception as e:
            logger.warning(f"Validator parse error: {e}")

        # Fallback - try to extract agreement from text
        agrees = "agree" in text.lower() and "disagree" not in text.lower()

        return ValidationResult(
            agrees=agrees,
            alternative=None,
            confidence=0.0,
            reasoning="Parse error - defaulting to text analysis",
            raw_response=text,
            error="JSON parse failed"
        )


# Singleton instance
_validator: Optional[OpenAIValidator] = None


async def get_openai_validator() -> OpenAIValidator:
    """Get singleton OpenAI validator instance."""
    global _validator
    if _validator is None:
        _validator = OpenAIValidator()
    return _validator

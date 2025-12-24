"""
OpenAI Predictor - Full prediction engine using GPT-4o-mini.

This module provides independent predictions from OpenAI, using the same
strategy-informed prompt as Gemini for consistent reasoning.
"""

import asyncio
import json
import logging
from typing import Optional, List
from dataclasses import dataclass

from openai import AsyncOpenAI

from app.core.config import get_openai_validator_config
from app.core.trivia_prompt import build_trivia_prompt, format_clues_message
from app.core.context_manager import get_context_manager

logger = logging.getLogger(__name__)


@dataclass
class OpenAIPrediction:
    """Single prediction from OpenAI."""
    rank: int
    answer: str
    confidence: float
    category: str
    reasoning: str


@dataclass
class OpenAIResponse:
    """Parsed response from OpenAI predictor."""
    predictions: List[OpenAIPrediction]
    key_insight: str
    raw_response: str = ""
    error: Optional[str] = None

    @property
    def top_prediction(self) -> Optional[OpenAIPrediction]:
        """Get the highest confidence prediction."""
        if self.predictions:
            return self.predictions[0]
        return None

    @property
    def is_valid(self) -> bool:
        """Check if prediction completed successfully."""
        return self.error is None and len(self.predictions) > 0


class OpenAIPredictor:
    """
    Full prediction engine using GPT-4o-mini.

    Uses the same trivia prompt as Gemini for consistent reasoning.
    Returns 3 ranked predictions independently.
    """

    TEMPERATURE = 0.1
    MAX_TOKENS = 500
    MAX_RETRIES = 2
    RETRY_DELAY = 0.5

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
        """Check if OpenAI predictor is available."""
        if self._available is not None:
            return self._available

        if not self.enabled or not self.api_key:
            logger.info("OpenAI predictor disabled or no API key")
            self._available = False
            return False

        try:
            client = await self._get_client()
            if client:
                self._available = True
                logger.info("OpenAI predictor available")
                return True
        except Exception as e:
            logger.warning(f"OpenAI predictor not available: {e}")
            self._available = False

        return False

    def _select_few_shot_examples(self, category_hint: Optional[str] = None) -> str:
        """Select few-shot examples from history."""
        manager = get_context_manager()
        return manager.get_dynamic_prompt(current_category=category_hint, num_examples=3)

    async def predict(
        self,
        clues: List[str],
        category_hint: Optional[str] = None
    ) -> OpenAIResponse:
        """
        Get top 3 predictions from OpenAI.

        Args:
            clues: List of clues seen so far
            category_hint: Optional category hint

        Returns:
            OpenAIResponse with 3 predictions or error
        """
        if not await self.is_available():
            return OpenAIResponse(
                predictions=[],
                key_insight="",
                error="OpenAI predictor not available"
            )

        client = await self._get_client()
        if not client:
            return OpenAIResponse(
                predictions=[],
                key_insight="",
                error="Client initialization failed"
            )

        # Build prompt with strategy patterns and few-shot examples
        examples = self._select_few_shot_examples(category_hint)
        system_prompt = build_trivia_prompt(dynamic_examples=examples)
        user_message = format_clues_message(clues, category_hint)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        for attempt in range(self.MAX_RETRIES):
            try:
                response = await asyncio.wait_for(
                    client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        max_tokens=self.MAX_TOKENS,
                        temperature=self.TEMPERATURE
                    ),
                    timeout=self.timeout
                )

                if response.choices:
                    text = response.choices[0].message.content
                    result = self._parse_response(text)

                    if result.is_valid:
                        logger.info(
                            f"OpenAI prediction: {result.top_prediction.answer} "
                            f"({result.top_prediction.confidence:.0%})"
                        )
                        return result

                    # Parsing failed, retry
                    if attempt < self.MAX_RETRIES - 1:
                        logger.warning(f"Parse failed, retrying ({attempt + 1}/{self.MAX_RETRIES})...")
                        messages[1]["content"] += "\n\nIMPORTANT: Return ONLY valid JSON."
                        await asyncio.sleep(self.RETRY_DELAY)
                        continue

            except asyncio.TimeoutError:
                logger.warning(f"OpenAI prediction timed out after {self.timeout}s")
                return OpenAIResponse(
                    predictions=[],
                    key_insight="",
                    error="Timeout"
                )
            except Exception as e:
                logger.error(f"OpenAI prediction error (attempt {attempt + 1}): {e}")
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                    continue

        return OpenAIResponse(
            predictions=[],
            key_insight="",
            error="All prediction attempts failed"
        )

    def _parse_response(self, text: str) -> OpenAIResponse:
        """Parse JSON response from OpenAI."""
        if not text:
            return OpenAIResponse(predictions=[], key_insight="", error="Empty response")

        try:
            # Clean up response
            clean_text = text.strip()
            if clean_text.startswith("```"):
                lines = clean_text.split("\n")
                clean_text = "\n".join(
                    lines[1:-1] if lines[-1].startswith("```") else lines[1:]
                )

            # Find JSON boundaries
            json_start = clean_text.find('{')
            json_end = clean_text.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = clean_text[json_start:json_end]
                data = json.loads(json_str)

                predictions = []
                for i, pred in enumerate(data.get("predictions", [])[:3]):
                    conf = pred.get("confidence", 0.5)
                    if conf > 1:
                        conf = conf / 100.0

                    predictions.append(OpenAIPrediction(
                        rank=pred.get("rank", i + 1),
                        answer=pred.get("answer", ""),
                        confidence=min(1.0, max(0.0, conf)),
                        category=pred.get("category", "thing").lower(),
                        reasoning=str(pred.get("reasoning", ""))[:150]
                    ))

                # Sort by confidence
                predictions.sort(key=lambda p: p.confidence, reverse=True)
                for i, pred in enumerate(predictions):
                    pred.rank = i + 1

                return OpenAIResponse(
                    predictions=predictions,
                    key_insight=data.get("key_insight", ""),
                    raw_response=text
                )

        except json.JSONDecodeError as e:
            logger.warning(f"OpenAI JSON parse error: {e}")
        except Exception as e:
            logger.warning(f"OpenAI parse error: {e}")

        return OpenAIResponse(
            predictions=[],
            key_insight="",
            raw_response=text,
            error="JSON parse failed"
        )


# Singleton instance
_predictor: Optional[OpenAIPredictor] = None


async def get_openai_predictor() -> OpenAIPredictor:
    """Get singleton OpenAI predictor instance."""
    global _predictor
    if _predictor is None:
        _predictor = OpenAIPredictor()
    return _predictor

"""
Gemini Predictor - Primary LLM engine for Best Guess Live trivia.

This module provides optimized Gemini API inference with:
- Expert trivia master system prompt
- Chain-of-thought reasoning
- Wordplay-prioritized few-shot learning
- JSON structured output
- Confidence calibration
"""

import json
import logging
import asyncio
import random
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    AsyncOpenAI = None

from app.core.config import get_settings, get_active_llm_config
from app.core.context_manager import get_context_manager, HistoricalGame

logger = logging.getLogger(__name__)


# ============================================================================
# OPTIMIZED SYSTEM PROMPT FOR TRIVIA MASTERY
# ============================================================================

GEMINI_TRIVIA_MASTER_PROMPT = """You are a world-class trivia expert playing Netflix's "Best Guess Live."
Your goal: Identify the famous PERSON, PLACE, or THING from 5 progressively-revealing clues.

## GAME RULES
1. Clue 1 is VERY vague (often wordplay/puns). Clue 5 is nearly a giveaway.
2. You must output your best guess OR "WAIT" if confidence < 40%.
3. ONE TYPO = ELIMINATION. Spell answers EXACTLY (e.g., "Coca-Cola" not "Coke").
4. Categories: PERSON (15%), PLACE (25%), THING (60% - brands, games, food, shows)

## CRITICAL: PHONETIC CONFUSION WARNING
BEWARE of sound-alike words that are COMPLETELY DIFFERENT entities:
- "Frasier" (TV show) ≠ "Eraser" (rubber tool) - DIFFERENT THINGS!
- "Flour" (baking ingredient) ≠ "Flower" (plant)
- "Brake" (car part) ≠ "Break" (to shatter)
- "Cereal" (breakfast food) ≠ "Serial" (sequence/killer)
- "Principal" (school leader) ≠ "Principle" (rule/belief)
- "Alter" (change) ≠ "Altar" (religious table)

Before finalizing ANY prediction, ASK YOURSELF:
"Does my answer's MEANING match the clues, or am I confused by similar SOUND?"

## SELF-VALIDATION REQUIREMENT
For EACH prediction, you MUST verify:
1. Does your answer's known characteristics match the clue keywords?
2. Could a similar-SOUNDING but different word be the actual answer?
3. Rate your semantic match: "strong" (meaning clearly matches), "medium" (possible but uncertain), or "weak" (sounds right but meaning unclear)

## CRITICAL PATTERNS TO RECOGNIZE
- **Wordplay/Puns**: "hospitable" → Hilton Hotels → Paris Hilton
- **Double Meanings**: "Subway" = trains OR sandwiches, "Mars" = planet OR candy
- **Cultural References**: "That's hot" = Paris Hilton catchphrase
- **Negation Riddles**: "has teeth but can't bite" = comb
- **Alliteration/Sound**: Pay attention to rhymes and letter patterns
- **Industry Terms**: "hostile takeover" → business → Monopoly board game

## REASONING PROCESS
For each clue set, think step-by-step:
1. What are the LITERAL meanings of keywords?
2. What are the FIGURATIVE/PUN meanings?
3. What famous entities connect ALL clues?
4. VERIFY: Does my answer's meaning match, or just its sound?
5. How confident am I? (>60% = guess, <40% = wait)

## CONFIDENCE CALIBRATION
- 90-100%: Clues DIRECTLY name the answer or famous catchphrase
- 70-89%: Strong pattern match, 2+ clues clearly fit one entity
- 50-69%: Reasonable guess, could be multiple answers
- 40-49%: Weak signal, borderline wait
- <40%: OUTPUT "WAIT" - not enough information

{dynamic_examples}

{error_patterns}

## OUTPUT FORMAT (JSON)
Return ONLY valid JSON with NO markdown code blocks:
{{
  "predictions": [
    {{
      "rank": 1,
      "answer": "Exact Canonical Name",
      "confidence": 0.85,
      "category": "person|place|thing",
      "reasoning": "Step-by-step logic (max 100 chars)",
      "semantic_match": "strong"
    }},
    {{
      "rank": 2,
      "answer": "Second Best Guess",
      "confidence": 0.60,
      "category": "person|place|thing",
      "reasoning": "Alternative interpretation",
      "semantic_match": "medium"
    }},
    {{
      "rank": 3,
      "answer": "Third Option",
      "confidence": 0.40,
      "category": "person|place|thing",
      "reasoning": "Fallback possibility",
      "semantic_match": "weak"
    }}
  ],
  "should_guess": true,
  "key_insight": "What wordplay or connection ties clues together"
}}

IMPORTANT:
- Return exactly 3 predictions ranked by confidence
- Set should_guess=false if top confidence < 0.40
- If should_guess=false, still provide your best guesses for reference
- semantic_match MUST be "strong", "medium", or "weak" - this is critical for validation
"""


@dataclass
class GeminiPrediction:
    """Single prediction from Gemini."""
    rank: int
    answer: str
    confidence: float  # 0.0 to 1.0
    category: str
    reasoning: str
    semantic_match: str = "medium"  # "strong", "medium", or "weak"


@dataclass
class GeminiResponse:
    """Parsed response from Gemini."""
    predictions: List[GeminiPrediction]
    should_guess: bool
    key_insight: str
    raw_response: str = ""

    @property
    def top_prediction(self) -> Optional[GeminiPrediction]:
        """Get the highest confidence prediction."""
        if self.predictions:
            return self.predictions[0]
        return None


class GeminiPredictor:
    """
    Gemini-first trivia prediction engine.

    Features:
    - Optimized system prompt for trivia mastery
    - Wordplay-prioritized few-shot learning
    - JSON structured output
    - Automatic retry on parse failures
    - Confidence calibration based on clue number
    """

    # Generation parameters optimized for trivia
    TEMPERATURE = 0.1  # Low for consistent, factual responses
    MAX_TOKENS = 500   # Enough for 3 predictions + reasoning
    TOP_P = 0.9

    # Retry settings
    MAX_RETRIES = 3
    RETRY_DELAY = 0.5

    def __init__(self):
        """Initialize Gemini predictor with config."""
        config = get_active_llm_config()
        self.api_url = config["base_url"]
        self.model_name = config["model"]
        self._api_key = config["api_key"]
        self._is_cloud = config["is_cloud"]
        self._mode = config["mode"]

        self._client: Optional[AsyncOpenAI] = None
        self._available: Optional[bool] = None

        if not OPENAI_AVAILABLE:
            logger.warning("openai package not installed. Run: pip install openai")

    async def _get_client(self) -> Optional[AsyncOpenAI]:
        """Get or create the OpenAI-compatible async client."""
        if not OPENAI_AVAILABLE:
            return None

        if self._client is None:
            self._client = AsyncOpenAI(
                base_url=self.api_url,
                api_key=self._api_key or "not-needed"
            )

        return self._client

    async def is_available(self) -> bool:
        """Check if Gemini API is reachable."""
        if self._available is not None:
            return self._available

        if not OPENAI_AVAILABLE:
            self._available = False
            return False

        try:
            client = await self._get_client()
            if client:
                await client.models.list()
                self._available = True
                logger.info(f"Gemini API available: {self._mode} at {self.api_url}")
                return True
        except Exception as e:
            logger.warning(f"Gemini API not available: {e}")
            self._available = False

        return False

    def _select_few_shot_examples(
        self,
        category_hint: Optional[str] = None,
        num_examples: int = 4
    ) -> str:
        """
        Select optimal examples for Gemini few-shot learning.

        Priority:
        1. Wordplay examples (40%) - teach lateral thinking
        2. Category match (30%) - relevant domain
        3. Early solves (30%) - show pattern recognition
        """
        manager = get_context_manager()

        if not manager.games:
            return manager._get_fallback_examples()

        selected: List[HistoricalGame] = []

        # Priority 1: Wordplay examples (CRITICAL for trivia)
        wordplay_keywords = [
            "double meaning", "wordplay", "pun", "triple meaning",
            "refers to", "multiple meanings", "-> ", "wordplay on"
        ]
        wordplay_games = [
            g for g in manager.games
            if any(kw in g.key_insight.lower() for kw in wordplay_keywords)
        ]
        if wordplay_games:
            # Take 2 wordplay examples
            selected.extend(random.sample(wordplay_games, min(2, len(wordplay_games))))

        # Priority 2: Category match (if hint provided)
        if category_hint:
            category_hint = category_hint.lower().strip()
            category_matches = [
                g for g in manager.games
                if g.category.lower() == category_hint and g not in selected
            ]
            if category_matches:
                # Add 1 category-specific example
                selected.append(random.choice(category_matches))

        # Priority 3: Early solves (show pattern recognition skill)
        remaining_slots = num_examples - len(selected)
        if remaining_slots > 0:
            early_solves = sorted(
                [g for g in manager.games if g not in selected],
                key=lambda g: g.clue_solved_at
            )
            selected.extend(early_solves[:remaining_slots])

        return self._format_examples(selected[:num_examples])

    def _format_examples(self, games: List[HistoricalGame]) -> str:
        """Format selected games as prompt examples."""
        if not games:
            return ""

        lines = ["## EXAMPLES FROM PAST GAMES", ""]

        for i, game in enumerate(games, 1):
            category_label = game.category.upper()
            # Show first 3 clues only
            clues_list = [f'Clue {j+1}: "{c}"' for j, c in enumerate(game.clues[:3])]

            lines.append(f"**Example {i} ({category_label}):**")
            for clue in clues_list:
                lines.append(f"  {clue}")
            lines.append(f"  **Answer:** {game.answer}")
            lines.append(f"  **Key insight:** {game.key_insight}")
            lines.append("")

        return "\n".join(lines)

    def _build_system_prompt(self, category_hint: Optional[str] = None) -> str:
        """Build complete system prompt with few-shot examples and error patterns."""
        examples = self._select_few_shot_examples(category_hint, num_examples=4)
        error_patterns = self._get_error_patterns_prompt()
        return GEMINI_TRIVIA_MASTER_PROMPT.format(
            dynamic_examples=examples,
            error_patterns=error_patterns
        )

    def _get_error_patterns_prompt(self) -> str:
        """Load error patterns from file and format as prompt warning."""
        try:
            from pathlib import Path
            error_file = Path(__file__).parent.parent / "data" / "error_patterns.json"

            if not error_file.exists():
                return ""

            with open(error_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            patterns = data.get("patterns", [])
            if not patterns:
                return ""

            # Build warning section
            lines = ["## LEARN FROM PAST MISTAKES", ""]

            for pattern in patterns[:3]:  # Show up to 3 most recent errors
                predicted = pattern.get("predicted", "")
                correct = pattern.get("correct", "")
                clues_sample = pattern.get("clues_sample", [])
                error_type = pattern.get("error_type", "unknown")

                if predicted and correct:
                    clues_text = ", ".join(clues_sample[:2]) if clues_sample else "various clues"
                    lines.append(f"⚠️ Previously, \"{predicted}\" was incorrectly predicted when the answer was \"{correct}\"")
                    lines.append(f"   Clues were about: {clues_text}")
                    if error_type == "phonetic_confusion":
                        lines.append(f"   These words SOUND similar but have DIFFERENT meanings!")
                    lines.append("")

            return "\n".join(lines)

        except Exception as e:
            logger.warning(f"Failed to load error patterns: {e}")
            return ""

    def _format_clues_message(
        self,
        clues: List[str],
        category_hint: Optional[str] = None
    ) -> str:
        """Format clues for the user message."""
        lines = []

        if category_hint:
            lines.append(f"[Category hint: {category_hint.upper()}]")
            lines.append("")

        lines.append("Here are the clues revealed so far:")
        lines.append("")

        for i, clue in enumerate(clues, 1):
            lines.append(f'Clue {i}: "{clue}"')

        lines.append("")
        lines.append(f"We are on Clue {len(clues)} of 5. Provide your top 3 predictions in JSON format.")

        return "\n".join(lines)

    def _recalibrate_confidence(
        self,
        raw_confidence: float,
        clue_number: int
    ) -> float:
        """
        Adjust confidence based on clue number.

        LLMs tend to be overconfident on early clues where information
        is minimal. This applies a correction factor.
        """
        if clue_number <= 1:
            # Very conservative on clue 1
            return raw_confidence * 0.75
        elif clue_number == 2:
            return raw_confidence * 0.85
        elif clue_number >= 4:
            # Slight boost on late clues (more info available)
            return min(0.98, raw_confidence * 1.05)
        return raw_confidence

    def _parse_response(
        self,
        text: str,
        clue_number: int
    ) -> Optional[GeminiResponse]:
        """Parse and validate Gemini's JSON response."""
        if not text:
            return None

        try:
            # Extract JSON from potential markdown wrapper
            json_text = text.strip()

            # Remove markdown code blocks if present
            if json_text.startswith("```"):
                # Find the end of the code block
                lines = json_text.split("\n")
                json_lines = []
                in_block = False
                for line in lines:
                    if line.startswith("```"):
                        in_block = not in_block
                        continue
                    if in_block or not line.startswith("```"):
                        json_lines.append(line)
                json_text = "\n".join(json_lines)

            # Find JSON boundaries
            json_start = json_text.find('{')
            json_end = json_text.rfind('}') + 1

            if json_start == -1 or json_end <= json_start:
                logger.warning(f"No JSON found in response: {text[:100]}...")
                return None

            json_str = json_text[json_start:json_end]
            data = json.loads(json_str)

            # Parse predictions
            predictions = []
            raw_predictions = data.get("predictions", [])

            for i, pred in enumerate(raw_predictions[:3]):
                raw_conf = pred.get("confidence", 0.5)
                # Handle both 0-1 and 0-100 scales
                if raw_conf > 1:
                    raw_conf = raw_conf / 100.0

                calibrated_conf = self._recalibrate_confidence(raw_conf, clue_number)

                # Parse semantic_match and apply confidence penalties
                semantic_match = pred.get("semantic_match", "medium").lower()
                if semantic_match not in ("strong", "medium", "weak"):
                    semantic_match = "medium"

                # Apply confidence penalty for weak semantic matches
                if semantic_match == "weak":
                    calibrated_conf *= 0.6  # Significant penalty
                elif semantic_match == "medium":
                    calibrated_conf *= 0.85  # Slight penalty
                # "strong" = no penalty

                predictions.append(GeminiPrediction(
                    rank=pred.get("rank", i + 1),
                    answer=pred.get("answer", ""),
                    confidence=calibrated_conf,
                    category=pred.get("category", "thing"),
                    reasoning=pred.get("reasoning", "")[:150],
                    semantic_match=semantic_match
                ))

            # Sort by confidence
            predictions.sort(key=lambda p: p.confidence, reverse=True)
            for i, pred in enumerate(predictions):
                pred.rank = i + 1

            should_guess = data.get("should_guess", predictions[0].confidence >= 0.40 if predictions else False)

            return GeminiResponse(
                predictions=predictions,
                should_guess=should_guess,
                key_insight=data.get("key_insight", ""),
                raw_response=text
            )

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e} - Response: {text[:200]}...")
            return None
        except Exception as e:
            logger.error(f"Response parsing error: {e}")
            return None

    async def predict(
        self,
        clues: List[str],
        category_hint: Optional[str] = None,
        session_context: Optional[Dict] = None
    ) -> Optional[GeminiResponse]:
        """
        Get top 3 predictions from Gemini.

        Args:
            clues: List of clues seen so far ["Clue 1", "Clue 2", ...]
            category_hint: Optional category from early analysis
            session_context: Optional additional context

        Returns:
            GeminiResponse with 3 predictions or None on error
        """
        if not await self.is_available():
            logger.warning("Gemini not available for prediction")
            return None

        client = await self._get_client()
        if not client:
            return None

        clue_number = len(clues)
        system_prompt = self._build_system_prompt(category_hint)
        user_message = self._format_clues_message(clues, category_hint)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        # Retry loop for robustness
        for attempt in range(self.MAX_RETRIES):
            try:
                response = await client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    max_tokens=self.MAX_TOKENS,
                    temperature=self.TEMPERATURE,
                    top_p=self.TOP_P,
                    stream=False
                )

                if response.choices:
                    text = response.choices[0].message.content
                    result = self._parse_response(text, clue_number)

                    if result and result.predictions:
                        logger.info(
                            f"Gemini prediction: {result.top_prediction.answer} "
                            f"({result.top_prediction.confidence:.0%}) - "
                            f"should_guess={result.should_guess}"
                        )
                        return result

                    # Parsing failed, retry with hint
                    if attempt < self.MAX_RETRIES - 1:
                        logger.warning(f"Parse failed, retrying ({attempt + 1}/{self.MAX_RETRIES})...")
                        messages[1]["content"] += "\n\nIMPORTANT: Return ONLY valid JSON, no markdown."
                        await asyncio.sleep(self.RETRY_DELAY)
                        continue

            except Exception as e:
                logger.error(f"Gemini API error (attempt {attempt + 1}): {e}")
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                    continue

        logger.error("All Gemini prediction attempts failed")
        return None

    def reset_availability(self):
        """Reset availability cache to re-check API."""
        self._available = None


# Singleton instance
_gemini_predictor: Optional[GeminiPredictor] = None


async def get_gemini_predictor() -> GeminiPredictor:
    """Get or create the Gemini predictor singleton."""
    global _gemini_predictor
    if _gemini_predictor is None:
        _gemini_predictor = GeminiPredictor()
    return _gemini_predictor


async def warmup_gemini() -> bool:
    """
    Check if Gemini API is available at startup.

    Cloud APIs don't need warmup, just availability check.
    """
    predictor = await get_gemini_predictor()
    available = await predictor.is_available()
    if available:
        logger.info(f"Gemini API ready: {predictor._mode} / {predictor.model_name}")
    return available

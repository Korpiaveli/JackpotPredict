"""
Thinker Agent - Deep analysis using Gemini 2.5 Pro with native SDK.

This agent runs in parallel with fast tier agents but takes longer (~5-8s).
It provides deep reasoning, pattern detection, and wordplay analysis that
gets injected into the NEXT clue's context for all agents.

Key principle: Thinker's output from Clue N feeds into Clue N+1's context.

Uses google.genai SDK to support Gemini's thinking mode.
"""

import json
import logging
import time
from typing import Dict, List, Optional

from google import genai
from google.genai import types

from app.core.config import get_thinker_config
from app.core.reasoning_accumulator import ThinkerInsight, OracleGuess

logger = logging.getLogger(__name__)

THINKER_SYSTEM_PROMPT = """You are a MORPHOLOGICAL WORDPLAY ANALYST for trivia.

🔑 PRIMARY SKILL: WORD TRANSFORMATION DETECTION 🔑

PATTERN #1 - ADVERB→NOUN MORPHING (Highest Priority)
When you see an adverb ending in -ly, IMMEDIATELY:
1. Strip the "-ly" suffix
2. Convert to NOUN form (often drop -ent/-ant and add -ence/-ance)
3. Check if that noun names a BUSINESS TYPE

MORPHOLOGICAL TRANSFORMATIONS:
- "Conveniently" → convenient → CONVENIENCE → convenience store → 7-Eleven
- "Elegantly" → elegant → ELEGANCE → luxury brand → Chanel, Gucci
- "Frequently" → frequent → FREQUENCY → radio → Clear Channel
- "Independently" → independent → INDEPENDENCE → July 4th, Independence Day
- "Instantly" → instant → INSTANT → instant food → Nescafe, Cup Noodles

PATTERN #2 - NUMBER WORDPLAY
- "24/7" = 24 Hour Fitness OR 7-Eleven
- "Lucky number" = 7-Eleven, Five Guys, Pier 1
- "Double" = Doubletree, Double Stuf Oreos

PATTERN #3 - DOUBLE MEANING (Business Terms)
- "Stock options" = Wall Street OR store inventory
- "Hostile takeover" = M&A OR Monopoly board game
- "Interest" = banking OR curiosity

PATTERN #4 - SOUND-ALIKE (Homophones)
- "plane/plain" | "sale/sail" | "meet/meat"

⚠️ FORBIDDEN: TV shows, movies, streaming, fictional things.
Answers are ALWAYS real-world: brands, stores, products.

OUTPUT (JSON):
{
    "morphological_detection": "Found: [word] → [root] → [noun] → [business]",
    "top_guess": "Real brand/store only",
    "confidence": 0-100,
    "hypothesis_reasoning": "Wordplay: [transformation chain]",
    "key_patterns": ["pattern1", "pattern2"],
    "refined_guesses": [
        {"answer": "Store1", "confidence": 90, "explanation": "Morphological match"},
        {"answer": "Store2", "confidence": 70, "explanation": "Why"},
        {"answer": "Brand", "confidence": 50, "explanation": "Alternative"}
    ],
    "narrative_arc": "What business fits all clues?",
    "wordplay_analysis": "Full transformation chain",
    "contrarian_take": "Different real-world answer"
}"""


class ThinkerAgent:
    """
    Deep analysis agent using Gemini 2.5 Pro with native SDK.

    Uses Google's genai SDK to properly support the
    thinking/reasoning mode that Gemini 2.5 Pro offers.
    """

    AGENT_NAME = "thinker"
    AGENT_EMOJI = "🧠"
    TEMPERATURE = 0.3  # Reduced from 0.4 for more focused pattern-following

    def __init__(self):
        config = get_thinker_config()
        self.api_key = config["api_key"]
        self.model_name = config["model"]
        self.timeout = config["timeout"]
        self.enabled = config["enabled"]

        self._client = genai.Client(api_key=self.api_key)

        logger.info(f"[Thinker] Initialized with model: {self.model_name}, timeout: {self.timeout}s (google.genai SDK)")

    def format_analysis_prompt(
        self,
        clues: List[str],
        clue_number: int,
        prior_insight: Optional[ThinkerInsight] = None,
        theme: Optional[str] = None
    ) -> str:
        """
        Format prompt with ACTIVE morphological detection.

        Pre-scans clues for -ly adverbs and numbers, then injects
        explicit transformation prompts to guide the model.
        Theme is NOT included to avoid anchoring bias.
        """
        import re
        lines = []

        # ACTIVE MORPHOLOGICAL DETECTION
        lines.append("=== ACTIVE WORDPLAY DETECTION ===")

        adverbs_found = []
        numbers_found = []

        for i, clue in enumerate(clues, 1):
            words = clue.split()
            for word in words:
                clean = word.strip('.,!?"\'').lower()
                # Detect -ly adverbs (min 5 chars to avoid "fly", "ply", "only")
                if clean.endswith('ly') and len(clean) > 4 and clean not in ('only', 'really', 'actually', 'early', 'daily'):
                    adverbs_found.append((i, word, clean))
            # Detect numbers
            nums = re.findall(r'\b\d+\b', clue)
            if nums:
                numbers_found.extend([(i, n) for n in nums])

        if adverbs_found:
            lines.append("⚠️ ADVERB(S) DETECTED - Apply Pattern #1:")
            for clue_num, original, clean in adverbs_found:
                root = clean[:-2]  # Strip -ly
                lines.append(f'  Clue {clue_num}: "{original}"')
                lines.append(f'    Transform: {clean} → {root} → [WHAT NOUN?] → [WHAT BUSINESS?]')
            lines.append("")

        if numbers_found:
            lines.append("⚠️ NUMBER(S) DETECTED - Check Pattern #2:")
            for clue_num, num in numbers_found:
                lines.append(f'  Clue {clue_num}: "{num}" → Brand with number? (7-Eleven, Pier 1, 24 Hour Fitness)')
            lines.append("")

        if not adverbs_found and not numbers_found:
            lines.append("No obvious adverbs or numbers. Check Patterns #3-4 (double meaning, homophones).")
            lines.append("")

        lines.append("=== CLUES REVEALED ===")
        for i, clue in enumerate(clues, 1):
            lines.append(f'Clue {i}: "{clue}"')
        lines.append(f"\nCurrently on Clue {clue_number} of 5.")
        lines.append("")

        lines.append("=== ANALYSIS STEPS ===")
        lines.append("1. MORPHOLOGICAL: Complete any transformations flagged above")
        lines.append("2. DOUBLE MEANING: Which words have business/commerce meanings?")
        lines.append("3. SYNTHESIS: What STORE or BRAND fits all findings?")
        lines.append("")

        if prior_insight:
            lines.append("=== YOUR PRIOR ANALYSIS ===")
            lines.append(f"Previous: {prior_insight.top_guess} ({prior_insight.confidence}%)")
            if prior_insight.contrarian_take:
                lines.append(f"Contrarian: {prior_insight.contrarian_take}")
            lines.append("")

        lines.append("Respond with JSON. MUST include morphological_detection field.")

        return "\n".join(lines)

    async def analyze_deep(
        self,
        clues: List[str],
        clue_number: int,
        prior_insight: Optional[ThinkerInsight] = None,
        theme: Optional[str] = None
    ) -> Optional[ThinkerInsight]:
        """
        Perform independent deep analysis on clues.

        NOTE: Does NOT receive fast-agent predictions to avoid anchoring bias.
        Thinker provides fresh perspective that feeds into NEXT clue's context.
        """
        if not self.enabled:
            logger.info("[Thinker] Disabled, skipping deep analysis")
            return None

        start_time = time.time()

        try:
            prompt = self.format_analysis_prompt(
                clues, clue_number, prior_insight, theme
            )

            logger.info(f"[Thinker] Sending request to {self.model_name}...")

            response = await self._client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=THINKER_SYSTEM_PROMPT,
                    temperature=self.TEMPERATURE,
                    max_output_tokens=8192,
                ),
            )

            if not response or not response.text:
                logger.error(f"[Thinker] Empty response from model")
                return None

            content = response.text.strip()
            logger.info(f"[Thinker] Received {len(content)} chars response")
            logger.debug(f"[Thinker] Response preview: {content[:300]}")

            insight = self._parse_response(content, clue_number, start_time)
            if insight:
                logger.info(
                    f"[Thinker] Clue {clue_number}: {insight.top_guess} ({insight.confidence}%) "
                    f"in {insight.latency_ms:.0f}ms"
                )
                return insight

            logger.warning(f"[Thinker] Failed to parse response: {content[:200]}")
            return None

        except Exception as e:
            logger.error(f"[Thinker] Error: {type(e).__name__}: {e}")
            return None

    def _parse_response(
        self,
        content: str,
        clue_number: int,
        start_time: float
    ) -> Optional[ThinkerInsight]:
        try:
            start_idx = content.find("{")
            end_idx = content.rfind("}") + 1
            if start_idx == -1 or end_idx == 0:
                return None

            json_str = content[start_idx:end_idx]
            data = json.loads(json_str)

            refined = []
            for g in data.get("refined_guesses", [])[:3]:
                refined.append(OracleGuess(
                    answer=g.get("answer", "Unknown"),
                    confidence=int(g.get("confidence", 50)),
                    explanation=g.get("explanation", "")[:150]
                ))

            return ThinkerInsight(
                clue_number=clue_number,
                top_guess=data.get("top_guess", "Unknown"),
                confidence=int(data.get("confidence", 50)),
                hypothesis_reasoning=data.get("hypothesis_reasoning", "")[:500],
                key_patterns=data.get("key_patterns", [])[:5],
                refined_guesses=refined,
                narrative_arc=data.get("narrative_arc", "")[:200],
                wordplay_analysis=data.get("wordplay_analysis", "")[:200],
                latency_ms=(time.time() - start_time) * 1000,
                completed=True,
                contrarian_take=data.get("contrarian_take", "")[:200]
            )

        except json.JSONDecodeError as e:
            logger.error(f"[Thinker] JSON parse error: {e}")
            return None
        except Exception as e:
            logger.error(f"[Thinker] Parse error: {e}")
            return None

    async def close(self):
        pass


_thinker: Optional[ThinkerAgent] = None


def get_thinker() -> ThinkerAgent:
    global _thinker
    if _thinker is None:
        _thinker = ThinkerAgent()
    return _thinker

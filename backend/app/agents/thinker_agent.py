"""
Thinker Agent - Deep analysis using Gemini 2.5 Pro.

This agent runs in parallel with fast tier agents but takes longer (~5-8s).
It provides deep reasoning, pattern detection, and wordplay analysis that
gets injected into the NEXT clue's context for all agents.

Key principle: Thinker's output from Clue N feeds into Clue N+1's context.
"""

import json
import logging
import time
from typing import Dict, List, Optional
import httpx

from app.core.config import get_thinker_config
from app.core.reasoning_accumulator import ThinkerInsight, OracleGuess
from .base_agent import AgentPrediction

logger = logging.getLogger(__name__)

THINKER_SYSTEM_PROMPT = """You are the THINKER - a deep analysis agent for trivia prediction.

Your role is NOT to guess quickly, but to provide DEEP ANALYSIS that helps other agents on the NEXT clue.

You receive:
1. All clues revealed so far
2. Fast-tier agent predictions (5 agents with instant responses)
3. Your prior analyses (if any)

Your task:
1. Identify PATTERNS across clues (narrative arc, theme evolution)
2. Analyze WORDPLAY and linguistic tricks (puns, homophones, double meanings)
3. Reason about WHY agents agree/disagree
4. Build HYPOTHESES with detailed rationale
5. Prepare CONTEXT for fast agents in next round

RESPONSE FORMAT (JSON):
{
    "top_guess": "Your best answer",
    "confidence": 0-100,
    "hypothesis_reasoning": "200-500 char deep analysis explaining your thinking process",
    "key_patterns": ["pattern1", "pattern2", "pattern3"],
    "refined_guesses": [
        {"answer": "Guess1", "confidence": 90, "explanation": "Why this is likely"},
        {"answer": "Guess2", "confidence": 70, "explanation": "Alternative possibility"},
        {"answer": "Guess3", "confidence": 40, "explanation": "Long shot consideration"}
    ],
    "narrative_arc": "The story these clues tell in 1-2 sentences",
    "wordplay_analysis": "Any detected puns, homophones, or double meanings"
}

Focus on DEPTH over speed. Your analysis helps future predictions."""


class ThinkerAgent:
    """
    Deep analysis agent using Gemini 2.5 Pro.

    Runs in parallel with fast tier but provides richer analysis
    that gets injected into subsequent clue predictions.
    """

    AGENT_NAME = "thinker"
    AGENT_EMOJI = "🧠"
    TEMPERATURE = 0.4

    def __init__(self):
        config = get_thinker_config()
        self.api_key = config["api_key"]
        self.base_url = config["base_url"].rstrip("/")
        self.model = config["model"]
        self.timeout = config["timeout"]
        self.enabled = config["enabled"]
        self._client: Optional[httpx.AsyncClient] = None
        logger.info(f"[Thinker] Initialized with model: {self.model}, timeout: {self.timeout}s")

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
            )
        return self._client

    def format_analysis_prompt(
        self,
        clues: List[str],
        clue_number: int,
        fast_predictions: Dict[str, AgentPrediction],
        prior_insight: Optional[ThinkerInsight] = None,
        theme: Optional[str] = None
    ) -> str:
        lines = []

        if theme:
            lines.append(f"TONIGHT'S THEME/SPONSOR: {theme}")
            lines.append("")

        if prior_insight:
            lines.append("=== YOUR PRIOR ANALYSIS ===")
            lines.append(f"Previous guess: {prior_insight.top_guess} ({prior_insight.confidence}%)")
            lines.append(f"Reasoning: {prior_insight.hypothesis_reasoning[:200]}")
            lines.append(f"Patterns found: {', '.join(prior_insight.key_patterns)}")
            lines.append("")

        lines.append("=== CLUES REVEALED ===")
        for i, clue in enumerate(clues, 1):
            lines.append(f'Clue {i}: "{clue}"')
        lines.append(f"\nCurrently on Clue {clue_number} of 5.")
        lines.append("")

        lines.append("=== FAST AGENT PREDICTIONS ===")
        for name, pred in fast_predictions.items():
            if pred:
                conf_pct = int(pred.confidence * 100)
                lines.append(f"  {name}: {pred.answer} ({conf_pct}%) - {pred.reasoning}")
        lines.append("")

        agreement = self._analyze_agreement(fast_predictions)
        lines.append(f"Agreement: {agreement}")
        lines.append("")

        lines.append("Provide deep analysis in JSON format. Focus on patterns, wordplay, and narrative arc.")

        return "\n".join(lines)

    def _analyze_agreement(self, predictions: Dict[str, AgentPrediction]) -> str:
        answers = {}
        for pred in predictions.values():
            if pred:
                key = pred.answer.lower()
                answers[key] = answers.get(key, 0) + 1

        if not answers:
            return "No predictions"

        top_answer = max(answers, key=answers.get)
        count = answers[top_answer]
        total = len([p for p in predictions.values() if p])

        if count >= 4:
            return f"Strong consensus on '{top_answer}' ({count}/{total})"
        elif count >= 3:
            return f"Moderate agreement on '{top_answer}' ({count}/{total})"
        elif count >= 2:
            return f"Split between options, '{top_answer}' leads ({count}/{total})"
        else:
            return f"No agreement - all agents different"

    async def analyze_deep(
        self,
        clues: List[str],
        clue_number: int,
        fast_predictions: Dict[str, AgentPrediction],
        prior_insight: Optional[ThinkerInsight] = None,
        theme: Optional[str] = None
    ) -> Optional[ThinkerInsight]:
        if not self.enabled:
            logger.info("[Thinker] Disabled, skipping deep analysis")
            return None

        start_time = time.time()

        try:
            messages = [
                {"role": "system", "content": THINKER_SYSTEM_PROMPT},
                {"role": "user", "content": self.format_analysis_prompt(
                    clues, clue_number, fast_predictions, prior_insight, theme
                )}
            ]

            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": self.TEMPERATURE,
                "max_tokens": 16384,
            }

            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            logger.info(f"[Thinker] Raw response structure: {json.dumps(data, default=str)[:500]}")

            content = None
            if "choices" in data and len(data["choices"]) > 0:
                choice = data["choices"][0]
                logger.info(f"[Thinker] Choice keys: {list(choice.keys())}")
                if "message" in choice:
                    message = choice["message"]
                    logger.info(f"[Thinker] Message keys: {list(message.keys()) if isinstance(message, dict) else type(message)}")
                    if isinstance(message, dict) and "content" in message:
                        content = message["content"]
                    elif isinstance(message, str):
                        content = message
                elif "text" in choice:
                    content = choice["text"]

            if content is None:
                logger.error(f"[Thinker] Could not extract content from response")
                return None

            content = content.strip()

            insight = self._parse_response(content, clue_number, start_time)
            if insight:
                logger.info(
                    f"[Thinker] Clue {clue_number}: {insight.top_guess} ({insight.confidence}%) "
                    f"in {insight.latency_ms:.0f}ms"
                )
                return insight

            logger.warning(f"[Thinker] Failed to parse response: {content[:200]}")
            return None

        except httpx.TimeoutException:
            logger.warning(f"[Thinker] Timeout after {self.timeout}s")
            return None
        except Exception as e:
            logger.error(f"[Thinker] Error: {e}")
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
                completed=True
            )

        except json.JSONDecodeError as e:
            logger.error(f"[Thinker] JSON parse error: {e}")
            return None
        except Exception as e:
            logger.error(f"[Thinker] Parse error: {e}")
            return None

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


_thinker: Optional[ThinkerAgent] = None


def get_thinker() -> ThinkerAgent:
    global _thinker
    if _thinker is None:
        _thinker = ThinkerAgent()
    return _thinker

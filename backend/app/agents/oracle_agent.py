"""
Oracle Agent - Meta-Synthesizer for 5-agent predictions.

Uses Claude 3.5 Sonnet to analyze all agent predictions and voting results,
providing 3 ranked guesses with clear explanations and pattern identification.

The Oracle sees the full picture that individual agents cannot:
- All 5 agent predictions and reasoning
- Voting results and agreement strength
- Confidence evolution across clues
- Emergent themes and patterns
"""

import json
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from anthropic import AsyncAnthropic

from app.core.config import get_oracle_config
from app.core.reasoning_accumulator import OracleSynthesis, OracleGuess, ClueAnalysis

logger = logging.getLogger(__name__)


# Oracle System Prompt (used when specialist predictions are available)
ORACLE_SYSTEM_PROMPT = """You are THE ORACLE - a meta-synthesizer for a 5-agent trivia prediction system
for Netflix's "Best Guess Live" game show.

YOUR UNIQUE ROLE:
Synthesize predictions from 5 specialist agents and provide YOUR TOP 3 GUESSES
with clear, concise explanations of why each fits the clues.

THE 5 SPECIALISTS YOU OVERSEE:
- Lateral: Multi-hop associative reasoning
- Wordsmith: Puns, wordplay, linguistic tricks
- PopCulture: Netflix/trending/celebrity bias
- Literal: Face-value interpretation, trap detection
- WildCard: Creative divergent thinking

YOUR TASK:
1. Analyze all 5 agent predictions and their reasoning
2. Identify patterns, themes, and narrative arcs across clues
3. Synthesize into YOUR TOP 3 GUESSES ranked by confidence
4. Provide SHORT but CLEAR explanations (1-2 sentences each)
5. Identify any blind spots the agents may have missed

OUTPUT FORMAT (strict JSON only, no markdown):
{
  "top_3": [
    {
      "answer": "MONOPOLY",
      "confidence": 92,
      "explanation": "Business terms ('hostile takeover') + board game ('round and round' = going around board) + 'dicey' = rolling dice"
    },
    {
      "answer": "RISK",
      "confidence": 45,
      "explanation": "Military conquest fits 'hostile takeover' but weaker match on 'flavors' and 'dicey' clues"
    },
    {
      "answer": "LIFE",
      "confidence": 30,
      "explanation": "WildCard's pick - 'flavors of life' metaphor works but doesn't explain 'hostile takeover'"
    }
  ],
  "key_theme": "Board games with business/strategy elements",
  "blind_spot": "Consider if 'dicey' is wordplay (dice) or means 'risky'"
}

CRITICAL RULES:
- Output ONLY valid JSON, no markdown code blocks
- Always provide exactly 3 guesses
- Confidence must be 0-100 (integers)
- Explanations should be 1-2 sentences max
- key_theme: 5-10 word summary of the dominant pattern
- blind_spot: What might agents be missing? (5-15 words)
"""

# Early Oracle System Prompt (runs in parallel with specialists, no current predictions)
ORACLE_EARLY_SYSTEM_PROMPT = """You are THE ORACLE - analyzing clue progression for Netflix's "Best Guess Live" game show.

You are running EARLY (in parallel with specialist agents, before their predictions arrive).
Focus on clue pattern analysis and historical context.

CONTEXT PROVIDED:
- All clues revealed so far
- Prior clue analyses (if any) with agent predictions and voting results

YOUR TASK:
1. Analyze the clue progression and emerging themes
2. Identify patterns connecting the clues
3. Provide YOUR TOP 3 GUESSES ranked by confidence
4. Flag potential blind spots

OUTPUT FORMAT (strict JSON only, no markdown):
{
  "top_3": [
    {
      "answer": "MONOPOLY",
      "confidence": 85,
      "explanation": "Clue progression suggests board game: 'flavors' (editions), 'round and round' (board movement), 'hostile takeover' (business theme)"
    },
    {
      "answer": "RISK",
      "confidence": 40,
      "explanation": "Military/conquest theme fits 'hostile takeover' but weaker on other clues"
    },
    {
      "answer": "LIFE",
      "confidence": 25,
      "explanation": "'Flavors of life' metaphor, but missing business connection"
    }
  ],
  "key_theme": "Board games with business/strategy elements",
  "blind_spot": "Check for wordplay - 'dicey' could mean dice or risky"
}

CRITICAL RULES:
- Output ONLY valid JSON, no markdown code blocks
- Always provide exactly 3 guesses
- Confidence must be 0-100 (integers)
- Explanations should be 1-2 sentences max
- key_theme: 5-10 word summary of the dominant pattern
- blind_spot: What might we be missing? (5-15 words)
"""


class OracleAgent:
    """
    Meta-synthesizer agent that analyzes all 5 specialist predictions.

    Uses Claude 3.5 Sonnet to see the full picture and provide:
    - 3 ranked guesses with explanations
    - Key theme identification
    - Blind spot detection
    """

    AGENT_NAME = "oracle"
    AGENT_EMOJI = "🔮"
    TEMPERATURE = 0.3

    def __init__(self):
        """Initialize Oracle with Anthropic client."""
        config = get_oracle_config()
        self.api_key = config["api_key"]
        self.model = config["model"]
        self.timeout = config["timeout"]
        self.enabled = config["enabled"]
        self._client: Optional[AsyncAnthropic] = None

    @property
    def client(self) -> AsyncAnthropic:
        """Lazy-initialize the Anthropic client."""
        if self._client is None:
            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client

    def _build_context(
        self,
        predictions: Dict[str, Any],
        voting_result: Any,
        clues: List[str],
        clue_number: int,
        prior_analyses: Optional[List[ClueAnalysis]] = None
    ) -> str:
        """
        Build context message for Oracle from all agent predictions.

        Args:
            predictions: Dict of agent_name -> AgentPrediction
            voting_result: VotingResult from weighted voting
            clues: List of clues revealed so far
            clue_number: Current clue number (1-5)
            prior_analyses: Optional prior clue analyses

        Returns:
            Formatted context string for Claude
        """
        lines = []

        # Current clue context
        lines.append(f"CURRENT STATE: Clue {clue_number} of 5")
        lines.append("")
        lines.append("CLUES REVEALED:")
        for i, clue in enumerate(clues, 1):
            marker = ">>>" if i == clue_number else "   "
            lines.append(f'{marker} Clue {i}: "{clue}"')
        lines.append("")

        # All agent predictions
        lines.append("=" * 50)
        lines.append("5 SPECIALIST AGENT PREDICTIONS:")
        lines.append("=" * 50)

        for agent_name, pred in predictions.items():
            if pred is not None:
                conf_pct = int(pred.confidence * 100)
                reasoning = pred.reasoning[:80] if pred.reasoning else "No reasoning"
                lines.append(f"[{agent_name.upper()}] {pred.answer} ({conf_pct}%)")
                lines.append(f"    Reasoning: \"{reasoning}\"")
                lines.append("")

        # Voting result
        lines.append("=" * 50)
        lines.append("VOTING RESULT:")
        lines.append("=" * 50)
        lines.append(f"Recommended: {voting_result.recommended_pick}")
        lines.append(f"Agreement: {voting_result.agreement_strength}")
        lines.append(f"Key Insight: {voting_result.key_insight}")
        lines.append("")

        # Vote breakdown
        if voting_result.vote_breakdown:
            lines.append("Vote Breakdown:")
            for vb in voting_result.vote_breakdown[:3]:
                agents_str = ", ".join(vb.agents)
                lines.append(f"  {vb.answer}: {vb.total_votes:.1f} votes ({agents_str})")
        lines.append("")

        # Prior analyses (if any)
        if prior_analyses:
            lines.append("=" * 50)
            lines.append("PRIOR CLUE ANALYSES:")
            lines.append("=" * 50)
            for analysis in prior_analyses:
                lines.append(f'Clue {analysis.clue_number}: "{analysis.clue_text}"')
                lines.append(f"  Top Pick: {analysis.top_answer} ({int(analysis.top_confidence * 100)}%)")
                lines.append(f"  Agreement: {analysis.agreement_strength}")
                if analysis.oracle_synthesis:
                    oracle = analysis.oracle_synthesis
                    if oracle.top_3:
                        lines.append(f"  Oracle Pick: {oracle.top_3[0].answer}")
                lines.append("")

        lines.append("=" * 50)
        lines.append("YOUR TASK: Provide your TOP 3 GUESSES as JSON")
        lines.append("=" * 50)

        return "\n".join(lines)

    def _parse_response(self, content: str) -> Optional[OracleSynthesis]:
        """
        Parse Claude's JSON response into OracleSynthesis.

        Args:
            content: Raw response from Claude

        Returns:
            OracleSynthesis or None if parsing fails
        """
        try:
            # Clean up response (remove markdown code blocks if present)
            content = content.strip()
            if content.startswith("```"):
                # Remove markdown code block
                lines = content.split("\n")
                content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

            data = json.loads(content)

            # Parse top 3 guesses
            top_3 = []
            for guess in data.get("top_3", [])[:3]:
                top_3.append(OracleGuess(
                    answer=guess.get("answer", "Unknown"),
                    confidence=int(guess.get("confidence", 50)),
                    explanation=guess.get("explanation", "")[:150]
                ))

            # Ensure we have at least 1 guess
            if not top_3:
                return None

            return OracleSynthesis(
                top_3=top_3,
                key_theme=data.get("key_theme", "Analysis pending")[:100],
                blind_spot=data.get("blind_spot", "None identified")[:100],
                latency_ms=0.0  # Set by caller
            )

        except json.JSONDecodeError as e:
            logger.error(f"[Oracle] JSON parse error: {e}")
            logger.debug(f"[Oracle] Raw response: {content[:500]}")
            return None
        except Exception as e:
            logger.error(f"[Oracle] Parse error: {e}")
            return None

    async def synthesize(
        self,
        predictions: Dict[str, Any],
        voting_result: Any,
        clues: List[str],
        clue_number: int,
        prior_analyses: Optional[List[ClueAnalysis]] = None
    ) -> Optional[OracleSynthesis]:
        """
        Run Oracle meta-synthesis on all agent predictions.

        Args:
            predictions: Dict of agent_name -> AgentPrediction
            voting_result: VotingResult from weighted voting
            clues: List of clues revealed so far
            clue_number: Current clue number (1-5)
            prior_analyses: Optional prior clue analyses

        Returns:
            OracleSynthesis with top 3 guesses, or None if failed
        """
        if not self.enabled:
            logger.warning("[Oracle] Disabled - no API key configured")
            return None

        start_time = time.time()

        try:
            # Build context
            context = self._build_context(
                predictions, voting_result, clues, clue_number, prior_analyses
            )

            # Call Claude 3.5 Sonnet
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=self.TEMPERATURE,
                system=ORACLE_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": context}]
            )

            # Extract text response
            content = response.content[0].text

            # Parse response
            synthesis = self._parse_response(content)
            if synthesis:
                synthesis.latency_ms = (time.time() - start_time) * 1000

                logger.info(
                    f"[Oracle] Top pick: {synthesis.top_3[0].answer} ({synthesis.top_3[0].confidence}%) | "
                    f"Theme: {synthesis.key_theme[:30]} | "
                    f"Latency: {synthesis.latency_ms:.0f}ms"
                )
                return synthesis

            logger.warning("[Oracle] Failed to parse response")
            return None

        except Exception as e:
            logger.error(f"[Oracle] Error: {e}")
            return None

    def _build_early_context(
        self,
        clues: List[str],
        clue_number: int,
        prior_analyses: Optional[List[ClueAnalysis]] = None
    ) -> str:
        """
        Build context for early Oracle (runs in parallel with specialists).

        No current predictions available - uses only clues and prior analyses.
        """
        lines = []

        # Current clue context
        lines.append(f"CURRENT STATE: Clue {clue_number} of 5")
        lines.append("")
        lines.append("CLUES REVEALED:")
        for i, clue in enumerate(clues, 1):
            marker = ">>>" if i == clue_number else "   "
            lines.append(f'{marker} Clue {i}: "{clue}"')
        lines.append("")

        # Prior analyses (this is the main context for early mode)
        if prior_analyses:
            lines.append("=" * 50)
            lines.append("PRIOR CLUE ANALYSES (from earlier rounds):")
            lines.append("=" * 50)
            for analysis in prior_analyses:
                lines.append(f'Clue {analysis.clue_number}: "{analysis.clue_text}"')
                lines.append(f"  Top Pick: {analysis.top_answer} ({int(analysis.top_confidence * 100)}%)")
                lines.append(f"  Agreement: {analysis.agreement_strength}")
                if analysis.top_agents:
                    lines.append(f"  Agents: {', '.join(analysis.top_agents)}")
                # Include agent snapshots for full context
                if analysis.agent_snapshots:
                    for snap in analysis.agent_snapshots[:5]:
                        conf_pct = int(snap.confidence * 100)
                        lines.append(f"    [{snap.agent_name}] {snap.answer} ({conf_pct}%) - {snap.insight}")
                if analysis.oracle_synthesis:
                    oracle = analysis.oracle_synthesis
                    if oracle.top_3:
                        lines.append(f"  Oracle Pick: {oracle.top_3[0].answer} ({oracle.top_3[0].confidence}%)")
                lines.append("")
        else:
            lines.append("(First clue - no prior analyses available)")
            lines.append("")

        lines.append("=" * 50)
        lines.append("YOUR TASK: Analyze clue progression and provide TOP 3 GUESSES as JSON")
        lines.append("=" * 50)

        return "\n".join(lines)

    async def synthesize_early(
        self,
        clues: List[str],
        clue_number: int,
        prior_analyses: Optional[List[ClueAnalysis]] = None
    ) -> Optional[OracleSynthesis]:
        """
        Run Oracle synthesis using only prior analyses and current clues.

        This runs in PARALLEL with specialist agents (no dependency on their predictions).
        Uses the early system prompt focused on clue pattern analysis.

        Args:
            clues: List of clues revealed so far
            clue_number: Current clue number (1-5)
            prior_analyses: Optional prior clue analyses with agent predictions

        Returns:
            OracleSynthesis with top 3 guesses, or None if failed
        """
        if not self.enabled:
            logger.warning("[Oracle] Disabled - no API key configured")
            return None

        start_time = time.time()

        try:
            # Build early context (no current predictions)
            context = self._build_early_context(clues, clue_number, prior_analyses)

            # Call Claude with early prompt
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=self.TEMPERATURE,
                system=ORACLE_EARLY_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": context}]
            )

            # Extract text response
            content = response.content[0].text

            # Parse response
            synthesis = self._parse_response(content)
            if synthesis:
                synthesis.latency_ms = (time.time() - start_time) * 1000

                logger.info(
                    f"[Oracle-Early] Top pick: {synthesis.top_3[0].answer} ({synthesis.top_3[0].confidence}%) | "
                    f"Theme: {synthesis.key_theme[:30]} | "
                    f"Latency: {synthesis.latency_ms:.0f}ms"
                )
                return synthesis

            logger.warning("[Oracle-Early] Failed to parse response")
            return None

        except Exception as e:
            logger.error(f"[Oracle-Early] Error: {e}")
            return None

    async def close(self):
        """Close the Anthropic client (if needed)."""
        # AsyncAnthropic doesn't require explicit close
        self._client = None


# Singleton instance
_oracle: Optional[OracleAgent] = None


def get_oracle() -> OracleAgent:
    """Get or create singleton Oracle instance."""
    global _oracle
    if _oracle is None:
        _oracle = OracleAgent()
    return _oracle

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
from app.core.context_manager import get_cultural_context_manager

logger = logging.getLogger(__name__)


# Oracle System Prompt (used when specialist predictions are available)
ORACLE_SYSTEM_PROMPT = """You are THE ORACLE - a meta-synthesizer for a 5-agent trivia prediction system
for Netflix's "Best Guess Live" game show.

CRITICAL ADVERSARIAL CONTEXT:
- Clue writers (Apploff Entertainment) design clues to MISLEAD both humans and AI
- Early clues are intentionally vague/deceptive; Clue 5 is often explicit/giveaway
- 65% of answers are THINGS, 20% are PEOPLE, 15% are PLACES
- Wordplay, puns, and double meanings appear in 90%+ of puzzles

MISDIRECTION PATTERNS TO DETECT:
1. POLYSEMY TRAP: Word has multiple meanings (e.g., "dicey" = dice OR risky)
2. CATEGORY MISDIRECTION: Clue sounds like category X but answer is category Y
3. LITERAL/FIGURATIVE INVERSION: The obvious literal reading is usually the trap
4. CULTURAL REFERENCE: Famous quotes, catchphrases, or media references

HISTORICAL EXAMPLES (from actual games - learn these patterns!):
- "SOUR SPORT THAT GOOD SPORTS RELISH" → PICKLEBALL (sour=pickle, sport=sport, relish=condiment)
- "IT'S FESTIVUS FOR THE BEST GUESTS OF US" → SEINFELD (Festivus = holiday from Seinfeld)
- "I PITY THE FOOL WHO DOESN'T GET THIS" → MR. T (direct quote from A-Team)
- "PUTS THE APE IN SKYSCRAPER" → KING KONG (ape + Empire State Building)
- "I'M THE KING OF THE WORLD" → TITANIC (famous movie quote)
- "JAIL TIME CAN BE DICEY" → MONOPOLY (jail square + rolling dice)
- "TASTES SO NICE THEY NAMED IT TWICE" → M&MS (M and M)
- "I MATTEL YOU: KEN THINKS SHE'S A DOLL" → BARBIE (Mattel brand, Ken, doll)

THE 5 SPECIALISTS YOU OVERSEE:
- Lateral: Multi-hop associative reasoning
- Wordsmith: Puns, wordplay, linguistic tricks
- PopCulture: Netflix/trending/celebrity bias
- Literal: Face-value interpretation, trap detection
- WildCard: Creative divergent thinking

YOUR TASK:
1. First ask: "What TRAP is the clue writer setting?" - identify the misdirection
2. Analyze all 5 agent predictions - are they falling for the trap?
3. Look for cultural references, quotes, or wordplay patterns
4. Synthesize into YOUR TOP 3 GUESSES ranked by confidence
5. Explain WHY each answer fits (connect specific clue words)

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
  "misdirection_detected": "Early clues suggest business/corporate but 'dicey' wordplay points to board game",
  "key_theme": "Board games with business/strategy elements",
  "blind_spot": "Consider if 'dicey' is wordplay (dice) or means 'risky'"
}

CRITICAL RULES:
- Output ONLY valid JSON, no markdown code blocks
- Always provide exactly 3 guesses
- Confidence must be 0-100 (integers)
- Explanations should be 1-2 sentences max, connecting specific clue words to answer
- misdirection_detected: What trap is the clue writer setting? (10-20 words)
- key_theme: 5-10 word summary of the dominant pattern
- blind_spot: What might agents be missing? (5-15 words)
"""

# Early Oracle System Prompt (runs in parallel with specialists, no current predictions)
ORACLE_EARLY_SYSTEM_PROMPT = """You are THE ORACLE - analyzing clue progression for Netflix's "Best Guess Live" game show.

You are running EARLY (in parallel with specialist agents, before their predictions arrive).
Focus on adversarial analysis: What TRAP is the clue writer setting?

CRITICAL ADVERSARIAL CONTEXT:
- Clue writers (Apploff Entertainment) design clues to MISLEAD both humans and AI
- Early clues (1-2) are intentionally vague/deceptive - the obvious answer is usually WRONG
- Later clues (4-5) often contain giveaways (quotes, explicit references)
- 65% of answers are THINGS, 20% are PEOPLE, 15% are PLACES
- Wordplay, puns, and double meanings appear in 90%+ of puzzles

MISDIRECTION PATTERNS TO DETECT:
1. POLYSEMY TRAP: Word has multiple meanings (e.g., "dicey" = dice OR risky)
2. CATEGORY MISDIRECTION: Clue sounds like category X but answer is category Y
3. LITERAL/FIGURATIVE INVERSION: The obvious literal reading is usually the trap
4. CULTURAL REFERENCE: Famous quotes, catchphrases, or media references

HISTORICAL EXAMPLES (from actual games - learn these patterns!):
- "SOUR SPORT THAT GOOD SPORTS RELISH" → PICKLEBALL (sour=pickle, sport=sport, relish=condiment)
- "IT'S FESTIVUS FOR THE BEST GUESTS OF US" → SEINFELD (Festivus = holiday from Seinfeld)
- "I PITY THE FOOL WHO DOESN'T GET THIS" → MR. T (direct quote from A-Team)
- "PUTS THE APE IN SKYSCRAPER" → KING KONG (ape + Empire State Building)
- "I'M THE KING OF THE WORLD" → TITANIC (famous movie quote)
- "JAIL TIME CAN BE DICEY" → MONOPOLY (jail square + rolling dice)
- "TASTES SO NICE THEY NAMED IT TWICE" → M&MS (M and M)
- "I MATTEL YOU: KEN THINKS SHE'S A DOLL" → BARBIE (Mattel brand, Ken, doll)
- "OPENAI HAD A BOT, A-LA-I-O" → CHATGPT (OpenAI + Old MacDonald wordplay)
- "DAKOTA HILLS, POTUS GRILLS" → MOUNT RUSHMORE (South Dakota + presidents' faces)
- "ROLLING THROUGH YOUR HOOD AND TALKING TRASH" → GARBAGE TRUCK (literal description)
- "THE FRUITCAKE OF HOLIDAY ATTIRE" → UGLY SWEATER (unwanted holiday gift metaphor)

CLUE NUMBER STRATEGY:
- Clue 1-2: Be SKEPTICAL of obvious answers - these are designed to mislead
- Clue 3: Look for pattern convergence across all clues
- Clue 4-5: Watch for explicit references, quotes, or giveaways

YOUR TASK:
1. First ask: "What TRAP is the clue writer setting?" - identify the misdirection
2. Analyze clue progression - what theme connects ALL clues?
3. Look for cultural references, quotes, wordplay, or puns
4. Provide YOUR TOP 3 GUESSES ranked by confidence
5. Explain WHY each answer fits (connect specific clue words)

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
  "misdirection_detected": "Early clues suggest corporate world but board game wordplay emerges",
  "key_theme": "Board games with business/strategy elements",
  "blind_spot": "Check for wordplay - 'dicey' could mean dice or risky"
}

CRITICAL RULES:
- Output ONLY valid JSON, no markdown code blocks
- Always provide exactly 3 guesses
- Confidence must be 0-100 (integers)
- Explanations should be 1-2 sentences max, connecting specific clue words to answer
- misdirection_detected: What trap is the clue writer setting? (10-20 words)
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
                latency_ms=0.0,  # Set by caller
                misdirection_detected=data.get("misdirection_detected", "")[:150]
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
        Includes cultural context injection for adversarial counter-reasoning.
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

        # Inject cultural context (MOA Optimization v3)
        try:
            cultural_ctx = get_cultural_context_manager()
            context_injection = cultural_ctx.build_context_injection(clues, clue_number)
            if context_injection:
                lines.append("=" * 50)
                lines.append("ADVERSARIAL CONTEXT (auto-detected):")
                lines.append("=" * 50)
                lines.append(context_injection)
                lines.append("")
        except Exception as e:
            logger.warning(f"[Oracle] Cultural context injection failed: {e}")

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

"""
Reasoning Accumulator - Accumulates and compresses agent reasoning across clues.

This module enables agents to build on prior analysis by:
1. Capturing full predictions after voting
2. Generating context injection strings for subsequent clues
3. Tracking hypothesis confidence evolution
4. Storing Oracle synthesis results

Part of the Advanced-One-Shot MoA architecture.
"""

import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AgentSnapshot:
    """Compressed prediction snapshot for storage."""
    agent_name: str
    answer: str
    confidence: float  # 0.0 to 1.0
    insight: str  # Reasoning summary (truncated)


@dataclass
class OracleGuess:
    """Single guess from the Oracle with explanation."""
    answer: str
    confidence: int  # 0-100
    explanation: str


@dataclass
class ThinkerInsight:
    """Deep analysis result from the Thinker (Gemini 2.5 Pro)."""
    clue_number: int
    top_guess: str
    confidence: int  # 0-100
    hypothesis_reasoning: str  # 200-500 char deep analysis
    key_patterns: List[str]  # Identified patterns
    refined_guesses: List[OracleGuess]  # Top 3 with explanations
    narrative_arc: str  # Story the clues tell
    wordplay_analysis: str  # Detected wordplay
    latency_ms: float
    completed: bool = True


@dataclass
class ThinkerContext:
    """Accumulated thinker insights for context injection."""
    insights: List[ThinkerInsight] = field(default_factory=list)
    last_updated: float = 0.0

    def add_insight(self, insight: ThinkerInsight) -> None:
        """Add a new insight from the thinker."""
        self.insights.append(insight)
        self.last_updated = time.time()

    def latest(self) -> Optional[ThinkerInsight]:
        """Get the most recent insight."""
        return self.insights[-1] if self.insights else None

    def get_for_clue(self, clue_number: int) -> Optional[ThinkerInsight]:
        """Get insight for a specific clue number."""
        for insight in self.insights:
            if insight.clue_number == clue_number:
                return insight
        return None

    def get_prior_insight(self, current_clue: int) -> Optional[ThinkerInsight]:
        """Get the insight from the previous clue (for context injection)."""
        return self.get_for_clue(current_clue - 1)


@dataclass
class OracleSynthesis:
    """Oracle's meta-synthesis output with top 3 guesses."""
    top_3: List[OracleGuess]
    key_theme: str
    blind_spot: str
    latency_ms: float


@dataclass
class ClueAnalysis:
    """Analysis results for a single clue."""
    clue_number: int
    clue_text: str

    # Top picks from voting
    top_answer: str
    top_confidence: float
    top_agents: List[str]

    # Alternative hypothesis (if any)
    alt_answer: Optional[str]
    alt_confidence: Optional[float]
    alt_agents: List[str]

    # Confidence delta from prior clue
    confidence_delta: float  # e.g., +0.07 means +7%

    # All agent predictions
    agent_snapshots: List[AgentSnapshot]

    # Voting signals
    agreement_strength: str  # "strong", "moderate", "weak", "none"

    # Oracle synthesis (if available)
    oracle_synthesis: Optional[OracleSynthesis] = None

    # Timestamp
    analyzed_at: float = field(default_factory=time.time)


class ReasoningAccumulator:
    """
    Accumulates and compresses agent reasoning across clues.

    Responsibilities:
    1. Capture full predictions after voting
    2. Compress to context-efficient format
    3. Track hypothesis confidence evolution
    4. Generate context injection strings for agents
    """

    def __init__(self, max_context_tokens: int = 500):
        """
        Initialize the reasoning accumulator.

        Args:
            max_context_tokens: Maximum tokens for context injection
        """
        self.max_tokens = max_context_tokens

    def create_clue_analysis(
        self,
        clue_number: int,
        clue_text: str,
        predictions: Dict[str, Any],  # AgentPrediction objects
        voting_result: Any,  # VotingResult object
        prior_analyses: List[ClueAnalysis]
    ) -> ClueAnalysis:
        """
        Create analysis for the current clue.

        Args:
            clue_number: Current clue number (1-5)
            clue_text: The clue text
            predictions: Dict of agent_name -> AgentPrediction
            voting_result: VotingResult from weighted voting
            prior_analyses: List of prior ClueAnalysis objects

        Returns:
            ClueAnalysis for this clue
        """
        # Extract top from voting breakdown
        top = voting_result.vote_breakdown[0] if voting_result.vote_breakdown else None
        alt = voting_result.vote_breakdown[1] if len(voting_result.vote_breakdown) > 1 else None

        # Calculate confidence delta from prior clue
        prior_top_conf = prior_analyses[-1].top_confidence if prior_analyses else 0.0
        current_conf = top.avg_confidence if top else 0.0
        delta = current_conf - prior_top_conf

        # Create agent snapshots
        snapshots = []
        for name, pred in predictions.items():
            if pred is not None:
                snapshots.append(AgentSnapshot(
                    agent_name=name,
                    answer=pred.answer,
                    confidence=pred.confidence,
                    insight=pred.reasoning[:50] if pred.reasoning else ""
                ))

        return ClueAnalysis(
            clue_number=clue_number,
            clue_text=clue_text,
            top_answer=top.answer if top else "Unknown",
            top_confidence=current_conf,
            top_agents=top.agents if top else [],
            alt_answer=alt.answer if alt else None,
            alt_confidence=alt.avg_confidence if alt else None,
            alt_agents=alt.agents if alt else [],
            confidence_delta=delta,
            agent_snapshots=snapshots,
            agreement_strength=voting_result.agreement_strength,
            oracle_synthesis=None,  # Set later if Oracle runs
            analyzed_at=time.time()
        )

    def generate_context_injection(
        self,
        analyses: List[ClueAnalysis],
        current_clue_number: int,
        full_predictions: bool = True,
        thinker_context: Optional[ThinkerContext] = None
    ) -> str:
        """
        Generate context injection string for agent prompts.

        Args:
            analyses: List of prior ClueAnalysis objects
            current_clue_number: Current clue number (for reference)
            full_predictions: If True, include all 5 agent predictions per clue
            thinker_context: Optional ThinkerContext with deep analysis insights

        Returns:
            Formatted context string for injection into prompts
        """
        lines = []

        # Priority 1: Thinker deep analysis from PRIOR clue
        if thinker_context:
            prior_insight = thinker_context.get_prior_insight(current_clue_number)
            if prior_insight:
                lines.append("=== DEEP ANALYSIS (from prior clue) ===")
                lines.append(f"Top Hypothesis: {prior_insight.top_guess} ({prior_insight.confidence}%)")
                lines.append(f"Reasoning: {prior_insight.hypothesis_reasoning[:300]}")
                if prior_insight.key_patterns:
                    lines.append(f"Patterns: {', '.join(prior_insight.key_patterns[:3])}")
                if prior_insight.wordplay_analysis:
                    lines.append(f"Wordplay: {prior_insight.wordplay_analysis}")
                lines.append(f"Narrative: {prior_insight.narrative_arc}")
                lines.append("")

        # Priority 2: Prior voting results
        if not analyses:
            return "\n".join(lines) if lines else ""

        lines.append("PRIOR ANALYSIS:")
        lines.append("")

        for analysis in analyses:
            # Clue header
            lines.append(f'=== CLUE {analysis.clue_number}: "{analysis.clue_text}" ===')

            if full_predictions:
                # Full agent predictions mode
                for snapshot in analysis.agent_snapshots:
                    conf_pct = int(snapshot.confidence * 100)
                    insight_clean = snapshot.insight.replace('"', "'")[:40]
                    lines.append(
                        f'  {snapshot.agent_name}: {snapshot.answer} ({conf_pct}%) - "{insight_clean}"'
                    )

            # Voting result summary
            trend = self._format_trend(analysis.confidence_delta)
            agent_count = len(analysis.top_agents)
            lines.append(
                f'  >> VOTE: {analysis.top_answer} ({agent_count}/5 agree, {analysis.agreement_strength}) {trend}'
            )

            # Oracle synthesis if available
            if analysis.oracle_synthesis:
                oracle = analysis.oracle_synthesis
                if oracle.top_3:
                    top_guess = oracle.top_3[0]
                    lines.append(f'  >> ORACLE: {top_guess.answer} ({top_guess.confidence}%) - "{oracle.key_theme}"')

            lines.append("")

        # Add evolution summary
        if len(analyses) >= 2:
            evolution = self._summarize_evolution(analyses)
            lines.append(f"[TREND: {evolution}]")
            lines.append("")

        return "\n".join(lines)

    def _format_trend(self, delta: float) -> str:
        """Format confidence delta as trend indicator."""
        if delta > 0.05:
            return f"[+{delta*100:.0f}%]"
        elif delta < -0.05:
            return f"[{delta*100:.0f}%]"
        elif delta == 0:
            return "[NEW]"
        else:
            return "[stable]"

    def _summarize_evolution(self, analyses: List[ClueAnalysis]) -> str:
        """Summarize hypothesis evolution in 5-10 words."""
        first = analyses[0]
        last = analyses[-1]

        if first.top_answer.lower() == last.top_answer.lower():
            delta = last.top_confidence - first.top_confidence
            if delta > 0.1:
                return f"{first.top_answer} strengthening (+{delta*100:.0f}% over {len(analyses)} clues)"
            elif delta < -0.1:
                return f"{first.top_answer} weakening ({delta*100:.0f}% over {len(analyses)} clues)"
            else:
                return f"{first.top_answer} holding steady across {len(analyses)} clues"
        else:
            return f"Shifted from {first.top_answer} to {last.top_answer}"

    def update_hypothesis_tracker(
        self,
        tracker: Dict[str, List[float]],
        analysis: ClueAnalysis
    ) -> None:
        """
        Update confidence tracking for hypotheses.

        Args:
            tracker: Dict mapping answer -> list of confidence values
            analysis: ClueAnalysis for current clue
        """
        # Track top answer
        answer_key = analysis.top_answer.lower()
        if answer_key not in tracker:
            tracker[answer_key] = []
        tracker[answer_key].append(analysis.top_confidence)

        # Track alternative if present
        if analysis.alt_answer and analysis.alt_confidence:
            alt_key = analysis.alt_answer.lower()
            if alt_key not in tracker:
                tracker[alt_key] = []
            tracker[alt_key].append(analysis.alt_confidence)

    def get_confidence_evolution(
        self,
        tracker: Dict[str, List[float]]
    ) -> Dict[str, Dict]:
        """
        Get formatted confidence evolution for API response.

        Args:
            tracker: Hypothesis tracker dict

        Returns:
            Dict with answer -> {history, trend} for top hypotheses
        """
        result = {}

        for answer, history in tracker.items():
            if len(history) < 2:
                trend = "new"
            else:
                delta = history[-1] - history[0]
                if delta > 0.1:
                    trend = "rising"
                elif delta < -0.1:
                    trend = "falling"
                else:
                    trend = "stable"

            result[answer] = {
                "history": history,
                "trend": trend
            }

        return result


# Singleton instance
_accumulator: Optional[ReasoningAccumulator] = None


def get_accumulator() -> ReasoningAccumulator:
    """Get or create the singleton ReasoningAccumulator instance."""
    global _accumulator
    if _accumulator is None:
        _accumulator = ReasoningAccumulator()
    return _accumulator

"""
Weighted Voting - Clue-aware voting system for agent predictions.

Implements weighted voting based on clue number:
- Early clues (1-2): Favor lateral/wordsmith agents (cryptic clues)
- Middle clues (3): Balanced weights
- Late clues (4-5): Favor literal agent (direct clues)
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
import logging

from .base_agent import AgentPrediction

logger = logging.getLogger(__name__)


# Voting weights by clue number
# Higher weight = more influence on final recommendation
# Note: Tuned so that 2+ agent consensus can still beat single-agent high-weight
CLUE_WEIGHTS = {
    1: {"lateral": 1.5, "wordsmith": 1.5, "popculture": 1.0, "literal": 0.5, "wildcard": 1.2},
    2: {"lateral": 1.3, "wordsmith": 1.3, "popculture": 1.1, "literal": 0.7, "wildcard": 1.0},
    3: {"lateral": 1.0, "wordsmith": 1.0, "popculture": 1.2, "literal": 1.0, "wildcard": 0.8},
    4: {"lateral": 0.9, "wordsmith": 0.9, "popculture": 1.1, "literal": 1.2, "wildcard": 0.7},
    5: {"lateral": 0.8, "wordsmith": 0.8, "popculture": 1.0, "literal": 1.3, "wildcard": 0.6},
}


@dataclass
class VoteResult:
    """Result of voting on an answer."""
    answer: str
    total_votes: float
    agents: List[str]
    avg_confidence: float


@dataclass
class VotingResult:
    """Complete voting result with recommendation."""
    recommended_pick: str
    recommended_confidence: float
    key_insight: str
    agreement_strength: str  # "strong", "moderate", "weak"
    vote_breakdown: List[VoteResult]


def normalize_answer(answer: str) -> str:
    """
    Normalize answer for comparison.

    - Lowercase
    - Strip whitespace
    - Remove common prefixes/suffixes
    """
    normalized = answer.lower().strip()

    # Remove common prefixes
    prefixes = ["the ", "a ", "an "]
    for prefix in prefixes:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]

    return normalized


def cluster_predictions(
    predictions: Dict[str, AgentPrediction],
    similarity_threshold: float = 0.85
) -> Dict[str, List[str]]:
    """
    Group similar predictions into clusters.

    For now, uses exact match after normalization.
    TODO: Add semantic similarity with embeddings.

    Args:
        predictions: Dict of agent_name -> AgentPrediction
        similarity_threshold: Cosine similarity threshold (future use)

    Returns:
        Dict mapping normalized_answer -> list of agent names
    """
    clusters: Dict[str, List[str]] = {}

    for agent_name, pred in predictions.items():
        if pred is None:
            continue

        normalized = normalize_answer(pred.answer)

        if normalized not in clusters:
            clusters[normalized] = []
        clusters[normalized].append(agent_name)

    return clusters


class WeightedVoting:
    """
    Weighted voting system for combining agent predictions.

    Features:
    - Clue-aware weighting (creative agents early, literal late)
    - Answer clustering for similar predictions
    - Agreement strength calculation
    - Key insight extraction
    """

    def __init__(self, weights: Dict[int, Dict[str, float]] = None):
        """
        Initialize voting system.

        Args:
            weights: Custom weight configuration (or use defaults)
        """
        self.weights = weights or CLUE_WEIGHTS

    def vote(
        self,
        predictions: Dict[str, AgentPrediction],
        clue_number: int
    ) -> VotingResult:
        """
        Perform weighted voting on agent predictions.

        Args:
            predictions: Dict of agent_name -> AgentPrediction
            clue_number: Current clue number (1-5)

        Returns:
            VotingResult with recommended pick and breakdown
        """
        # Get weights for this clue number
        clue_weights = self.weights.get(clue_number, self.weights[3])  # Default to balanced

        # Filter out None predictions
        valid_predictions = {k: v for k, v in predictions.items() if v is not None}

        if not valid_predictions:
            return VotingResult(
                recommended_pick="Unknown",
                recommended_confidence=0.0,
                key_insight="No valid predictions",
                agreement_strength="none",
                vote_breakdown=[]
            )

        # Cluster similar answers
        clusters = cluster_predictions(valid_predictions)

        # Calculate weighted votes for each cluster
        vote_results: List[VoteResult] = []

        for normalized_answer, agent_names in clusters.items():
            # Sum weighted votes
            total_votes = 0.0
            confidences = []

            for agent_name in agent_names:
                pred = valid_predictions[agent_name]
                weight = clue_weights.get(agent_name, 1.0)
                total_votes += weight * pred.confidence
                confidences.append(pred.confidence)

            # Get canonical answer (from first agent in cluster)
            canonical_answer = valid_predictions[agent_names[0]].answer

            vote_results.append(VoteResult(
                answer=canonical_answer,
                total_votes=total_votes,
                agents=agent_names,
                avg_confidence=sum(confidences) / len(confidences)
            ))

        # Sort by total votes
        vote_results.sort(key=lambda x: x.total_votes, reverse=True)

        # Get winner
        winner = vote_results[0]
        num_agreeing = len(winner.agents)

        # Determine agreement strength
        if num_agreeing >= 4:
            agreement_strength = "strong"
        elif num_agreeing >= 2:
            agreement_strength = "moderate"
        else:
            agreement_strength = "weak"

        # Extract key insight from the highest-confidence agreeing agent
        key_insight = "No insight"
        best_conf = 0.0
        for agent_name in winner.agents:
            pred = valid_predictions[agent_name]
            if pred.confidence > best_conf:
                best_conf = pred.confidence
                key_insight = pred.reasoning

        return VotingResult(
            recommended_pick=winner.answer,
            recommended_confidence=winner.avg_confidence,
            key_insight=key_insight,
            agreement_strength=agreement_strength,
            vote_breakdown=vote_results
        )

    def should_guess(
        self,
        voting_result: VotingResult,
        clue_number: int
    ) -> tuple[bool, str]:
        """
        Determine if user should guess now.

        Thresholds based on clue number:
        - Clue 1: 90%+ confidence with strong agreement
        - Clue 2: 85%+ confidence with strong agreement
        - Clue 3: 75%+ confidence with moderate+ agreement
        - Clue 4: 65%+ confidence
        - Clue 5: Always guess (last chance)

        Args:
            voting_result: Result from vote()
            clue_number: Current clue number

        Returns:
            (should_guess, rationale)
        """
        conf = voting_result.recommended_confidence
        agreement = voting_result.agreement_strength
        num_agreeing = len(voting_result.vote_breakdown[0].agents) if voting_result.vote_breakdown else 0

        thresholds = {
            1: (0.90, "strong"),
            2: (0.85, "strong"),
            3: (0.75, "moderate"),
            4: (0.65, "weak"),
            5: (0.0, "none"),  # Always guess on clue 5
        }

        min_conf, min_agreement = thresholds.get(clue_number, (0.75, "moderate"))

        agreement_order = {"none": 0, "weak": 1, "moderate": 2, "strong": 3}

        if clue_number == 5:
            return True, "Last clue - must guess now"

        if conf >= min_conf and agreement_order[agreement] >= agreement_order[min_agreement]:
            return True, f"{num_agreeing} agents agree at {conf*100:.0f}% confidence"

        return False, f"Confidence {conf*100:.0f}% - wait for more clues"

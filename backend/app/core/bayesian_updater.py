"""
Bayesian Updater - Probability engine for answer prediction.

This module implements Bayesian probability updates across the 5-clue sequence,
combining prior probabilities with clue-entity likelihood scores.

Formula: P(answer|clues) ∝ P(clues|answer) × P(answer)
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass
import logging
import math

from .entity_registry import Entity, EntityCategory
from .clue_analyzer import ClueAnalysis

logger = logging.getLogger(__name__)


@dataclass
class EntityProbability:
    """
    Probability score for an entity with reasoning.

    Attributes:
        entity: The Entity object
        probability: Current probability score (0-1)
        confidence: Confidence level (0-1, accounting for evidence quality)
        reasoning: Human-readable explanation of score
        evidence_points: List of evidence factors contributing to score
    """
    entity: Entity
    probability: float
    confidence: float
    reasoning: str
    evidence_points: List[str]

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        return {
            "canonical_name": self.entity.canonical_name,
            "category": self.entity.category.value,
            "probability": round(self.probability, 4),
            "confidence": round(self.confidence, 4),
            "reasoning": self.reasoning,
            "evidence_points": self.evidence_points
        }


class BayesianUpdater:
    """
    Bayesian probability engine for sequential clue analysis.

    Maintains probability distribution over entities and updates it as new
    clues arrive using Bayes' theorem with polysemy bonuses and category priors.
    """

    # Polysemy bonus multiplier (entities with dual meanings get 1.5x boost)
    POLYSEMY_BONUS = 1.5

    # Category weight in likelihood calculation
    CATEGORY_WEIGHT = 0.3

    # Keyword match weight
    KEYWORD_WEIGHT = 0.4

    # Recency bonus weight
    RECENCY_WEIGHT = 0.1

    # Clue association weight
    ASSOCIATION_WEIGHT = 0.2

    def __init__(self):
        """Initialize BayesianUpdater."""
        self.entity_probs: Dict[str, EntityProbability] = {}
        self.clue_history: List[ClueAnalysis] = []

    def initialize_priors(
        self,
        entities: List[Entity],
        category_priors: Dict[EntityCategory, float]
    ):
        """
        Initialize prior probabilities based on category distribution.

        Args:
            entities: List of all candidate entities
            category_priors: Base category probabilities (Thing: 0.6, Place: 0.25, Person: 0.15)
        """
        if not entities:
            logger.warning("No entities provided for prior initialization")
            return

        # Count entities per category
        category_counts = {cat: 0 for cat in EntityCategory}
        for entity in entities:
            category_counts[entity.category] += 1

        # Assign uniform prior within each category
        for entity in entities:
            category_prior = category_priors.get(entity.category, 0.33)
            category_count = category_counts[entity.category]

            if category_count > 0:
                # Uniform distribution within category, weighted by category prior
                prior_prob = category_prior / category_count

                # Small recency boost (max 10% adjustment)
                recency_boost = 1.0 + (0.1 * entity.recency_score)
                prior_prob *= recency_boost

                self.entity_probs[entity.canonical_name] = EntityProbability(
                    entity=entity,
                    probability=prior_prob,
                    confidence=0.1,  # Low confidence initially
                    reasoning="Prior based on category distribution",
                    evidence_points=[]
                )

        # Normalize probabilities
        self._normalize_probabilities()

    def update_probabilities(
        self,
        clue_analysis: ClueAnalysis,
        entity_search_results: List[Tuple[Entity, float]]
    ) -> List[EntityProbability]:
        """
        Update entity probabilities based on new clue (Bayesian update).

        Args:
            clue_analysis: Analyzed clue with extracted features
            entity_search_results: List of (Entity, similarity_score) from registry search

        Returns:
            List of EntityProbability objects, sorted by probability descending
        """
        self.clue_history.append(clue_analysis)

        # Create lookup for search scores
        search_scores = {entity.canonical_name: score for entity, score in entity_search_results}

        # Update each entity's probability
        for canonical_name, entity_prob in self.entity_probs.items():
            entity = entity_prob.entity

            # Get prior probability
            prior = entity_prob.probability

            # Calculate likelihood: P(clue|entity)
            likelihood, evidence = self._calculate_likelihood(
                entity,
                clue_analysis,
                search_scores.get(canonical_name, 0.0)
            )

            # Posterior: P(entity|clue) ∝ P(clue|entity) × P(entity)
            posterior = likelihood * prior

            # Calculate confidence (increases with more evidence)
            new_confidence = self._calculate_confidence(
                entity_prob.confidence,
                likelihood,
                len(evidence)
            )

            # Build reasoning string
            reasoning = self._build_reasoning(entity, clue_analysis, evidence)

            # Update entity probability
            self.entity_probs[canonical_name] = EntityProbability(
                entity=entity,
                probability=posterior,
                confidence=new_confidence,
                reasoning=reasoning,
                evidence_points=evidence
            )

        # Eliminate contradictory entities
        self._eliminate_contradictions(clue_analysis)

        # Normalize probabilities
        self._normalize_probabilities()

        # Return top entities sorted by probability
        sorted_entities = sorted(
            self.entity_probs.values(),
            key=lambda x: x.probability,
            reverse=True
        )

        return sorted_entities

    def _calculate_likelihood(
        self,
        entity: Entity,
        clue_analysis: ClueAnalysis,
        search_score: float
    ) -> Tuple[float, List[str]]:
        """
        Calculate P(clue|entity) - how well the clue matches this entity.

        Args:
            entity: Entity to score
            clue_analysis: Analyzed clue
            search_score: TF-IDF similarity score from registry search

        Returns:
            (likelihood_score, evidence_list) tuple
        """
        likelihood = 1.0
        evidence = []

        # 1. Keyword match score (from TF-IDF search)
        if search_score > 0:
            keyword_contribution = self.KEYWORD_WEIGHT * search_score
            likelihood *= (1.0 + keyword_contribution)
            if search_score > 0.3:
                evidence.append(f"Strong keyword match (score: {search_score:.2f})")

        # 2. Category alignment
        category_prob = clue_analysis.category_probs.get(entity.category, 0.33)
        category_contribution = self.CATEGORY_WEIGHT * category_prob
        likelihood *= (1.0 + category_contribution)

        if category_prob > 0.5:
            evidence.append(f"Category '{entity.category.value}' strongly indicated ({category_prob:.0%})")

        # 3. Polysemy bonus - critical for Clue 1-2
        polysemy_match = False
        for polysemous_word, meanings in clue_analysis.polysemous_words.items():
            # Check if any meaning relates to entity triggers
            for trigger in entity.polysemy_triggers:
                if any(meaning.lower() in trigger.lower() for meaning in meanings):
                    polysemy_match = True
                    evidence.append(f"Polysemy match: '{polysemous_word}' → {trigger}")
                    break

        if polysemy_match:
            likelihood *= self.POLYSEMY_BONUS

        # 4. Clue association match
        for keyword in clue_analysis.keywords:
            for association in entity.clue_associations:
                if keyword in association.lower():
                    association_contribution = self.ASSOCIATION_WEIGHT
                    likelihood *= (1.0 + association_contribution)
                    evidence.append(f"Clue pattern match: '{keyword}' in '{association}'")
                    break

        # 5. Recency bonus (recent entities slightly favored)
        if entity.recency_score > 0.7:
            recency_contribution = self.RECENCY_WEIGHT * entity.recency_score
            likelihood *= (1.0 + recency_contribution)
            evidence.append(f"High cultural relevance ({entity.recency_score:.0%})")

        # 6. Negation pattern matching
        if clue_analysis.negation_patterns:
            for has_attr, cannot_action in clue_analysis.negation_patterns:
                # Check if this pattern relates to entity
                pattern_text = f"has {has_attr} but cannot {cannot_action}"
                for association in entity.clue_associations:
                    if has_attr in association.lower() or cannot_action in association.lower():
                        likelihood *= 1.3
                        evidence.append(f"Negation pattern: '{pattern_text}'")
                        break

        return likelihood, evidence

    def _calculate_confidence(
        self,
        prior_confidence: float,
        likelihood: float,
        evidence_count: int
    ) -> float:
        """
        Calculate confidence level (how sure we are about the probability).

        Confidence increases with:
        - More clues analyzed
        - Stronger likelihood scores
        - More evidence points

        Args:
            prior_confidence: Previous confidence level
            likelihood: Current likelihood score
            evidence_count: Number of evidence points

        Returns:
            Updated confidence score (0-1)
        """
        # Base confidence increases with each clue
        base_increase = 0.15 * len(self.clue_history)

        # Evidence quality boost
        evidence_boost = min(0.3, evidence_count * 0.05)

        # Likelihood strength boost
        likelihood_boost = min(0.2, (likelihood - 1.0) * 0.1)

        new_confidence = prior_confidence + base_increase + evidence_boost + likelihood_boost

        # Cap at 0.95 (never 100% certain)
        return min(0.95, new_confidence)

    def _eliminate_contradictions(self, clue_analysis: ClueAnalysis):
        """
        Eliminate entities that contradict any clue.

        For example, if category signals strongly indicate "person", heavily
        penalize non-person entities.

        Args:
            clue_analysis: Current clue analysis
        """
        # If category probability is very high (>80%), heavily penalize others
        for category, prob in clue_analysis.category_probs.items():
            if prob > 0.8:
                for canonical_name, entity_prob in list(self.entity_probs.items()):
                    if entity_prob.entity.category != category:
                        # Reduce probability by 80%
                        self.entity_probs[canonical_name].probability *= 0.2
                        logger.debug(f"Penalized {canonical_name} for category mismatch")

    def _normalize_probabilities(self):
        """Normalize all probabilities to sum to 1.0."""
        total = sum(ep.probability for ep in self.entity_probs.values())

        if total > 0:
            for canonical_name in self.entity_probs:
                self.entity_probs[canonical_name].probability /= total

    def _build_reasoning(
        self,
        entity: Entity,
        clue_analysis: ClueAnalysis,
        evidence: List[str]
    ) -> str:
        """
        Build human-readable reasoning for probability score.

        Args:
            entity: Entity being evaluated
            clue_analysis: Current clue analysis
            evidence: List of evidence points

        Returns:
            Reasoning string for display to user
        """
        if not evidence:
            return f"Weak match for '{clue_analysis.clue_text}'"

        # Highlight top evidence
        top_evidence = evidence[:2]  # Show max 2 evidence points

        reasoning_parts = [f"Clue {clue_analysis.clue_number}:"]
        reasoning_parts.extend(top_evidence)

        return " | ".join(reasoning_parts)

    def get_top_predictions(self, top_k: int = 3) -> List[EntityProbability]:
        """
        Get top K predictions sorted by probability.

        Args:
            top_k: Number of top predictions to return

        Returns:
            List of EntityProbability objects
        """
        sorted_entities = sorted(
            self.entity_probs.values(),
            key=lambda x: x.probability,
            reverse=True
        )

        return sorted_entities[:top_k]

    def reset(self):
        """Reset all probabilities and clue history for new puzzle."""
        self.entity_probs.clear()
        self.clue_history.clear()
        logger.info("BayesianUpdater reset for new puzzle")

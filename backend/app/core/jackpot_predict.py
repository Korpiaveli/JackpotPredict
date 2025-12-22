"""
JackpotPredict - Main orchestrator for trivia answer prediction.

This is the public API that coordinates all core components to analyze clues
and generate ranked predictions with confidence scores and reasoning.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from uuid import uuid4
import time
import logging

from .entity_registry import EntityRegistry, EntityCategory
from .clue_analyzer import ClueAnalyzer, ClueAnalysis
from .bayesian_updater import BayesianUpdater, EntityProbability
from .spelling_validator import SpellingValidator

logger = logging.getLogger(__name__)


@dataclass
class Prediction:
    """
    Single prediction result with all metadata.

    Attributes:
        rank: Position in top predictions (1, 2, 3)
        answer: Canonical spelling of predicted answer
        confidence: Confidence percentage (0-100)
        reasoning: Human-readable explanation
        category: Entity category (thing/place/person)
        clues_analyzed: Number of clues analyzed so far
    """
    rank: int
    answer: str
    confidence: float  # 0-100
    reasoning: str
    category: str
    clues_analyzed: int

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        return {
            "rank": self.rank,
            "answer": self.answer,
            "confidence": round(self.confidence, 1),
            "reasoning": self.reasoning,
            "category": self.category,
            "clues_analyzed": self.clues_analyzed
        }


@dataclass
class PredictionResponse:
    """
    Complete response with predictions and metadata.

    Attributes:
        predictions: Top 3 predictions ranked by confidence
        session_id: Unique session identifier
        clue_number: Current clue number (1-5)
        elapsed_time: Processing time in seconds
        should_guess: Recommendation whether to guess now (based on confidence)
    """
    predictions: List[Prediction]
    session_id: str
    clue_number: int
    elapsed_time: float
    should_guess: bool

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        return {
            "predictions": [p.to_dict() for p in self.predictions],
            "session_id": self.session_id,
            "clue_number": self.clue_number,
            "elapsed_time": round(self.elapsed_time, 3),
            "should_guess": self.should_guess
        }


class JackpotPredict:
    """
    Main orchestrator for the trivia prediction engine.

    Coordinates EntityRegistry, ClueAnalyzer, BayesianUpdater, and SpellingValidator
    to produce high-confidence predictions within <2 second latency requirement.
    """

    # Confidence thresholds for guess recommendations (based on clue number)
    GUESS_THRESHOLDS = {
        1: 50.0,  # Very rare to guess on Clue 1
        2: 65.0,  # Two clues align perfectly
        3: 75.0,  # Pop culture pivot confirms hypothesis
        4: 85.0,  # Direct hint validates; most winners here
        5: 0.0,   # Must guess on final clue (no choice)
    }

    # Category priors (60/25/15 distribution from PRD)
    DEFAULT_CATEGORY_PRIORS = {
        EntityCategory.THING: 0.60,
        EntityCategory.PLACE: 0.25,
        EntityCategory.PERSON: 0.15,
    }

    def __init__(
        self,
        entity_registry: EntityRegistry,
        clue_analyzer: ClueAnalyzer,
        spelling_validator: Optional[SpellingValidator] = None
    ):
        """
        Initialize JackpotPredict orchestrator.

        Args:
            entity_registry: Initialized EntityRegistry
            clue_analyzer: Initialized ClueAnalyzer
            spelling_validator: Optional SpellingValidator (will create if None)
        """
        self.registry = entity_registry
        self.analyzer = clue_analyzer
        self.validator = spelling_validator or SpellingValidator(entity_registry)

        self.bayesian = BayesianUpdater()
        self.session_id = str(uuid4())
        self.clue_count = 0
        self.category_probs = self.DEFAULT_CATEGORY_PRIORS.copy()

        logger.info(f"JackpotPredict initialized (session: {self.session_id})")

    def add_clue(self, clue_text: str) -> PredictionResponse:
        """
        Analyze a new clue and generate updated predictions.

        This is the main entry point for the prediction engine.

        Args:
            clue_text: The clue text to analyze

        Returns:
            PredictionResponse with top 3 predictions and metadata
        """
        start_time = time.time()

        # Increment clue counter
        self.clue_count += 1
        logger.info(f"Processing Clue {self.clue_count}: '{clue_text}'")

        # Step 1: Analyze clue with NLP
        clue_analysis = self.analyzer.analyze(
            clue_text=clue_text,
            clue_number=self.clue_count,
            previous_category_probs=self.category_probs
        )

        # Update category probabilities for next clue
        self.category_probs = clue_analysis.category_probs

        # Step 2: Search entity registry with keywords
        search_results = self.registry.search_by_keywords(
            keywords=clue_analysis.keywords,
            category=None,  # Don't filter by category yet
            top_k=50,  # Get more candidates for Bayesian filtering
            min_score=0.01  # Lowered to catch weak polysemy matches like "flavors/editions"
        )

        # Step 3: Initialize Bayesian priors on first clue
        if self.clue_count == 1:
            all_entities = [entity for entity, _ in search_results]
            # Get more entities if search returned few
            if len(all_entities) < 100:
                additional = self.registry._get_all_entities()[:200]
                all_entities.extend(additional)

            self.bayesian.initialize_priors(all_entities, self.DEFAULT_CATEGORY_PRIORS)

        # Step 4: Update probabilities with Bayesian inference
        entity_probabilities = self.bayesian.update_probabilities(
            clue_analysis=clue_analysis,
            entity_search_results=search_results
        )

        # Step 5: Get top 3 predictions
        top_3 = entity_probabilities[:3]

        # Step 6: Validate spelling and format
        predictions = []
        for rank, entity_prob in enumerate(top_3, start=1):
            # Validate canonical spelling
            validation = self.validator.validate(entity_prob.entity.canonical_name)

            if not validation.is_valid:
                logger.warning(f"Validation failed for {entity_prob.entity.canonical_name}: {validation.error_message}")
                # Use formatted answer if available, otherwise canonical
                answer = validation.formatted_answer or entity_prob.entity.canonical_name
            else:
                answer = validation.formatted_answer

            # Use confidence score (already 0-1), convert to percentage
            confidence_pct = entity_prob.confidence * 100

            # Build reasoning (limit to 100 chars for UI)
            reasoning = entity_prob.reasoning
            if len(reasoning) > 100:
                reasoning = reasoning[:97] + "..."

            prediction = Prediction(
                rank=rank,
                answer=answer,
                confidence=confidence_pct,
                reasoning=reasoning,
                category=entity_prob.entity.category.value,
                clues_analyzed=self.clue_count
            )
            predictions.append(prediction)

        # Step 7: Determine guess recommendation
        should_guess = self._should_guess_now(predictions)

        # Calculate elapsed time
        elapsed_time = time.time() - start_time

        logger.info(f"Clue {self.clue_count} processed in {elapsed_time:.3f}s. "
                   f"Top prediction: {predictions[0].answer} ({predictions[0].confidence:.1f}%)")

        return PredictionResponse(
            predictions=predictions,
            session_id=self.session_id,
            clue_number=self.clue_count,
            elapsed_time=elapsed_time,
            should_guess=should_guess
        )

    def _should_guess_now(self, predictions: List[Prediction]) -> bool:
        """
        Determine if user should guess now based on confidence threshold.

        Args:
            predictions: Current top predictions

        Returns:
            True if confidence exceeds threshold for current clue number
        """
        if not predictions:
            return False

        top_confidence = predictions[0].confidence
        threshold = self.GUESS_THRESHOLDS.get(self.clue_count, 75.0)

        # Always recommend guessing on Clue 5 (last chance)
        if self.clue_count >= 5:
            return True

        return top_confidence >= threshold

    def reset(self):
        """
        Reset session for a new puzzle.

        Clears clue history, probabilities, and generates new session ID.
        """
        self.bayesian.reset()
        self.session_id = str(uuid4())
        self.clue_count = 0
        self.category_probs = self.DEFAULT_CATEGORY_PRIORS.copy()

        logger.info(f"Session reset. New session ID: {self.session_id}")

    def get_session_info(self) -> Dict:
        """
        Get current session metadata.

        Returns:
            Dictionary with session information
        """
        return {
            "session_id": self.session_id,
            "clues_analyzed": self.clue_count,
            "category_probs": {
                cat.value: round(prob, 3)
                for cat, prob in self.category_probs.items()
            }
        }

    def predict_all_clues(self, clues: List[str]) -> List[PredictionResponse]:
        """
        Convenience method: Process all 5 clues sequentially.

        Useful for batch testing with historical puzzles.

        Args:
            clues: List of 1-5 clue texts

        Returns:
            List of PredictionResponse objects (one per clue)
        """
        self.reset()
        responses = []

        for clue_text in clues:
            response = self.add_clue(clue_text)
            responses.append(response)

        return responses

    def get_top_answer(self) -> Optional[str]:
        """
        Get the current top predicted answer.

        Returns:
            Top answer string, or None if no predictions yet
        """
        if self.clue_count == 0:
            return None

        top_predictions = self.bayesian.get_top_predictions(top_k=1)
        if top_predictions:
            return top_predictions[0].entity.canonical_name

        return None

    def get_confidence_at_clue(self, clue_number: int) -> Optional[float]:
        """
        Get top prediction confidence after specific clue number.

        Useful for performance analysis (e.g., "confidence at Clue 3").

        Args:
            clue_number: Clue number (1-5)

        Returns:
            Confidence percentage, or None if that clue hasn't been processed
        """
        if clue_number > self.clue_count:
            return None

        # Get current top prediction
        top_predictions = self.bayesian.get_top_predictions(top_k=1)
        if top_predictions:
            return top_predictions[0].probability * 100

        return None

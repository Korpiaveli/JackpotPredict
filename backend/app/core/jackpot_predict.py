"""
JackpotPredict - Main orchestrator for trivia answer prediction.

GEMINI-FIRST ARCHITECTURE (v2.0)
================================
This is the simplified, Gemini-first prediction engine that replaces the
previous hybrid Bayesian+LLM system.

Key components:
- GeminiPredictor: Primary prediction engine (Gemini 2.0 Flash)
- SpellingValidator: Critical canonical name validation (prevents elimination)
- ContextManager: Few-shot example selection from history.json

The Bayesian, ClueAnalyzer, and LLM Interpreter modules have been removed
as Gemini handles all reasoning natively with better accuracy.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from uuid import uuid4
import time
import logging

from .entity_registry import EntityRegistry, EntityCategory
from .spelling_validator import SpellingValidator
from .gemini_predictor import (
    get_gemini_predictor,
    GeminiPredictor,
    GeminiResponse,
    GeminiPrediction
)
from .hybrid_validation import (
    HybridValidationService,
    DualPredictionResult,
    get_hybrid_service
)
from .openai_predictor import OpenAIPrediction
from .response_validator import (
    Prediction,
    PredictionResponse,
    GuessRecommendation,
    build_guess_recommendation,
    build_category_probabilities,
    create_wait_response,
    create_error_response
)
from .config import get_openai_validator_config

logger = logging.getLogger(__name__)


class JackpotPredict:
    """
    Main orchestrator for the trivia prediction engine.

    GEMINI-FIRST ARCHITECTURE:
    1. GeminiPredictor gets top 3 predictions with reasoning
    2. SpellingValidator ensures canonical name accuracy (critical!)
    3. ResponseValidator formats for frontend API contract

    The old Bayesian/ClueAnalyzer/HybridCombiner system has been removed
    in favor of simpler, more accurate Gemini-only prediction.
    """

    # Category priors (60/25/15 distribution from game statistics)
    DEFAULT_CATEGORY_PRIORS = {
        "thing": 0.60,
        "place": 0.25,
        "person": 0.15,
    }

    def __init__(
        self,
        entity_registry: EntityRegistry,
        spelling_validator: Optional[SpellingValidator] = None,
        enable_hybrid_validation: bool = True
    ):
        """
        Initialize JackpotPredict orchestrator.

        Args:
            entity_registry: Initialized EntityRegistry for spelling validation
            spelling_validator: Optional SpellingValidator (will create if None)
            enable_hybrid_validation: Enable parallel OpenAI validation (default True)
        """
        self.registry = entity_registry
        self.validator = spelling_validator or SpellingValidator(entity_registry)
        self.enable_hybrid_validation = enable_hybrid_validation

        # Session state
        self.session_id = str(uuid4())
        self.clue_count = 0
        self.clue_history: List[str] = []
        self.category_probs = self.DEFAULT_CATEGORY_PRIORS.copy()
        self.last_agreement_level: Optional[str] = None  # Track validation agreement

        # Predictors (lazy initialized)
        self._gemini: Optional[GeminiPredictor] = None
        self._hybrid_service: Optional[HybridValidationService] = None

        logger.info(f"JackpotPredict initialized (session: {self.session_id}, hybrid={enable_hybrid_validation})")

    async def _get_gemini(self) -> GeminiPredictor:
        """Get or create Gemini predictor."""
        if self._gemini is None:
            self._gemini = await get_gemini_predictor()
        return self._gemini

    async def _get_hybrid_service(self) -> HybridValidationService:
        """Get or create hybrid validation service."""
        if self._hybrid_service is None:
            self._hybrid_service = await get_hybrid_service()
        return self._hybrid_service

    def _is_hybrid_enabled(self) -> bool:
        """Check if hybrid validation should be used."""
        if not self.enable_hybrid_validation:
            return False
        config = get_openai_validator_config()
        return config["enabled"]

    def add_clue(self, clue_text: str) -> PredictionResponse:
        """
        DEPRECATED: Use add_clue_async() for Gemini predictions.

        This synchronous method is kept for backwards compatibility
        but returns a WAIT response directing to use async.
        """
        logger.warning("Synchronous add_clue() called - use add_clue_async() for Gemini predictions")

        self.clue_count += 1
        self.clue_history.append(clue_text)

        return create_wait_response(
            session_id=self.session_id,
            clue_number=self.clue_count,
            clue_history=self.clue_history,
            reason="Use async API for Gemini predictions"
        )

    async def add_clue_async(self, clue_text: str) -> dict:
        """
        Analyze a new clue with dual AI prediction (Gemini + OpenAI in parallel).

        This is the main entry point for the prediction engine.

        Flow:
        1. Build context with clue history
        2. Run Gemini and OpenAI predictions in parallel
        3. Find agreements between both AIs
        4. Validate spelling of all predictions
        5. Build guess recommendation based on agreements
        6. Return both prediction lists with agreement analysis

        Args:
            clue_text: The clue text to analyze

        Returns:
            Dict with dual predictions and agreement analysis
        """
        start_time = time.time()

        # Increment clue counter
        self.clue_count += 1
        self.clue_history.append(clue_text)
        logger.info(f"Processing Clue {self.clue_count}: '{clue_text}'")

        # Determine category hint from previous predictions or priors
        category_hint = self._get_category_hint()

        # Always use dual prediction now
        hybrid_service = await self._get_hybrid_service()
        dual_result = await hybrid_service.predict_dual(
            clues=self.clue_history,
            category_hint=category_hint
        )

        # Validate Gemini predictions
        validated_gemini = self._validate_predictions(dual_result.gemini_predictions)
        validated_openai = self._validate_openai_predictions(dual_result.openai_predictions)

        # Update category probabilities from Gemini predictions
        self.category_probs = build_category_probabilities(validated_gemini)

        # Build guess recommendation based on agreement strength
        top_confidence = validated_gemini[0].confidence if validated_gemini else 0.0
        if dual_result.agreement_strength == "strong":
            # Both AIs agree - boost confidence in recommendation
            rationale = f"BOTH AIs agree: {dual_result.recommended_pick}"
        elif dual_result.agreement_strength == "moderate":
            rationale = f"Agreement found: {dual_result.agreements}"
        else:
            rationale = f"AIs differ - Gemini: {dual_result.top_gemini}, OpenAI: {dual_result.top_openai}"

        guess_rec = build_guess_recommendation(
            top_confidence=top_confidence,
            clue_number=self.clue_count,
            key_insight=rationale
        )

        elapsed_time = time.time() - start_time

        # Log result
        logger.info(
            f"Clue {self.clue_count} processed in {elapsed_time:.3f}s. "
            f"Gemini: {dual_result.top_gemini}, OpenAI: {dual_result.top_openai}, "
            f"Agreements: {dual_result.agreements}, Recommended: {dual_result.recommended_pick}"
        )

        # Return the new dual prediction format
        return {
            "session_id": self.session_id,
            "clue_number": self.clue_count,
            "gemini_predictions": validated_gemini,
            "openai_predictions": validated_openai,
            "agreements": dual_result.agreements,
            "agreement_strength": dual_result.agreement_strength,
            "recommended_pick": dual_result.recommended_pick,
            "predictions": validated_gemini,  # Backwards compatibility
            "guess_recommendation": guess_rec,
            "elapsed_time": elapsed_time,
            "clue_history": self.clue_history.copy(),
            "category_probabilities": self.category_probs,
            "gemini_insight": dual_result.gemini_key_insight,
            "openai_insight": dual_result.openai_key_insight,
        }

    def _get_category_hint(self) -> Optional[str]:
        """Get category hint from current probabilities."""
        if not self.category_probs:
            return None

        # Return category with highest probability
        top_cat = max(self.category_probs.items(), key=lambda x: x[1])
        if top_cat[1] > 0.5:  # Only hint if confident
            return top_cat[0]
        return None

    def _validate_predictions(
        self,
        gemini_predictions: List[GeminiPrediction]
    ) -> List[Prediction]:
        """
        Validate and format Gemini predictions.

        CRITICAL: Spelling validation prevents elimination in the game.
        One typo = you're out.

        Args:
            gemini_predictions: Raw predictions from Gemini

        Returns:
            List of validated Prediction objects
        """
        validated = []

        for pred in gemini_predictions:
            # Skip WAIT responses
            if pred.answer.upper() == "WAIT":
                validated.append(Prediction(
                    answer="WAIT",
                    confidence=0.0,
                    category=pred.category,
                    reasoning="Waiting for more clues",
                    spelling_valid=True,
                    canonical_name=None
                ))
                continue

            # Validate spelling against entity database
            validation = self.validator.validate(pred.answer)

            if validation.is_valid:
                # Use canonical spelling from database
                canonical = validation.formatted_answer
                spelling_valid = True
                logger.debug(f"Spelling valid: '{pred.answer}' -> '{canonical}'")
            else:
                # Validation already does fuzzy matching and provides suggestion
                if validation.suggestion:
                    canonical = validation.suggestion
                    spelling_valid = True
                    logger.info(f"Fuzzy match: '{pred.answer}' -> '{canonical}'")
                else:
                    # Use LLM answer as-is (risky but better than nothing)
                    canonical = pred.answer
                    spelling_valid = False
                    logger.warning(f"No spelling match for: '{pred.answer}'")

            validated.append(Prediction(
                answer=canonical,
                confidence=pred.confidence,
                category=pred.category,
                reasoning=pred.reasoning,
                spelling_valid=spelling_valid,
                canonical_name=canonical if spelling_valid else None
            ))

        return validated

    def _validate_openai_predictions(
        self,
        openai_predictions: List[OpenAIPrediction]
    ) -> List[Prediction]:
        """
        Validate and format OpenAI predictions.

        Same validation as Gemini predictions.
        """
        validated = []

        for pred in openai_predictions:
            # Skip WAIT responses
            if pred.answer.upper() == "WAIT":
                validated.append(Prediction(
                    answer="WAIT",
                    confidence=0.0,
                    category=pred.category,
                    reasoning="Waiting for more clues",
                    spelling_valid=True,
                    canonical_name=None
                ))
                continue

            # Validate spelling against entity database
            validation = self.validator.validate(pred.answer)

            if validation.is_valid:
                canonical = validation.formatted_answer
                spelling_valid = True
            else:
                if validation.suggestion:
                    canonical = validation.suggestion
                    spelling_valid = True
                else:
                    canonical = pred.answer
                    spelling_valid = False

            validated.append(Prediction(
                answer=canonical,
                confidence=pred.confidence,
                category=pred.category,
                reasoning=pred.reasoning,
                spelling_valid=spelling_valid,
                canonical_name=canonical if spelling_valid else None
            ))

        return validated

    def reset(self):
        """
        Reset session for a new puzzle.

        Clears clue history, probabilities, and generates new session ID.
        """
        self.session_id = str(uuid4())
        self.clue_count = 0
        self.clue_history.clear()
        self.category_probs = self.DEFAULT_CATEGORY_PRIORS.copy()
        self.last_agreement_level = None

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
            "clue_history": self.clue_history.copy(),
            "category_probs": self.category_probs.copy()
        }

    async def predict_all_clues(self, clues: List[str]) -> List[PredictionResponse]:
        """
        Process all clues sequentially (async version).

        Useful for batch testing with historical puzzles.

        Args:
            clues: List of 1-5 clue texts

        Returns:
            List of PredictionResponse objects (one per clue)
        """
        self.reset()
        responses = []

        for clue_text in clues:
            response = await self.add_clue_async(clue_text)
            responses.append(response)

        return responses

    def get_top_answer(self) -> Optional[str]:
        """
        Get the current top predicted answer.

        Note: In Gemini-first architecture, we don't track predictions
        between clues. Use the response from add_clue_async() instead.

        Returns:
            None (deprecated - use response from add_clue_async)
        """
        logger.warning("get_top_answer() deprecated in Gemini-first architecture")
        return None


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_jackpot_predict(entity_registry: EntityRegistry) -> JackpotPredict:
    """
    Factory function to create JackpotPredict instance.

    Args:
        entity_registry: Initialized EntityRegistry

    Returns:
        Configured JackpotPredict instance
    """
    return JackpotPredict(entity_registry=entity_registry)

"""
Hybrid Validation Service - Parallel dual AI prediction with agreement detection.

Runs Gemini and OpenAI predictors in true parallel, then finds agreements
between their predictions. No complex reconciliation - just show both lists.
"""

import asyncio
import logging
from typing import Optional, List, Set
from dataclasses import dataclass

from app.core.gemini_predictor import (
    GeminiPredictor,
    GeminiResponse,
    GeminiPrediction,
    get_gemini_predictor
)
from app.core.openai_predictor import (
    OpenAIPredictor,
    OpenAIResponse,
    OpenAIPrediction,
    get_openai_predictor
)

logger = logging.getLogger(__name__)


@dataclass
class DualPredictionResult:
    """Result from parallel Gemini + OpenAI predictions."""
    gemini_predictions: List[GeminiPrediction]
    openai_predictions: List[OpenAIPrediction]
    agreements: List[str]  # Answers that appear in both top-3
    agreement_strength: str  # "strong" (both #1), "moderate" (both top-3), "none"
    recommended_pick: str  # Top agreement or top Gemini
    gemini_key_insight: str
    openai_key_insight: str
    gemini_available: bool
    openai_available: bool

    @property
    def has_agreement(self) -> bool:
        """Check if both AIs agree on any answer."""
        return len(self.agreements) > 0

    @property
    def top_gemini(self) -> Optional[str]:
        """Get Gemini's #1 prediction."""
        if self.gemini_predictions:
            return self.gemini_predictions[0].answer
        return None

    @property
    def top_openai(self) -> Optional[str]:
        """Get OpenAI's #1 prediction."""
        if self.openai_predictions:
            return self.openai_predictions[0].answer
        return None


class HybridValidationService:
    """
    Parallel dual AI prediction service.

    Runs both Gemini and OpenAI simultaneously, then finds agreements.
    No complex reconciliation - just transparency about what each AI thinks.
    """

    def __init__(self):
        self._gemini: Optional[GeminiPredictor] = None
        self._openai: Optional[OpenAIPredictor] = None

    async def _get_gemini(self) -> GeminiPredictor:
        """Get Gemini predictor instance."""
        if self._gemini is None:
            self._gemini = await get_gemini_predictor()
        return self._gemini

    async def _get_openai(self) -> OpenAIPredictor:
        """Get OpenAI predictor instance."""
        if self._openai is None:
            self._openai = await get_openai_predictor()
        return self._openai

    async def predict_dual(
        self,
        clues: List[str],
        category_hint: Optional[str] = None
    ) -> DualPredictionResult:
        """
        Get predictions from both Gemini and OpenAI in parallel.

        Args:
            clues: List of clues seen so far
            category_hint: Optional category hint

        Returns:
            DualPredictionResult with both prediction lists and agreements
        """
        gemini = await self._get_gemini()
        openai = await self._get_openai()

        # Run both predictors in TRUE parallel
        logger.info("Running Gemini and OpenAI predictions in parallel...")

        gemini_task = gemini.predict(clues, category_hint)
        openai_task = openai.predict(clues, category_hint)

        # Wait for both to complete
        gemini_result, openai_result = await asyncio.gather(
            gemini_task,
            openai_task,
            return_exceptions=True
        )

        # Handle exceptions
        if isinstance(gemini_result, Exception):
            logger.error(f"Gemini prediction failed: {gemini_result}")
            gemini_result = None
        if isinstance(openai_result, Exception):
            logger.error(f"OpenAI prediction failed: {openai_result}")
            openai_result = None

        # Extract predictions
        gemini_preds = gemini_result.predictions if gemini_result else []
        openai_preds = openai_result.predictions if openai_result else []
        gemini_insight = gemini_result.key_insight if gemini_result else ""
        openai_insight = openai_result.key_insight if openai_result else ""

        # Find agreements
        agreements, strength = self._find_agreements(gemini_preds, openai_preds)

        # Determine recommended pick
        recommended = self._get_recommended_pick(gemini_preds, openai_preds, agreements)

        logger.info(
            f"Dual prediction complete: "
            f"Gemini={gemini_preds[0].answer if gemini_preds else 'N/A'}, "
            f"OpenAI={openai_preds[0].answer if openai_preds else 'N/A'}, "
            f"Agreements={agreements}, Recommended={recommended}"
        )

        return DualPredictionResult(
            gemini_predictions=gemini_preds,
            openai_predictions=self._convert_openai_predictions(openai_preds),
            agreements=agreements,
            agreement_strength=strength,
            recommended_pick=recommended,
            gemini_key_insight=gemini_insight,
            openai_key_insight=openai_insight,
            gemini_available=gemini_result is not None,
            openai_available=openai_result is not None and openai_result.is_valid
        )

    def _convert_openai_predictions(
        self,
        openai_preds: List[OpenAIPrediction]
    ) -> List[OpenAIPrediction]:
        """Convert OpenAI predictions (already correct type)."""
        return openai_preds

    def _find_agreements(
        self,
        gemini_preds: List[GeminiPrediction],
        openai_preds: List[OpenAIPrediction]
    ) -> tuple[List[str], str]:
        """
        Find answers that appear in both prediction lists.

        Returns:
            Tuple of (agreement_list, strength)
            - strength: "strong" if both #1, "moderate" if both top-3, "none"
        """
        if not gemini_preds or not openai_preds:
            return [], "none"

        # Normalize answers for comparison (lowercase, strip)
        gemini_answers = {p.answer.lower().strip(): p.answer for p in gemini_preds}
        openai_answers = {p.answer.lower().strip(): p.answer for p in openai_preds}

        # Find overlapping answers
        common_keys = set(gemini_answers.keys()) & set(openai_answers.keys())

        if not common_keys:
            return [], "none"

        # Use the canonical form from Gemini
        agreements = [gemini_answers[k] for k in common_keys]

        # Determine strength
        gemini_top = gemini_preds[0].answer.lower().strip()
        openai_top = openai_preds[0].answer.lower().strip()

        if gemini_top == openai_top:
            strength = "strong"  # Both #1 agree
        else:
            strength = "moderate"  # Agreement somewhere in top-3

        return agreements, strength

    def _get_recommended_pick(
        self,
        gemini_preds: List[GeminiPrediction],
        openai_preds: List[OpenAIPrediction],
        agreements: List[str]
    ) -> str:
        """
        Get the recommended answer.

        Priority:
        1. If both agree on #1, use that
        2. If there's any agreement, use highest-ranked agreement
        3. Otherwise, use Gemini's #1
        """
        if not gemini_preds:
            if openai_preds:
                return openai_preds[0].answer
            return ""

        # If strong agreement (both #1), use it
        if agreements and gemini_preds[0].answer in agreements:
            return gemini_preds[0].answer

        # If any agreement, find the highest-ranked one
        if agreements:
            # Find which agreement has highest combined rank
            for pred in gemini_preds:
                if pred.answer in agreements:
                    return pred.answer

        # Default to Gemini's #1
        return gemini_preds[0].answer


# Singleton instance
_hybrid_service: Optional[HybridValidationService] = None


async def get_hybrid_service() -> HybridValidationService:
    """Get singleton hybrid validation service instance."""
    global _hybrid_service
    if _hybrid_service is None:
        _hybrid_service = HybridValidationService()
    return _hybrid_service

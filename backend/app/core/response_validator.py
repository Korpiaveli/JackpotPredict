"""
Response Validator - JSON validation and response formatting for Gemini predictions.

This module provides:
- Pydantic models for type-safe validation
- Confidence recalibration
- API response formatting
- Error handling and fallbacks
"""

import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)


# ============================================================================
# PYDANTIC MODELS FOR VALIDATION
# ============================================================================

class PredictionItem(BaseModel):
    """Single prediction from Gemini."""
    rank: int = Field(ge=1, le=3)
    answer: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    category: str = Field(pattern=r'^(person|place|thing)$')
    reasoning: str = Field(default="", max_length=200)

    @field_validator('confidence', mode='before')
    @classmethod
    def normalize_confidence(cls, v):
        """Convert 0-100 scale to 0-1 if needed."""
        if isinstance(v, (int, float)):
            if v > 1:
                return v / 100.0
        return v

    @field_validator('category', mode='before')
    @classmethod
    def normalize_category(cls, v):
        """Normalize category to lowercase."""
        if isinstance(v, str):
            return v.lower().strip()
        return v

    @field_validator('answer', mode='before')
    @classmethod
    def clean_answer(cls, v):
        """Clean up answer text."""
        if isinstance(v, str):
            return v.strip().strip('"\'')
        return v


class GeminiResponseModel(BaseModel):
    """Validated Gemini response structure."""
    predictions: List[PredictionItem] = Field(min_length=1, max_length=3)
    should_guess: bool = True
    key_insight: str = Field(default="", max_length=300)

    @model_validator(mode='after')
    def validate_predictions(self):
        """Ensure predictions are sorted by confidence and properly ranked."""
        # Sort by confidence descending
        self.predictions = sorted(
            self.predictions,
            key=lambda p: p.confidence,
            reverse=True
        )
        # Re-assign ranks
        for i, pred in enumerate(self.predictions):
            pred.rank = i + 1
        return self


# ============================================================================
# API RESPONSE MODELS (matches frontend contract)
# ============================================================================

@dataclass
class Prediction:
    """API prediction response (frontend contract)."""
    answer: str
    confidence: float
    category: str
    reasoning: str = ""
    spelling_valid: bool = True
    canonical_name: Optional[str] = None


@dataclass
class GuessRecommendation:
    """Guess recommendation for frontend."""
    should_guess: bool
    confidence_threshold: float
    rationale: str


@dataclass
class PredictionResponse:
    """Complete API response (matches frontend contract)."""
    session_id: str
    clue_number: int
    predictions: List[Prediction]
    guess_recommendation: GuessRecommendation
    elapsed_time: float
    clue_history: List[str]
    category_probabilities: Dict[str, float]
    key_insight: str = ""
    validation_agreement: Optional[str] = None  # "strong", "moderate", "disagreement", "unavailable"


# ============================================================================
# VALIDATION UTILITIES
# ============================================================================

def validate_gemini_response(raw_data: Dict[str, Any]) -> Optional[GeminiResponseModel]:
    """
    Validate raw Gemini response data against Pydantic model.

    Args:
        raw_data: Parsed JSON dictionary from Gemini

    Returns:
        Validated GeminiResponseModel or None if invalid
    """
    try:
        return GeminiResponseModel(**raw_data)
    except Exception as e:
        logger.warning(f"Gemini response validation failed: {e}")
        return None


def recalibrate_confidence(
    raw_confidence: float,
    clue_number: int,
    is_early_solve_pattern: bool = False
) -> float:
    """
    Adjust LLM confidence based on clue number and patterns.

    LLMs tend to be overconfident on early clues. This applies
    empirically-tuned correction factors.

    Args:
        raw_confidence: Raw confidence from LLM (0.0-1.0)
        clue_number: Current clue number (1-5)
        is_early_solve_pattern: True if matches common early-solve patterns

    Returns:
        Calibrated confidence (0.0-1.0)
    """
    if clue_number <= 1:
        # Very conservative on clue 1 unless strong pattern
        factor = 0.80 if is_early_solve_pattern else 0.70
        return raw_confidence * factor
    elif clue_number == 2:
        factor = 0.90 if is_early_solve_pattern else 0.85
        return raw_confidence * factor
    elif clue_number == 3:
        # Clue 3 is the inflection point - mild adjustment
        return raw_confidence * 0.95
    elif clue_number >= 4:
        # Later clues are more reliable - slight boost
        return min(0.98, raw_confidence * 1.03)

    return raw_confidence


def build_guess_recommendation(
    top_confidence: float,
    clue_number: int,
    key_insight: str = ""
) -> GuessRecommendation:
    """
    Build guess recommendation based on confidence and clue number.

    Threshold strategy:
    - Clue 1: Need 75%+ (very risky early guess)
    - Clue 2: Need 65%+ (risky but acceptable)
    - Clue 3: Need 55%+ (balanced risk)
    - Clue 4: Need 45%+ (safer to guess)
    - Clue 5: Need 35%+ (last chance, guess almost anything)

    Args:
        top_confidence: Confidence of top prediction (0.0-1.0)
        clue_number: Current clue number (1-5)
        key_insight: Key insight from LLM for rationale

    Returns:
        GuessRecommendation with should_guess, threshold, and rationale
    """
    # Dynamic thresholds based on clue number
    thresholds = {
        1: 0.75,  # Very conservative early
        2: 0.65,
        3: 0.55,
        4: 0.45,
        5: 0.35,  # Aggressive on last clue
    }

    threshold = thresholds.get(clue_number, 0.50)
    should_guess = top_confidence >= threshold

    # Build rationale
    if should_guess:
        if clue_number <= 2:
            rationale = f"High confidence ({top_confidence:.0%}) on early clue warrants guess. {key_insight}"
        else:
            rationale = f"Confidence ({top_confidence:.0%}) meets threshold ({threshold:.0%}). {key_insight}"
    else:
        if clue_number < 5:
            rationale = f"Confidence ({top_confidence:.0%}) below threshold ({threshold:.0%}). Wait for more clues."
        else:
            rationale = f"Low confidence ({top_confidence:.0%}) but it's Clue 5 - consider guessing anyway."
            # On clue 5, we might still recommend guessing even below threshold
            if top_confidence >= 0.25:
                should_guess = True
                rationale = f"Clue 5 with {top_confidence:.0%} confidence - recommend guessing. {key_insight}"

    return GuessRecommendation(
        should_guess=should_guess,
        confidence_threshold=threshold,
        rationale=rationale.strip()[:200]
    )


def build_category_probabilities(
    predictions: List[Prediction]
) -> Dict[str, float]:
    """
    Calculate category probabilities from predictions.

    Uses weighted average based on prediction confidence.

    Args:
        predictions: List of predictions with categories

    Returns:
        Dict with person/place/thing probabilities (sum to 1.0)
    """
    if not predictions:
        # Default priors from game statistics
        return {"person": 0.15, "place": 0.25, "thing": 0.60}

    # Weighted category votes
    category_weights = {"person": 0.0, "place": 0.0, "thing": 0.0}
    total_weight = 0.0

    for pred in predictions:
        cat = pred.category.lower()
        if cat in category_weights:
            category_weights[cat] += pred.confidence
            total_weight += pred.confidence

    if total_weight == 0:
        return {"person": 0.15, "place": 0.25, "thing": 0.60}

    # Normalize to sum to 1.0
    return {
        cat: weight / total_weight
        for cat, weight in category_weights.items()
    }


def create_wait_response(
    session_id: str,
    clue_number: int,
    clue_history: List[str],
    reason: str = "Insufficient confidence"
) -> PredictionResponse:
    """
    Create a WAIT response when LLM confidence is too low.

    Args:
        session_id: Current session ID
        clue_number: Current clue number
        clue_history: History of clues
        reason: Reason for waiting

    Returns:
        PredictionResponse with WAIT recommendation
    """
    wait_prediction = Prediction(
        answer="WAIT",
        confidence=0.0,
        category="thing",
        reasoning=reason,
        spelling_valid=True
    )

    return PredictionResponse(
        session_id=session_id,
        clue_number=clue_number,
        predictions=[wait_prediction],
        guess_recommendation=GuessRecommendation(
            should_guess=False,
            confidence_threshold=0.50,
            rationale=reason
        ),
        elapsed_time=0.0,
        clue_history=clue_history,
        category_probabilities={"person": 0.15, "place": 0.25, "thing": 0.60},
        key_insight=""
    )


def create_error_response(
    session_id: str,
    clue_number: int,
    clue_history: List[str],
    error_message: str = "Prediction service error"
) -> PredictionResponse:
    """
    Create an error response when prediction fails.

    Args:
        session_id: Current session ID
        clue_number: Current clue number
        clue_history: History of clues
        error_message: Error description

    Returns:
        PredictionResponse with error info
    """
    error_prediction = Prediction(
        answer="ERROR",
        confidence=0.0,
        category="thing",
        reasoning=error_message,
        spelling_valid=False
    )

    return PredictionResponse(
        session_id=session_id,
        clue_number=clue_number,
        predictions=[error_prediction],
        guess_recommendation=GuessRecommendation(
            should_guess=False,
            confidence_threshold=1.0,
            rationale=f"Error: {error_message}"
        ),
        elapsed_time=0.0,
        clue_history=clue_history,
        category_probabilities={"person": 0.15, "place": 0.25, "thing": 0.60},
        key_insight=""
    )

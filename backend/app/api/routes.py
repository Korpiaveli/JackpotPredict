"""
FastAPI Routes - REST API endpoints for JackpotPredict.

Endpoints:
- POST /api/predict - Submit clue and get predictions
- POST /api/reset - Reset session for new puzzle
- POST /api/validate - Validate answer spelling
- GET /api/health - Health check and metrics
"""

import time
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.api.models import (
    ClueRequest,
    PredictionResponse,
    Prediction,
    GuessRecommendation,
    ResetRequest,
    ResetResponse,
    ValidationRequest,
    ValidationResponse,
    HealthResponse,
    ErrorResponse,
    EntityCategory
)
from app.core.jackpot_predict import JackpotPredict
from app.core.spelling_validator import SpellingValidator
from app.core.entity_registry import EntityRegistry
from app.core.clue_analyzer import ClueAnalyzer

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/api", tags=["predictions"])

# Global state
_sessions: Dict[str, JackpotPredict] = {}
_session_timestamps: Dict[str, datetime] = {}
_server_start_time = datetime.now()
_entity_registry: Optional[EntityRegistry] = None
_clue_analyzer: Optional[ClueAnalyzer] = None
_spelling_validator: Optional[SpellingValidator] = None

# Session expiry time (5 minutes)
SESSION_EXPIRY_MINUTES = 5


def get_entity_registry() -> EntityRegistry:
    """Get or initialize the entity registry singleton."""
    global _entity_registry
    if _entity_registry is None:
        _entity_registry = EntityRegistry()
        logger.info(f"Entity registry initialized with {_entity_registry.get_entity_count()} entities")
    return _entity_registry


def get_clue_analyzer() -> ClueAnalyzer:
    """Get or initialize the clue analyzer singleton."""
    global _clue_analyzer
    if _clue_analyzer is None:
        _clue_analyzer = ClueAnalyzer()
        logger.info("Clue analyzer initialized")
    return _clue_analyzer


def get_spelling_validator() -> SpellingValidator:
    """Get or initialize the spelling validator singleton."""
    global _spelling_validator
    if _spelling_validator is None:
        _spelling_validator = SpellingValidator(get_entity_registry())
        logger.info("Spelling validator initialized")
    return _spelling_validator


def cleanup_expired_sessions():
    """Remove sessions older than SESSION_EXPIRY_MINUTES."""
    global _sessions, _session_timestamps

    now = datetime.now()
    expired_ids = []

    for session_id, timestamp in _session_timestamps.items():
        if now - timestamp > timedelta(minutes=SESSION_EXPIRY_MINUTES):
            expired_ids.append(session_id)

    for session_id in expired_ids:
        _sessions.pop(session_id, None)
        _session_timestamps.pop(session_id, None)

    if expired_ids:
        logger.info(f"Cleaned up {len(expired_ids)} expired sessions")


def get_or_create_session(session_id: Optional[str] = None) -> tuple[str, JackpotPredict, bool]:
    """
    Get existing session or create new one.

    Args:
        session_id: Optional existing session ID

    Returns:
        Tuple of (session_id, predictor, is_new)
    """
    global _sessions, _session_timestamps

    # Cleanup expired sessions
    cleanup_expired_sessions()

    # Create new session if no ID provided or session doesn't exist
    if session_id is None or session_id not in _sessions:
        new_session_id = str(uuid.uuid4())
        predictor = JackpotPredict(
            entity_registry=get_entity_registry(),
            clue_analyzer=get_clue_analyzer()
        )
        _sessions[new_session_id] = predictor
        _session_timestamps[new_session_id] = datetime.now()
        logger.info(f"Created new session: {new_session_id}")
        return new_session_id, predictor, True

    # Update timestamp for existing session
    _session_timestamps[session_id] = datetime.now()
    return session_id, _sessions[session_id], False


@router.post(
    "/predict",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit clue and get predictions",
    description="Analyze a clue and return top 3 predictions with confidence scores"
)
async def predict(request: ClueRequest) -> PredictionResponse:
    """
    Submit a clue and get top 3 predictions.

    This is the main endpoint for the prediction engine. Submit clues sequentially
    (1-5) and the system will maintain session state, updating probabilities
    based on all clues seen so far.
    """
    start_time = time.time()

    try:
        # Get or create session
        session_id, predictor, is_new = get_or_create_session(request.session_id)

        # Add clue to predictor
        logger.info(f"Session {session_id}: Processing clue #{predictor.clue_count + 1}: '{request.clue_text}'")
        prediction_result = predictor.add_clue(request.clue_text)

        # Convert to API response format
        predictions = [
            Prediction(
                rank=i + 1,
                answer=pred.answer,
                confidence=pred.confidence / 100.0,  # Convert from percentage (0-100) to fraction (0-1)
                category=EntityCategory(pred.category),
                reasoning=pred.reasoning
            )
            for i, pred in enumerate(prediction_result.predictions)
        ]

        # Build guess recommendation
        # Get threshold for current clue number (from JackpotPredict.GUESS_THRESHOLDS)
        threshold_map = {1: 0.50, 2: 0.65, 3: 0.75, 4: 0.85, 5: 0.0}
        threshold = threshold_map.get(predictor.clue_count, 0.75)

        # Build rationale string
        top_conf = predictions[0].confidence if predictions else 0.0
        if prediction_result.should_guess:
            rationale = f"Clue {predictor.clue_count}: Confidence {top_conf:.0%} exceeds {threshold:.0%} threshold - recommended to guess"
        else:
            rationale = f"Clue {predictor.clue_count}: Confidence {top_conf:.0%} below {threshold:.0%} threshold - continue to next clue"

        guess_rec = GuessRecommendation(
            should_guess=prediction_result.should_guess,
            confidence_threshold=threshold,
            rationale=rationale
        )

        # Calculate elapsed time
        elapsed = time.time() - start_time

        # Build clue history from Bayesian updater's stored clue texts
        clue_texts = [clue.clue_text for clue in predictor.bayesian.clue_history]

        response = PredictionResponse(
            session_id=session_id,
            clue_number=predictor.clue_count,
            predictions=predictions,
            guess_recommendation=guess_rec,
            elapsed_time=elapsed,
            clue_history=clue_texts,
            category_probabilities={
                "thing": predictor.category_probs.get(EntityCategory.THING, 0.0),
                "place": predictor.category_probs.get(EntityCategory.PLACE, 0.0),
                "person": predictor.category_probs.get(EntityCategory.PERSON, 0.0)
            }
        )

        logger.info(
            f"Session {session_id}: Clue #{predictor.clue_count} processed in {elapsed:.2f}s "
            f"- Top: {predictions[0].answer if predictions else 'None'} "
            f"({predictions[0].confidence:.2%} confidence)" if predictions else ""
        )

        return response

    except Exception as e:
        logger.error(f"Error processing prediction: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )


@router.post(
    "/reset",
    response_model=ResetResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset session for new puzzle",
    description="Clear session state and start a new puzzle"
)
async def reset(request: ResetRequest) -> ResetResponse:
    """
    Reset session for a new puzzle.

    If session_id is provided, clears that session's state.
    If not provided, creates a new session.
    """
    global _sessions, _session_timestamps

    try:
        if request.session_id and request.session_id in _sessions:
            # Remove existing session
            _sessions.pop(request.session_id, None)
            _session_timestamps.pop(request.session_id, None)
            logger.info(f"Reset session: {request.session_id}")

        # Create new session
        new_session_id = str(uuid.uuid4())
        predictor = JackpotPredict()
        _sessions[new_session_id] = predictor
        _session_timestamps[new_session_id] = datetime.now()

        logger.info(f"Created new session after reset: {new_session_id}")

        return ResetResponse(
            session_id=new_session_id,
            message="Session reset successfully. Ready for new puzzle."
        )

    except Exception as e:
        logger.error(f"Error resetting session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reset failed: {str(e)}"
        )


@router.post(
    "/validate",
    response_model=ValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate answer spelling",
    description="Check if an answer is spelled correctly and get suggestions"
)
async def validate(request: ValidationRequest) -> ValidationResponse:
    """
    Validate answer spelling against entity registry.

    Returns canonical spelling if valid, or suggestions if invalid.
    Critical for ensuring no typos that would eliminate player.
    """
    try:
        validator = get_spelling_validator()
        result = validator.validate(request.answer)

        logger.info(
            f"Validation: '{request.answer}' -> "
            f"{'VALID' if result.is_valid else 'INVALID'} "
            f"({result.error_type or 'OK'})"
        )

        return ValidationResponse(
            is_valid=result.is_valid,
            canonical_spelling=result.canonical_spelling,
            error_type=result.error_type,
            suggestion=result.suggestion,
            fuzzy_matches=result.fuzzy_matches
        )

    except Exception as e:
        logger.error(f"Error validating answer: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}"
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Get service health status and metrics"
)
async def health() -> HealthResponse:
    """
    Health check endpoint.

    Returns service status, entity count, active sessions, and uptime.
    """
    try:
        # Cleanup expired sessions first
        cleanup_expired_sessions()

        registry = get_entity_registry()
        uptime = (datetime.now() - _server_start_time).total_seconds()

        return HealthResponse(
            status="healthy",
            version="1.0.0",
            entity_count=registry.get_entity_count(),
            active_sessions=len(_sessions),
            uptime_seconds=uptime
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}"
        )


# Exception handlers are now in server.py

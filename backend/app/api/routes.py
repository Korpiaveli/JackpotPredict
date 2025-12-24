"""
FastAPI Routes - REST API endpoints for JackpotPredict.

GEMINI-FIRST ARCHITECTURE (v2.0)
================================
Simplified routes using Gemini as the primary prediction engine.
Removed hybrid/Bayesian endpoints as they're no longer needed.

Endpoints:
- POST /api/predict - Submit clue and get predictions
- POST /api/reset - Reset session for new puzzle
- POST /api/validate - Validate answer spelling
- POST /api/feedback - Submit puzzle feedback for learning
- GET /api/health - Health check and metrics
"""

import time
import uuid
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
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
    EntityCategory,
    SemanticMatch,
    FeedbackRequest,
    FeedbackResponse
)
from app.core.jackpot_predict import JackpotPredict
from app.core.spelling_validator import SpellingValidator
from app.core.entity_registry import EntityRegistry

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/api", tags=["predictions"])

# Global state
_sessions: Dict[str, JackpotPredict] = {}
_session_timestamps: Dict[str, datetime] = {}
_server_start_time = datetime.now()
_entity_registry: Optional[EntityRegistry] = None
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
            entity_registry=get_entity_registry()
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
    summary="Submit clue and get dual AI predictions",
    description="Analyze a clue with both Gemini and OpenAI in parallel, showing agreements"
)
async def predict(request: ClueRequest) -> PredictionResponse:
    """
    Submit a clue and get predictions from both Gemini and OpenAI.

    This is the main endpoint for the prediction engine. Submit clues sequentially
    (1-5) and the system will maintain session state, providing predictions
    based on all clues seen so far.

    Both AIs predict independently using the same strategy-informed prompt.
    Agreements between AIs are highlighted as high-confidence signals.
    """
    start_time = time.time()

    try:
        # Get or create session
        session_id, predictor, is_new = get_or_create_session(request.session_id)

        # Add clue to predictor (async for dual AI predictions)
        logger.info(f"Session {session_id}: Processing clue #{predictor.clue_count + 1}: '{request.clue_text}'")
        result = await predictor.add_clue_async(request.clue_text)

        # Convert Gemini predictions to API format
        gemini_preds = [
            Prediction(
                rank=i + 1,
                answer=pred.answer,
                confidence=pred.confidence,
                category=EntityCategory(pred.category),
                reasoning=pred.reasoning,
                semantic_match=SemanticMatch.MEDIUM
            )
            for i, pred in enumerate(result["gemini_predictions"])
        ]

        # Convert OpenAI predictions to API format
        openai_preds = [
            Prediction(
                rank=i + 1,
                answer=pred.answer,
                confidence=pred.confidence,
                category=EntityCategory(pred.category),
                reasoning=pred.reasoning,
                semantic_match=SemanticMatch.MEDIUM
            )
            for i, pred in enumerate(result["openai_predictions"])
        ]

        # Use the guess recommendation from the predictor
        guess_rec_data = result["guess_recommendation"]
        guess_rec = GuessRecommendation(
            should_guess=guess_rec_data.should_guess,
            confidence_threshold=guess_rec_data.confidence_threshold,
            rationale=guess_rec_data.rationale
        )

        # Calculate elapsed time
        elapsed = time.time() - start_time

        response = PredictionResponse(
            session_id=session_id,
            clue_number=result["clue_number"],
            gemini_predictions=gemini_preds,
            openai_predictions=openai_preds,
            agreements=result["agreements"],
            agreement_strength=result["agreement_strength"],
            recommended_pick=result["recommended_pick"],
            predictions=gemini_preds,  # Backwards compatibility
            guess_recommendation=guess_rec,
            elapsed_time=elapsed,
            clue_history=result["clue_history"],
            category_probabilities=result["category_probabilities"]
        )

        # Log summary
        logger.info(
            f"Session {session_id}: Clue #{result['clue_number']} - "
            f"Gemini: {gemini_preds[0].answer if gemini_preds else 'N/A'}, "
            f"OpenAI: {openai_preds[0].answer if openai_preds else 'N/A'}, "
            f"Agreements: {result['agreements']}"
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
        predictor = JackpotPredict(
            entity_registry=get_entity_registry()
        )
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
            version="2.0.0",  # Updated version for Gemini-first
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


def _record_error_pattern(
    predicted: str,
    correct: str,
    clues: List[str],
    error_type: str = "unknown"
) -> bool:
    """
    Record an error pattern for future learning.

    Saves to error_patterns.json to warn Gemini about past mistakes.
    """
    try:
        error_file = Path(__file__).parent.parent / "data" / "error_patterns.json"

        # Load existing patterns
        if error_file.exists():
            with open(error_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"patterns": [], "last_updated": ""}

        # Check if this error pattern already exists
        existing = None
        for pattern in data["patterns"]:
            if pattern["predicted"].lower() == predicted.lower() and pattern["correct"].lower() == correct.lower():
                existing = pattern
                break

        if existing:
            # Update existing pattern
            existing["occurrences"] = existing.get("occurrences", 1) + 1
            existing["timestamp"] = datetime.now().strftime("%Y-%m-%d")
        else:
            # Add new pattern
            data["patterns"].append({
                "predicted": predicted,
                "correct": correct,
                "clues_sample": clues[:2] if clues else [],
                "error_type": error_type,
                "occurrences": 1,
                "timestamp": datetime.now().strftime("%Y-%m-%d")
            })

        # Keep only the most recent 10 patterns
        data["patterns"] = sorted(
            data["patterns"],
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )[:10]

        data["last_updated"] = datetime.now().strftime("%Y-%m-%d")

        with open(error_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Recorded error pattern: {predicted} -> {correct}")
        return True

    except Exception as e:
        logger.error(f"Failed to record error pattern: {e}")
        return False


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit puzzle feedback",
    description="Submit the correct answer after a puzzle for learning improvement"
)
async def submit_feedback(request: FeedbackRequest) -> FeedbackResponse:
    """
    Submit puzzle feedback for continuous learning.

    Records the correct answer and clues to history.json for
    few-shot learning improvement in the Gemini context.

    If our prediction was wrong, also records the error pattern
    to error_patterns.json to help prevent similar mistakes.
    """
    try:
        from app.core.context_manager import get_context_manager

        manager = get_context_manager()

        # Convert EntityCategory enum to string for context manager
        category_str = request.category.value

        success = manager.add_game_result(
            category=category_str,
            clues=request.clues,
            answer=request.correct_answer,
            solved_at_clue=request.solved_at_clue or len(request.clues),
            key_insight=request.key_insight or ""
        )

        # Check if we need to record an error pattern
        # This requires checking if there was a prediction for this session
        if request.session_id and request.session_id in _sessions:
            predictor = _sessions[request.session_id]
            if hasattr(predictor, '_last_predictions') and predictor._last_predictions:
                top_prediction = predictor._last_predictions[0] if predictor._last_predictions else None
                if top_prediction and top_prediction.answer.lower() != request.correct_answer.lower():
                    # Our prediction was wrong - record the error pattern
                    # Determine error type based on similarity
                    try:
                        from Levenshtein import distance as levenshtein_distance
                        edit_distance = levenshtein_distance(
                            top_prediction.answer.lower(),
                            request.correct_answer.lower()
                        )
                        # If edit distance is small, it's likely phonetic confusion
                        if edit_distance <= 3:
                            error_type = "phonetic_confusion"
                        else:
                            error_type = "semantic_error"
                    except ImportError:
                        error_type = "unknown"

                    _record_error_pattern(
                        predicted=top_prediction.answer,
                        correct=request.correct_answer,
                        clues=request.clues,
                        error_type=error_type
                    )

        if success:
            logger.info(
                f"Feedback recorded: {request.correct_answer} ({category_str}) "
                f"with {len(request.clues)} clues"
            )
            return FeedbackResponse(
                success=True,
                message="Feedback recorded successfully. Thank you for helping improve predictions!"
            )
        else:
            return FeedbackResponse(
                success=False,
                message="Failed to save feedback to history"
            )

    except Exception as e:
        logger.error(f"Error submitting feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )


# Exception handlers are now in server.py

"""
FastAPI Routes - REST API endpoints for JackpotPredict.

MIXTURE OF AGENTS ARCHITECTURE (v3.0)
=====================================
5 specialized agents running in parallel with weighted voting.
Agents: Lateral, Wordsmith, PopCulture, Literal, WildCard

Endpoints:
- POST /api/predict - Submit clue and get predictions from all 5 agents
- POST /api/reset - Reset session for new puzzle
- POST /api/validate - Validate answer spelling
- POST /api/feedback - Submit puzzle feedback for learning
- GET /api/health - Health check and metrics
- GET /api/thinker-status/{session_id}/{clue_number} - Poll for thinker status
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
    FeedbackResponse,
    AgentPrediction as APIAgentPrediction,
    VotingResult as APIVotingResult,
    VoteBreakdown,
    OracleSynthesis as APIOracleSynthesis,
    OracleGuess as APIOracleGuess,
    ThinkerInsight as APIThinkerInsight,
    ThinkerStatus as APIThinkerStatus
)
from app.core.spelling_validator import SpellingValidator
from app.core.entity_registry import EntityRegistry
from app.agents.orchestrator import get_orchestrator, warmup_agents
from app.agents.oracle_agent import get_oracle
from app.core.reasoning_accumulator import (
    get_accumulator,
    ClueAnalysis,
    OracleSynthesis,
    OracleGuess,
    ThinkerContext,
    ThinkerInsight
)

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/api", tags=["predictions"])

from dataclasses import dataclass, field


@dataclass
class SessionState:
    """State for a prediction session with reasoning accumulation."""
    clues: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_prediction: Optional[str] = None

    # Reasoning accumulation
    clue_analyses: List[ClueAnalysis] = field(default_factory=list)
    hypothesis_tracker: Dict[str, List[float]] = field(default_factory=dict)

    # Thinker context (deep analysis from prior clues)
    thinker_context: ThinkerContext = field(default_factory=ThinkerContext)

# Global state
_sessions: Dict[str, SessionState] = {}
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
    global _sessions

    now = datetime.now()
    expired_ids = []

    for session_id, state in _sessions.items():
        if now - state.created_at > timedelta(minutes=SESSION_EXPIRY_MINUTES):
            expired_ids.append(session_id)

    for session_id in expired_ids:
        _sessions.pop(session_id, None)

    if expired_ids:
        logger.info(f"Cleaned up {len(expired_ids)} expired sessions")


def get_or_create_session(session_id: Optional[str] = None) -> tuple[str, SessionState, bool]:
    """
    Get existing session or create new one.

    Args:
        session_id: Optional existing session ID

    Returns:
        Tuple of (session_id, session_state, is_new)
    """
    global _sessions

    # Cleanup expired sessions
    cleanup_expired_sessions()

    # Create new session if no ID provided or session doesn't exist
    if session_id is None or session_id not in _sessions:
        new_session_id = str(uuid.uuid4())
        state = SessionState(clues=[], created_at=datetime.now())
        _sessions[new_session_id] = state
        logger.info(f"Created new session: {new_session_id}")
        return new_session_id, state, True

    # Update timestamp for existing session
    state = _sessions[session_id]
    state.created_at = datetime.now()  # Refresh TTL
    return session_id, state, False


@router.post(
    "/predict",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit clue and get predictions from 5 specialized agents",
    description="Analyze a clue with 5 agents in parallel: Lateral, Wordsmith, PopCulture, Literal, WildCard"
)
async def predict(request: ClueRequest) -> PredictionResponse:
    """
    Submit a clue and get predictions from 5 specialized agents.

    This is the main endpoint for the prediction engine. Submit clues sequentially
    (1-5) and the system will maintain session state, providing predictions
    based on all clues seen so far.

    5 agents predict in parallel:
    - Lateral: Multi-hop associative reasoning
    - Wordsmith: Puns and wordplay detection
    - PopCulture: Netflix/trending bias
    - Literal: Trap detection, face-value interpretation
    - WildCard: Creative leaps and paradoxes

    Weighted voting aggregates results based on clue number.
    """
    start_time = time.time()

    try:
        # Get or create session
        session_id, session_state, is_new = get_or_create_session(request.session_id)

        # Add clue to session history
        session_state.clues.append(request.clue_text)
        clue_number = len(session_state.clues)

        logger.info(f"Session {session_id}: Processing clue #{clue_number}: '{request.clue_text}'")

        # Generate context injection from prior clue analyses + thinker context (REASONING ACCUMULATION)
        accumulator = get_accumulator()
        prior_context = None
        if session_state.clue_analyses or session_state.thinker_context.insights:
            prior_context = accumulator.generate_context_injection(
                analyses=session_state.clue_analyses,
                current_clue_number=clue_number,
                full_predictions=True,
                thinker_context=session_state.thinker_context
            )
            thinker_insight_count = len(session_state.thinker_context.insights)
            logger.info(f"Session {session_id}: Injecting context from {len(session_state.clue_analyses)} prior clues, {thinker_insight_count} thinker insights")

        # Run 5 agents in parallel via orchestrator (with prior context for reasoning accumulation)
        orchestrator = get_orchestrator()
        result = await orchestrator.predict(
            clues=session_state.clues,
            clue_number=clue_number,
            category_hint=None,  # Could add category detection later
            prior_context=prior_context,
            prior_analyses=session_state.clue_analyses,  # For Oracle context
            theme=request.theme,  # Optional theme/sponsor context
            session_id=session_id,  # For thinker background task tracking
            thinker_context=session_state.thinker_context  # Prior thinker insights
        )

        # Convert agent predictions to API format
        agent_preds: Dict[str, Optional[APIAgentPrediction]] = {}
        for agent_name, pred in result.predictions.items():
            if pred:
                agent_preds[agent_name] = APIAgentPrediction(
                    answer=pred.answer,
                    confidence=pred.confidence,
                    reasoning=pred.reasoning
                )
            else:
                agent_preds[agent_name] = None

        # Convert voting result to API format
        vote_breakdown = [
            VoteBreakdown(
                answer=vr.answer,
                total_votes=vr.total_votes,
                agents=vr.agents
            )
            for vr in result.voting.vote_breakdown
        ]

        voting_result = APIVotingResult(
            recommended_pick=result.voting.recommended_pick,
            key_insight=result.voting.key_insight,
            agreement_strength=result.voting.agreement_strength,
            vote_breakdown=vote_breakdown
        )

        # Build guess recommendation
        # Calculate threshold based on clue number
        thresholds = {1: 0.90, 2: 0.85, 3: 0.75, 4: 0.65, 5: 0.50}
        threshold = thresholds.get(clue_number, 0.75)

        guess_rec = GuessRecommendation(
            should_guess=result.should_guess,
            confidence_threshold=threshold,
            rationale=result.guess_rationale
        )

        # Store last prediction for error learning
        session_state.last_prediction = result.voting.recommended_pick

        # Calculate elapsed time
        elapsed = time.time() - start_time

        # Build agreements list (agents that agree on recommended pick)
        agreements = []
        if result.voting.vote_breakdown:
            top_vote = result.voting.vote_breakdown[0]
            agreements = top_vote.agents

        # Convert Oracle synthesis to API format
        oracle_synthesis = None
        if result.oracle_synthesis:
            oracle_synthesis = APIOracleSynthesis(
                top_3=[
                    APIOracleGuess(
                        answer=g.answer,
                        confidence=g.confidence,
                        explanation=g.explanation
                    )
                    for g in result.oracle_synthesis.top_3
                ],
                key_theme=result.oracle_synthesis.key_theme,
                blind_spot=result.oracle_synthesis.blind_spot,
                latency_ms=result.oracle_synthesis.latency_ms
            )

        response = PredictionResponse(
            session_id=session_id,
            clue_number=clue_number,
            agents=agent_preds,
            voting=voting_result,
            oracle=oracle_synthesis,
            thinker_task_id=result.thinker_task_id,
            recommended_pick=result.voting.recommended_pick,
            key_insight=result.voting.key_insight,
            agreement_strength=result.voting.agreement_strength,
            agents_responded=result.agents_responded,
            agreements=agreements,
            guess_recommendation=guess_rec,
            elapsed_time=elapsed,
            clue_history=session_state.clues.copy(),
            category_probabilities={"thing": 0.60, "place": 0.25, "person": 0.15}  # Priors
        )

        # Log summary
        agent_answers = [f"{k}:{v.answer}" for k, v in agent_preds.items() if v]
        logger.info(
            f"Session {session_id}: Clue #{clue_number} - "
            f"Recommended: {result.voting.recommended_pick} ({result.voting.agreement_strength}) | "
            f"Agents: {', '.join(agent_answers)}"
        )

        # REASONING ACCUMULATION: Store analysis for next clue's context
        clue_analysis = accumulator.create_clue_analysis(
            clue_number=clue_number,
            clue_text=request.clue_text,
            predictions=result.predictions,
            voting_result=result.voting,
            prior_analyses=session_state.clue_analyses
        )
        # Attach Oracle synthesis if available
        if result.oracle_synthesis:
            clue_analysis.oracle_synthesis = result.oracle_synthesis
        session_state.clue_analyses.append(clue_analysis)

        # Update hypothesis tracker for confidence evolution
        accumulator.update_hypothesis_tracker(
            tracker=session_state.hypothesis_tracker,
            analysis=clue_analysis
        )

        logger.info(
            f"Session {session_id}: Stored analysis for clue #{clue_number} | "
            f"Tracking {len(session_state.hypothesis_tracker)} hypotheses"
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
    global _sessions

    try:
        if request.session_id and request.session_id in _sessions:
            # Remove existing session
            _sessions.pop(request.session_id, None)
            logger.info(f"Reset session: {request.session_id}")

        # Create new session
        new_session_id = str(uuid.uuid4())
        _sessions[new_session_id] = SessionState(clues=[], created_at=datetime.now())

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
            version="3.0.0",  # MoA architecture with 5 specialized agents
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


@router.get(
    "/thinker-status/{session_id}/{clue_number}",
    response_model=APIThinkerStatus,
    status_code=status.HTTP_200_OK,
    summary="Get thinker analysis status",
    description="Poll for thinker deep analysis completion. Called every 1s by frontend."
)
async def get_thinker_status(session_id: str, clue_number: int) -> APIThinkerStatus:
    """
    Get status of background thinker analysis.

    Frontend polls this every 1s after receiving prediction response.
    Returns pending=True while thinker is still processing.
    Returns completed=True with insight when thinker finishes.

    Also updates session's thinker_context when insight is retrieved.
    """
    try:
        orchestrator = get_orchestrator()
        status_result = orchestrator.get_thinker_status(session_id, clue_number)

        insight_data = None
        if status_result.get("insight"):
            insight = status_result["insight"]
            insight_data = APIThinkerInsight(
                clue_number=insight.clue_number,
                top_guess=insight.top_guess,
                confidence=insight.confidence,
                hypothesis_reasoning=insight.hypothesis_reasoning,
                key_patterns=insight.key_patterns,
                refined_guesses=[
                    APIOracleGuess(
                        answer=g.answer,
                        confidence=g.confidence,
                        explanation=g.explanation
                    )
                    for g in insight.refined_guesses
                ],
                narrative_arc=insight.narrative_arc,
                wordplay_analysis=insight.wordplay_analysis,
                latency_ms=insight.latency_ms
            )

            if session_id in _sessions:
                session = _sessions[session_id]
                existing = session.thinker_context.get_for_clue(clue_number)
                if not existing:
                    session.thinker_context.add_insight(insight)
                    logger.info(f"Session {session_id}: Stored thinker insight for clue #{clue_number}")

        return APIThinkerStatus(
            pending=status_result.get("pending", False),
            completed=status_result.get("completed", False),
            insight=insight_data
        )

    except Exception as e:
        logger.error(f"Error getting thinker status: {e}", exc_info=True)
        return APIThinkerStatus(
            pending=False,
            completed=False,
            insight=None
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
            session_state = _sessions[request.session_id]
            if session_state.last_prediction:
                if session_state.last_prediction.lower() != request.correct_answer.lower():
                    # Our prediction was wrong - record the error pattern
                    # Determine error type based on similarity
                    try:
                        from Levenshtein import distance as levenshtein_distance
                        edit_distance = levenshtein_distance(
                            session_state.last_prediction.lower(),
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
                        predicted=session_state.last_prediction,
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


@router.get(
    "/test-agents",
    status_code=status.HTTP_200_OK,
    summary="Test all agents individually",
    description="Diagnostic endpoint to test each agent's API connectivity and response parsing"
)
async def test_agents():
    """
    Test each agent individually with a sample clue.

    Returns detailed status for each agent including:
    - API connectivity
    - Response parsing success
    - Raw response content (on failure)
    - Error details
    """
    import asyncio
    import httpx

    test_clue = "Surrounded by success and failure"
    results = {
        "test_clue": test_clue,
        "agents": {},
        "oracle": {},
        "summary": {}
    }

    # Test all 5 agents
    orchestrator = get_orchestrator()
    orchestrator._init_agents()

    async def test_single_agent(name: str, agent):
        try:
            # Check if API key is configured
            if not agent.api_key:
                return {
                    "status": "error",
                    "error": "No API key configured",
                    "api_key_present": False
                }

            start_time = time.time()

            # Build request
            messages = [
                {"role": "system", "content": agent.get_system_prompt()},
                {"role": "user", "content": agent.format_clues_message([test_clue])}
            ]

            payload = {
                "model": agent.model,
                "messages": messages,
                "temperature": agent.TEMPERATURE,
                "max_tokens": 150,
            }

            # Make API call
            response = await agent.client.post(
                f"{agent.base_url}/chat/completions",
                json=payload
            )

            latency_ms = (time.time() - start_time) * 1000

            if response.status_code != 200:
                return {
                    "status": "api_error",
                    "http_status": response.status_code,
                    "error": response.text[:500],
                    "latency_ms": latency_ms,
                    "api_key_present": True,
                    "model": agent.model,
                    "base_url": agent.base_url
                }

            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

            # Try to parse the response
            prediction = agent.parse_response(content)

            if prediction:
                return {
                    "status": "success",
                    "prediction": {
                        "answer": prediction.answer,
                        "confidence": prediction.confidence,
                        "reasoning": prediction.reasoning
                    },
                    "latency_ms": latency_ms,
                    "model": agent.model,
                    "base_url": agent.base_url
                }
            else:
                return {
                    "status": "parse_error",
                    "raw_response": content[:500],
                    "latency_ms": latency_ms,
                    "model": agent.model,
                    "base_url": agent.base_url,
                    "error": "Response did not match expected format (ANSWER/CONFIDENCE/REASONING)"
                }

        except httpx.TimeoutException:
            return {
                "status": "timeout",
                "error": f"Request timed out after {agent.timeout}s",
                "model": agent.model,
                "base_url": agent.base_url
            }
        except Exception as e:
            return {
                "status": "exception",
                "error": str(e),
                "error_type": type(e).__name__,
                "model": agent.model if hasattr(agent, 'model') else "unknown",
                "base_url": agent.base_url if hasattr(agent, 'base_url') else "unknown"
            }

    # Test all agents in parallel
    agent_tasks = [
        (name, test_single_agent(name, agent))
        for name, agent in orchestrator._agents.items()
    ]

    for name, task in agent_tasks:
        results["agents"][name] = await task

    # Test Oracle
    oracle = get_oracle()
    try:
        if not oracle.enabled:
            results["oracle"] = {
                "status": "disabled",
                "error": "No Anthropic API key configured"
            }
        else:
            start_time = time.time()
            synthesis = await asyncio.wait_for(
                oracle.synthesize_early(
                    clues=[test_clue],
                    clue_number=1,
                    prior_analyses=None
                ),
                timeout=10
            )
            latency_ms = (time.time() - start_time) * 1000

            if synthesis:
                results["oracle"] = {
                    "status": "success",
                    "top_pick": synthesis.top_3[0].answer if synthesis.top_3 else "None",
                    "confidence": synthesis.top_3[0].confidence if synthesis.top_3 else 0,
                    "key_theme": synthesis.key_theme,
                    "latency_ms": latency_ms,
                    "model": oracle.model
                }
            else:
                results["oracle"] = {
                    "status": "parse_error",
                    "error": "Failed to parse Oracle response",
                    "latency_ms": latency_ms,
                    "model": oracle.model
                }
    except asyncio.TimeoutError:
        results["oracle"] = {
            "status": "timeout",
            "error": "Oracle timed out after 10s"
        }
    except Exception as e:
        results["oracle"] = {
            "status": "exception",
            "error": str(e),
            "error_type": type(e).__name__
        }

    # Generate summary
    successful = sum(1 for r in results["agents"].values() if r.get("status") == "success")
    results["summary"] = {
        "agents_successful": successful,
        "agents_total": 5,
        "oracle_status": results["oracle"].get("status", "unknown"),
        "all_working": successful == 5 and results["oracle"].get("status") == "success"
    }

    return results


# Exception handlers are now in server.py

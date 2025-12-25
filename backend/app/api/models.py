"""
API Request/Response Models - Pydantic schemas for FastAPI endpoints.

Defines:
- Request models for submitting clues
- Response models for predictions (5-agent MoA architecture)
- Session management models
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


# Agent names for MoA architecture
AGENT_NAMES = ["lateral", "wordsmith", "popculture", "literal", "wildcard"]


class EntityCategory(str, Enum):
    """Entity category enum matching core models."""
    PERSON = "person"
    PLACE = "place"
    THING = "thing"


class ClueRequest(BaseModel):
    """Request model for submitting a new clue."""

    clue_text: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="The clue text to analyze",
        examples=["Savors many flavors"]
    )

    session_id: Optional[str] = Field(
        None,
        description="Optional session ID for continuing an existing puzzle"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "clue_text": "Savors many flavors",
                "session_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
    )


class SemanticMatch(str, Enum):
    """Semantic match quality for self-validation."""
    STRONG = "strong"
    MEDIUM = "medium"
    WEAK = "weak"


class Prediction(BaseModel):
    """Individual prediction result."""

    rank: int = Field(
        ...,
        ge=1,
        le=3,
        description="Rank position (1-3)"
    )

    answer: str = Field(
        ...,
        description="Predicted answer (canonical spelling)"
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0-1.0)"
    )

    category: EntityCategory = Field(
        ...,
        description="Entity category (person/place/thing)"
    )

    reasoning: str = Field(
        ...,
        description="Explanation of why this answer was predicted"
    )

    semantic_match: SemanticMatch = Field(
        default=SemanticMatch.MEDIUM,
        description="Self-validation: how well the answer's meaning matches the clues (strong/medium/weak)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "rank": 1,
                "answer": "Monopoly",
                "confidence": 0.87,
                "category": "thing",
                "reasoning": "Strong polysemy match with 'flavors' (editions) and keyword alignment",
                "semantic_match": "strong"
            }
        }
    )


class GuessRecommendation(BaseModel):
    """Recommendation on whether to guess now."""

    should_guess: bool = Field(
        ...,
        description="Whether to make a guess with current top answer"
    )

    confidence_threshold: float = Field(
        ...,
        description="Minimum confidence threshold for this clue number"
    )

    rationale: str = Field(
        ...,
        description="Explanation of recommendation"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "should_guess": True,
                "confidence_threshold": 0.75,
                "rationale": "Clue 3: Confidence 87% exceeds 75% threshold - recommended to guess"
            }
        }
    )


class AgentPrediction(BaseModel):
    """Individual agent prediction in MoA architecture."""

    answer: str = Field(
        ...,
        description="Predicted answer from this agent"
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0-1.0)"
    )

    reasoning: str = Field(
        ...,
        description="Brief 2-4 word explanation"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "answer": "Bowling",
                "confidence": 0.85,
                "reasoning": "Strike=win"
            }
        }
    )


class VoteBreakdown(BaseModel):
    """Vote breakdown for an answer in weighted voting."""

    answer: str = Field(
        ...,
        description="The answer that received votes"
    )

    total_votes: float = Field(
        ...,
        description="Weighted vote total"
    )

    agents: List[str] = Field(
        ...,
        description="List of agents that predicted this answer"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "answer": "Bowling",
                "total_votes": 2.65,
                "agents": ["lateral", "wordsmith"]
            }
        }
    )


class VotingResult(BaseModel):
    """Result of weighted voting across agents."""

    recommended_pick: str = Field(
        ...,
        description="The winning answer from voting"
    )

    key_insight: str = Field(
        ...,
        description="Key reasoning from top-confidence agent"
    )

    agreement_strength: str = Field(
        ...,
        description="Agreement strength: 'strong', 'moderate', 'weak', 'none'"
    )

    vote_breakdown: List[VoteBreakdown] = Field(
        default_factory=list,
        description="Vote distribution across answers"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "recommended_pick": "Bowling",
                "key_insight": "Strike=Success, Gutter=Failure",
                "agreement_strength": "strong",
                "vote_breakdown": [
                    {"answer": "Bowling", "total_votes": 2.65, "agents": ["lateral", "wordsmith"]},
                    {"answer": "Squid Game", "total_votes": 0.60, "agents": ["popculture"]}
                ]
            }
        }
    )


class OracleGuess(BaseModel):
    """A single guess from the Oracle meta-synthesizer."""

    answer: str = Field(
        ...,
        description="Predicted answer"
    )

    confidence: int = Field(
        ...,
        ge=0,
        le=100,
        description="Confidence percentage (0-100)"
    )

    explanation: str = Field(
        ...,
        description="Brief explanation (1-2 sentences)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "answer": "Monopoly",
                "confidence": 92,
                "explanation": "Business terms ('hostile takeover') + board game signals + 'dicey' = dice"
            }
        }
    )


class OracleSynthesis(BaseModel):
    """Oracle meta-synthesizer output with top 3 ranked guesses."""

    top_3: List[OracleGuess] = Field(
        ...,
        min_length=1,
        max_length=3,
        description="Top 3 guesses ranked by confidence"
    )

    key_theme: str = Field(
        ...,
        description="Dominant theme identified across clues (5-10 words)"
    )

    blind_spot: str = Field(
        ...,
        description="What the agents might be missing (5-15 words)"
    )

    latency_ms: float = Field(
        default=0.0,
        description="Oracle processing time in milliseconds"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "top_3": [
                    {"answer": "Monopoly", "confidence": 92, "explanation": "Business terms + board game + dice"},
                    {"answer": "Risk", "confidence": 45, "explanation": "Military conquest theme, weaker fit"},
                    {"answer": "Life", "confidence": 30, "explanation": "'Flavors of life' metaphor"}
                ],
                "key_theme": "Board games with business/strategy elements",
                "blind_spot": "Consider if 'dicey' is wordplay (dice) or means 'risky'",
                "latency_ms": 1250.0
            }
        }
    )


class PredictionResponse(BaseModel):
    """Response model for prediction results with 5-agent MoA architecture."""

    session_id: str = Field(
        ...,
        description="Unique session identifier"
    )

    clue_number: int = Field(
        ...,
        ge=1,
        le=5,
        description="Current clue number (1-5)"
    )

    # 5-Agent predictions (MoA architecture)
    agents: Dict[str, Optional[AgentPrediction]] = Field(
        default_factory=dict,
        description="Predictions from 5 specialized agents: lateral, wordsmith, popculture, literal, wildcard"
    )

    # Voting results
    voting: Optional[VotingResult] = Field(
        None,
        description="Weighted voting result across agents"
    )

    # Oracle meta-synthesis (Claude 3.5 Sonnet)
    oracle: Optional[OracleSynthesis] = Field(
        None,
        description="Oracle meta-synthesizer output with top 3 guesses"
    )

    # Convenience fields
    recommended_pick: str = Field(
        default="",
        description="The recommended answer from voting"
    )

    key_insight: str = Field(
        default="",
        description="Key reasoning explaining the recommendation"
    )

    agreement_strength: str = Field(
        default="none",
        description="Agreement strength: 'strong', 'moderate', 'weak', 'none'"
    )

    agents_responded: int = Field(
        default=0,
        description="Number of agents that responded (0-5)"
    )

    # Legacy fields for backwards compatibility
    gemini_predictions: List[Prediction] = Field(
        default_factory=list,
        description="Legacy: Top 3 predictions from Gemini (deprecated)"
    )

    openai_predictions: List[Prediction] = Field(
        default_factory=list,
        description="Legacy: Top 3 predictions from OpenAI (deprecated)"
    )

    predictions: List[Prediction] = Field(
        default_factory=list,
        description="Legacy: Top 3 predictions (deprecated)"
    )

    agreements: List[str] = Field(
        default_factory=list,
        description="Legacy: Answers that appear in multiple agents' predictions"
    )

    guess_recommendation: GuessRecommendation = Field(
        ...,
        description="Recommendation on whether to guess now"
    )

    elapsed_time: float = Field(
        ...,
        description="Processing time in seconds"
    )

    clue_history: List[str] = Field(
        ...,
        description="All clues submitted so far in this session"
    )

    category_probabilities: Dict[str, float] = Field(
        default_factory=dict,
        description="Current probability distribution across categories"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "clue_number": 2,
                "agents": {
                    "lateral": {"answer": "Bowling", "confidence": 0.85, "reasoning": "Strike=win"},
                    "wordsmith": {"answer": "Bowling", "confidence": 0.80, "reasoning": "Pun: strike"},
                    "popculture": {"answer": "Squid Game", "confidence": 0.60, "reasoning": "Netflix"},
                    "literal": {"answer": "Life", "confidence": 0.40, "reasoning": "(trap)"},
                    "wildcard": {"answer": "Roulette", "confidence": 0.55, "reasoning": "wheel"}
                },
                "voting": {
                    "recommended_pick": "Bowling",
                    "key_insight": "Strike=Success, Gutter=Failure",
                    "agreement_strength": "strong",
                    "vote_breakdown": [
                        {"answer": "Bowling", "total_votes": 2.65, "agents": ["lateral", "wordsmith"]}
                    ]
                },
                "recommended_pick": "Bowling",
                "key_insight": "Strike=Success, Gutter=Failure",
                "agreement_strength": "strong",
                "agents_responded": 5,
                "guess_recommendation": {
                    "should_guess": True,
                    "confidence_threshold": 0.65,
                    "rationale": "2 agents agree on Bowling with high confidence"
                },
                "elapsed_time": 2.1,
                "clue_history": ["Surrounded by success and failure", "Strike and gutter"],
                "category_probabilities": {"thing": 1.0, "place": 0.0, "person": 0.0}
            }
        }
    )


class ResetRequest(BaseModel):
    """Request model for resetting a session."""

    session_id: Optional[str] = Field(
        None,
        description="Optional session ID to reset (if None, creates new session)"
    )


class ResetResponse(BaseModel):
    """Response model for session reset."""

    session_id: str = Field(
        ...,
        description="New session identifier"
    )

    message: str = Field(
        ...,
        description="Confirmation message"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "Session reset successfully. Ready for new puzzle."
            }
        }
    )


class ValidationRequest(BaseModel):
    """Request model for spelling validation."""

    answer: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Answer to validate"
    )


class ValidationResponse(BaseModel):
    """Response model for spelling validation."""

    is_valid: bool = Field(
        ...,
        description="Whether the answer is valid"
    )

    canonical_spelling: Optional[str] = Field(
        None,
        description="Correct canonical spelling if valid"
    )

    error_type: Optional[str] = Field(
        None,
        description="Type of error (abbreviation, partial_name, typo, not_found)"
    )

    suggestion: Optional[str] = Field(
        None,
        description="Suggested correction"
    )

    fuzzy_matches: List[str] = Field(
        default_factory=list,
        description="Alternative fuzzy matches"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "is_valid": False,
                "canonical_spelling": None,
                "error_type": "partial_name",
                "suggestion": "Paris Hilton",
                "fuzzy_matches": ["Paris Hilton", "Paris, France"]
            }
        }
    )


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(
        ...,
        description="Service status (healthy/unhealthy)"
    )

    version: str = Field(
        ...,
        description="API version"
    )

    entity_count: int = Field(
        ...,
        description="Number of entities in registry"
    )

    active_sessions: int = Field(
        ...,
        description="Number of active sessions"
    )

    uptime_seconds: float = Field(
        ...,
        description="Server uptime in seconds"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "entity_count": 5000,
                "active_sessions": 12,
                "uptime_seconds": 3600.5
            }
        }
    )


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: str = Field(
        ...,
        description="Error type"
    )

    message: str = Field(
        ...,
        description="Human-readable error message"
    )

    detail: Optional[str] = Field(
        None,
        description="Additional error details"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "ValidationError",
                "message": "Invalid clue text",
                "detail": "Clue text cannot be empty"
            }
        }
    )


class FeedbackRequest(BaseModel):
    """Request model for submitting puzzle feedback."""

    session_id: str = Field(
        ...,
        description="Session ID for the completed puzzle"
    )

    correct_answer: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="The correct answer for this puzzle"
    )

    category: EntityCategory = Field(
        ...,
        description="Category of the answer (person/place/thing)"
    )

    clues: List[str] = Field(
        ...,
        description="List of clues submitted during this puzzle"
    )

    solved_at_clue: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="Clue number when user knew the answer (optional)"
    )

    key_insight: Optional[str] = Field(
        None,
        max_length=500,
        description="Key insight about how to interpret the clues (optional)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "correct_answer": "Monopoly",
                "category": "thing",
                "clues": ["Savors many flavors", "Round and round", "A hostile takeover"],
                "solved_at_clue": 3,
                "key_insight": "'hostile takeover' referred to the business theme"
            }
        }
    )


class FeedbackResponse(BaseModel):
    """Response model for feedback submission."""

    success: bool = Field(
        ...,
        description="Whether feedback was successfully recorded"
    )

    message: str = Field(
        ...,
        description="Confirmation or error message"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Feedback recorded successfully"
            }
        }
    )

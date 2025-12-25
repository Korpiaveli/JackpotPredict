"""
FastAPI Server - Main application entry point.

MIXTURE OF AGENTS ARCHITECTURE (v3.0)
=====================================
5 specialized agents running in parallel with weighted voting.
Agents: Lateral, Wordsmith, PopCulture, Literal, WildCard

Run with:
    uvicorn app.server:app --reload --port 8000
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.entity_registry import EntityRegistry
from app.agents.orchestrator import warmup_agents, get_orchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown events.

    On startup:
    - Initialize entity registry
    - Verify agent APIs availability

    On shutdown:
    - Close database connections
    - Close agent HTTP clients
    """
    # Startup
    start_time = time.time()
    logger.info("[STARTUP] JackpotPredict API v3.0 (MoA) starting up...")

    try:
        # Initialize entity registry (singleton pattern handled in routes.py)
        from app.api.routes import get_entity_registry
        registry = get_entity_registry()

        entity_count = registry.get_entity_count()
        logger.info(f"[OK] Entity registry loaded: {entity_count} entities")

        # Verify agent APIs are available
        agents_ready = await warmup_agents()
        if agents_ready:
            logger.info("[OK] Agent APIs ready (3+ agents configured)")
        else:
            logger.warning("[WARN] Less than 3 agents available - predictions may be limited")

        startup_time = time.time() - start_time
        logger.info(f"[OK] Startup complete in {startup_time:.2f}s")
        logger.info("[READY] API server ready at http://localhost:8000")
        logger.info("[DOCS] API docs available at http://localhost:8000/docs")

    except Exception as e:
        logger.error(f"[ERROR] Startup failed: {e}", exc_info=True)
        raise

    yield

    # Shutdown
    logger.info("[SHUTDOWN] JackpotPredict API shutting down...")
    try:
        # Close entity registry connection
        from app.api.routes import _entity_registry
        if _entity_registry:
            _entity_registry.close()
            logger.info("[OK] Entity registry closed")

        # Close agent orchestrator
        orchestrator = get_orchestrator()
        await orchestrator.close()
        logger.info("[OK] Agent orchestrator closed")

        logger.info("[OK] Shutdown complete")

    except Exception as e:
        logger.error(f"[ERROR] Shutdown error: {e}", exc_info=True)


# Create FastAPI application
app = FastAPI(
    title="JackpotPredict API",
    description="""
    AI-powered real-time inference engine for Netflix's Best Guess Live game show.

    **MIXTURE OF AGENTS ARCHITECTURE (v3.0)**

    Submit clues sequentially (1-5) and receive predictions from 5 specialized agents.

    ## 5 Specialized Agents
    - **Lateral**: Multi-hop associative reasoning (GPT-4o-mini)
    - **Wordsmith**: Puns, wordplay, homophones (GPT-4o-mini)
    - **PopCulture**: Netflix/trending bias (Gemini Flash)
    - **Literal**: Trap detection, face-value (Llama 3.3 70B via Groq)
    - **WildCard**: Paradox, creative leaps (GPT-4o-mini, high temp)

    ## Key Features
    - 5 agents predict in parallel (~5s total)
    - Weighted voting based on clue number
    - Early clues favor creative agents
    - Late clues favor literal interpretation
    - Spelling validation (100% accuracy requirement)
    - Session management with 5-minute expiry

    ## Workflow
    1. POST /api/predict - Submit Clue 1 (returns session_id + 5 predictions)
    2. POST /api/predict - Submit Clue 2 (voting recommends best answer)
    3. Continue until confidence threshold met
    4. POST /api/validate - Validate spelling before guessing
    5. POST /api/reset - Start new puzzle

    ## Category Priors
    - Thing: 60% (brands, games, objects, shows)
    - Place: 25% (landmarks, cities, buildings)
    - Person: 15% (celebrities, characters)
    """,
    version="3.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    """Handle unexpected exceptions gracefully."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "detail": str(exc) if app.debug else None
        }
    )


# Include API routes
app.include_router(router)


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint - API information."""
    return {
        "name": "JackpotPredict API",
        "version": "3.0.0",
        "architecture": "Mixture of Agents (MoA)",
        "agents": ["lateral", "wordsmith", "popculture", "literal", "wildcard"],
        "description": "AI-powered trivia answer prediction engine with 5 specialized agents",
        "docs": "/docs",
        "health": "/api/health",
        "endpoints": {
            "predict": "POST /api/predict",
            "reset": "POST /api/reset",
            "validate": "POST /api/validate",
            "feedback": "POST /api/feedback",
            "health": "GET /api/health"
        }
    }


if __name__ == "__main__":
    import uvicorn

    # Run with uvicorn
    uvicorn.run(
        "app.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

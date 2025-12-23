"""
FastAPI Server - Main application entry point.

GEMINI-FIRST ARCHITECTURE (v2.0)
================================
Simplified server using Gemini API as the primary LLM.
Removed Ollama warmup as cloud APIs don't require it.

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
from app.core.gemini_predictor import warmup_gemini

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
    - Verify Gemini API availability

    On shutdown:
    - Close database connections
    """
    # Startup
    start_time = time.time()
    logger.info("[STARTUP] JackpotPredict API starting up...")

    try:
        # Initialize entity registry (singleton pattern handled in routes.py)
        from app.api.routes import get_entity_registry
        registry = get_entity_registry()

        entity_count = registry.get_entity_count()
        logger.info(f"[OK] Entity registry loaded: {entity_count} entities")

        # Verify Gemini API is available
        # Note: Cloud APIs don't need warmup, just availability check
        gemini_ready = await warmup_gemini()
        if gemini_ready:
            logger.info("[OK] Gemini API ready")
        else:
            logger.warning("[WARN] Gemini API not available - predictions will fail")

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

        logger.info("[OK] Shutdown complete")

    except Exception as e:
        logger.error(f"[ERROR] Shutdown error: {e}", exc_info=True)


# Create FastAPI application
app = FastAPI(
    title="JackpotPredict API",
    description="""
    AI-powered real-time inference engine for Netflix's Best Guess Live game show.

    **GEMINI-FIRST ARCHITECTURE (v2.0)**

    Submit clues sequentially (1-5) and receive top 3 predictions with confidence scores.

    ## Key Features
    - Gemini 2.0 Flash for intelligent trivia prediction
    - Few-shot learning from 45+ historical games
    - Wordplay and lateral thinking detection
    - Spelling validation (100% accuracy requirement)
    - Session management with 5-minute expiry
    - Guess recommendations based on confidence thresholds

    ## Workflow
    1. POST /api/predict - Submit Clue 1 (returns session_id)
    2. POST /api/predict - Submit Clue 2 (use session_id)
    3. Continue until top prediction confidence exceeds threshold
    4. POST /api/validate - Validate spelling before guessing
    5. POST /api/reset - Start new puzzle

    ## Category Priors
    - Thing: 60% (brands, games, objects, shows)
    - Place: 25% (landmarks, cities, buildings)
    - Person: 15% (celebrities, characters)
    """,
    version="2.0.0",
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
        "version": "2.0.0",
        "architecture": "Gemini-First",
        "description": "AI-powered trivia answer prediction engine",
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

"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
from supabase import AsyncClient

from app.core.clients import get_openai_client, get_supabase_client
from app.core.config import get_settings
from app.detection.embeddings import EmbeddingsDetector
from app.models.schemas import HealthResponse

logger = logging.getLogger(__name__)
settings = get_settings()


# Application state for shared clients
class AppState:
    """Shared application state for clients."""

    openai_client: AsyncOpenAI | None = None
    supabase_client: AsyncClient | None = None
    embeddings_detector: EmbeddingsDetector | None = None


app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan - initialize and cleanup clients.

    Creates shared OpenAI and Supabase clients on startup and
    initializes the EmbeddingsDetector for Layer 2 detection.
    """
    # Startup: Initialize clients
    try:
        app_state.openai_client = await get_openai_client()
        app_state.supabase_client = await get_supabase_client()
        app_state.embeddings_detector = EmbeddingsDetector(
            openai_client=app_state.openai_client,
            supabase_client=app_state.supabase_client,
        )
        logger.info("Initialized OpenAI and Supabase clients")
    except ValueError as e:
        # Log warning but don't fail startup - allows health checks without full config
        logger.warning(f"Client initialization skipped: {e}")

    yield

    # Shutdown: Cleanup (Supabase client doesn't require explicit cleanup)
    app_state.openai_client = None
    app_state.supabase_client = None
    app_state.embeddings_detector = None
    logger.info("Cleaned up application state")


app = FastAPI(
    title="Argus AI",
    description="Real-time API for detecting prompt injection attacks",
    version="0.1.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# CORS middleware for playground
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check endpoint (no authentication required)."""
    # Check if clients are initialized
    if app_state.embeddings_detector is None:
        return HealthResponse(status="degraded", version="0.1.0")
    return HealthResponse(status="healthy", version="0.1.0")


# Detection routes will be added in Step 8
# from app.api.routes import router as detect_router
# app.include_router(detect_router, prefix="/v1", tags=["Detection"])

"""FastAPI REST API for Gauntlet prompt injection detection.

Provides /detect and /health endpoints. The core Gauntlet detector
is synchronous, so detection runs in a thread pool via asyncio.to_thread().

Usage:
    uvicorn gauntlet.api:app --host 0.0.0.0 --port 8000
    # or via CLI:
    gauntlet serve
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any

from pydantic import BaseModel, Field

_detector = None


def _get_detector():
    global _detector
    if _detector is None:
        from gauntlet.detector import Gauntlet

        _detector = Gauntlet()
    return _detector


@asynccontextmanager
async def _lifespan(app: Any):
    """Initialize Gauntlet detector on startup."""
    from gauntlet._logging import setup_logging

    setup_logging()
    _get_detector()
    yield


class DetectRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text to analyze for prompt injection")
    layers: list[int] | None = Field(
        None, description="Specific layers to run (default: all available)"
    )


class LayerResultResponse(BaseModel):
    layer: int
    is_injection: bool
    confidence: float
    attack_type: str | None = None
    latency_ms: float


class DetectResponse(BaseModel):
    is_injection: bool
    confidence: float
    attack_type: str | None = None
    detected_by_layer: int | None = None
    layer_results: list[LayerResultResponse]
    total_latency_ms: float
    errors: list[str] = []
    layers_skipped: list[int] = []


class HealthResponse(BaseModel):
    status: str
    version: str
    available_layers: list[int]


def create_app():
    """Create and configure the FastAPI application."""
    try:
        from fastapi import FastAPI
    except ImportError:
        raise ImportError(
            "FastAPI is required for the API server. " "Install with: pip install gauntlet-ai[api]"
        )

    app = FastAPI(
        title="Gauntlet",
        description="Prompt injection detection API",
        version="0.2.0",
        lifespan=_lifespan,
    )

    @app.get("/health", response_model=HealthResponse)
    async def health():
        detector = _get_detector()
        return HealthResponse(
            status="healthy",
            version="0.2.0",
            available_layers=detector.available_layers,
        )

    @app.post("/detect", response_model=DetectResponse)
    async def detect(body: DetectRequest):
        detector = _get_detector()
        result = await asyncio.to_thread(detector.detect, body.text, body.layers)
        return DetectResponse(
            is_injection=result.is_injection,
            confidence=result.confidence,
            attack_type=result.attack_type,
            detected_by_layer=result.detected_by_layer,
            layer_results=[
                LayerResultResponse(
                    layer=lr.layer,
                    is_injection=lr.is_injection,
                    confidence=lr.confidence,
                    attack_type=lr.attack_type,
                    latency_ms=lr.latency_ms,
                )
                for lr in result.layer_results
            ],
            total_latency_ms=result.total_latency_ms,
            errors=result.errors or [],
            layers_skipped=result.layers_skipped or [],
        )

    return app


app = create_app()

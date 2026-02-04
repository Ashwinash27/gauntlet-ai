"""Detection API endpoint for prompt injection analysis."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.auth import APIKeyDep, APIKeyInfo
from app.core.config import get_settings
from app.detection.pipeline import DetectionPipeline, PipelineResult
from app.detection.rules import RulesDetector
from app.models.schemas import DetectRequest, LayerResult

router = APIRouter(prefix="/v1", tags=["detection"])


class DetectResponse(BaseModel):
    """Response body for the /v1/detect endpoint."""

    is_injection: bool = Field(
        ...,
        description="Whether the input is classified as a prompt injection attack",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score from the detecting layer (0-1)",
    )
    attack_type: str | None = Field(
        default=None,
        description="Type of attack detected (if any)",
    )
    detected_by_layer: int | None = Field(
        default=None,
        description="Which layer detected the injection (1, 2, or 3)",
    )
    layer_results: list[LayerResult] = Field(
        default_factory=list,
        description="Results from each layer that was executed",
    )
    latency_ms: float = Field(
        ...,
        ge=0.0,
        description="Total processing time in milliseconds",
    )


def get_pipeline(request: Request) -> DetectionPipeline:
    """
    Dependency to get the detection pipeline from app state.

    Creates a pipeline with available detectors from app state.
    Layer 3 (LLM) is optional and may not be available if
    ANTHROPIC_API_KEY is not configured.

    Args:
        request: FastAPI request object with app state.

    Returns:
        Configured DetectionPipeline instance.

    Raises:
        HTTPException: If core detectors are not initialized.
    """
    from app.main import app_state

    # Layer 1 (Rules) always available - no external dependencies
    rules_detector = RulesDetector()

    # Layer 2 (Embeddings) requires OpenAI and Supabase
    if app_state.embeddings_detector is None:
        raise HTTPException(
            status_code=503,
            detail="Detection service not available. Please check API configuration.",
        )

    # Layer 3 (LLM) is optional
    llm_detector = app_state.llm_detector  # May be None

    return DetectionPipeline(
        rules_detector=rules_detector,
        embeddings_detector=app_state.embeddings_detector,
        llm_detector=llm_detector,
    )


@router.post("/detect", response_model=DetectResponse)
async def detect_injection(
    request: DetectRequest,
    api_key: APIKeyDep,
    pipeline: DetectionPipeline = Depends(get_pipeline),
) -> DetectResponse:
    """
    Detect prompt injection in text.

    Runs the input through a 3-layer detection cascade:
    - **Layer 1 (Rules)**: Fast regex pattern matching (~0.1ms)
    - **Layer 2 (Embeddings)**: Semantic similarity search (~100ms)
    - **Layer 3 (LLM Judge)**: Claude reasoning analysis (~500ms)

    The cascade stops at the first layer that detects an injection,
    providing fast responses for obvious attacks.

    Args:
        request: Detection request with text to analyze.
        pipeline: Detection pipeline (injected dependency).

    Returns:
        DetectResponse with detection results and layer details.
    """
    settings = get_settings()

    # Validate input length
    if len(request.text) > settings.max_input_length:
        raise HTTPException(
            status_code=400,
            detail=f"Input exceeds maximum length of {settings.max_input_length} characters",
        )

    # Run detection
    result: PipelineResult = await pipeline.detect(
        text=request.text,
        skip_layer3=request.skip_layer3,
    )

    return DetectResponse(
        is_injection=result.is_injection,
        confidence=result.confidence,
        attack_type=result.attack_type,
        detected_by_layer=result.detected_by_layer,
        layer_results=result.layer_results,
        latency_ms=result.total_latency_ms,
    )


@router.get("/detect/health")
async def detect_health(request: Request) -> dict:
    """
    Check detection endpoint health and available layers.

    Returns:
        Dictionary with layer availability status.
    """
    from app.main import app_state

    return {
        "layer1_available": True,  # Rules always available
        "layer2_available": app_state.embeddings_detector is not None,
        "layer3_available": app_state.llm_detector is not None,
    }

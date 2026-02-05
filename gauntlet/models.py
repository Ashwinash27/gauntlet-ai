"""Pydantic models for Gauntlet detection results."""

from pydantic import BaseModel, Field


class LayerResult(BaseModel):
    """Result from a single detection layer."""

    is_injection: bool = Field(
        ...,
        description="Whether this layer detected an injection",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score from this layer",
    )
    attack_type: str | None = Field(
        default=None,
        description="Type of attack detected by this layer",
    )
    layer: int = Field(
        ...,
        ge=1,
        le=3,
        description="Which layer produced this result (1, 2, or 3)",
    )
    latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Time taken by this layer in milliseconds",
    )
    details: dict | None = Field(
        default=None,
        description="Layer-specific details",
    )
    error: str | None = Field(
        default=None,
        description="Error message if layer failed (fail-open)",
    )


class DetectionResult(BaseModel):
    """Result from the Gauntlet detection pipeline."""

    is_injection: bool = Field(
        ...,
        description="Whether any layer detected a prompt injection",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence from the detecting layer (or 0 if no detection)",
    )
    attack_type: str | None = Field(
        default=None,
        description="Type of attack detected (if any)",
    )
    detected_by_layer: int | None = Field(
        default=None,
        ge=1,
        le=3,
        description="Which layer made the detection (1, 2, or 3)",
    )
    layer_results: list[LayerResult] = Field(
        default_factory=list,
        description="Results from each layer that was executed",
    )
    total_latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Total time taken across all layers in milliseconds",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Errors from layers that failed open (layer ran but errored)",
    )
    layers_skipped: list[int] = Field(
        default_factory=list,
        description="Layer numbers that were requested but unavailable (missing deps/keys)",
    )

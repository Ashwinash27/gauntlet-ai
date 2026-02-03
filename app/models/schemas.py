"""Pydantic schemas for API requests and responses."""

from typing import Literal

from pydantic import BaseModel, Field


class DetectRequest(BaseModel):
    """Request body for the /v1/detect endpoint."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The user input text to analyze for prompt injection",
    )
    skip_layer3: bool = Field(
        default=False,
        description="Skip the LLM judge layer (faster, cheaper, less accurate)",
    )


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
        description="Confidence score between 0 and 1",
    )
    attack_type: str | None = Field(
        default=None,
        description="Type of attack detected (if any)",
    )
    details: dict | None = Field(
        default=None,
        description="Additional details about the detection",
    )


class HealthResponse(BaseModel):
    """Response body for the /health endpoint."""

    status: Literal["healthy", "degraded"] = Field(
        ...,
        description="Service health status",
    )
    version: str = Field(
        ...,
        description="API version",
    )


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

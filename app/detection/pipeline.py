"""Detection pipeline orchestrating the three-layer cascade.

This module provides the DetectionPipeline class that runs input text through
all three detection layers in sequence, stopping at the first detection.

Detection cascade: Layer 1 (rules/regex) → Layer 2 (embeddings) → Layer 3 (LLM judge)
"""

import logging
import time

from pydantic import BaseModel, Field

from app.detection.embeddings import EmbeddingsDetector
from app.detection.llm_judge import LLMDetector
from app.detection.rules import RulesDetector
from app.models.schemas import LayerResult

logger = logging.getLogger(__name__)


class PipelineResult(BaseModel):
    """Result from the detection pipeline."""

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
        description="Which layer made the detection (1, 2, or 3), or None if no detection",
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


class DetectionPipeline:
    """
    Three-layer cascade detection pipeline.

    Orchestrates the detection flow through:
    - Layer 1: Rules (fast regex pattern matching)
    - Layer 2: Embeddings (semantic similarity search)
    - Layer 3: LLM Judge (Claude reasoning)

    The pipeline stops at the first layer that detects an injection,
    providing fast responses for obvious attacks while using more
    expensive analysis only when needed.

    Attributes:
        rules_detector: Layer 1 regex-based detector.
        embeddings_detector: Layer 2 embedding similarity detector.
        llm_detector: Layer 3 LLM judge detector (optional).
    """

    def __init__(
        self,
        rules_detector: RulesDetector,
        embeddings_detector: EmbeddingsDetector,
        llm_detector: LLMDetector | None = None,
    ) -> None:
        """
        Initialize the detection pipeline.

        Args:
            rules_detector: Layer 1 detector for regex patterns.
            embeddings_detector: Layer 2 detector for embedding similarity.
            llm_detector: Layer 3 detector using LLM. Optional - if not provided,
                         pipeline will only run L1 and L2.
        """
        self.rules_detector = rules_detector
        self.embeddings_detector = embeddings_detector
        self.llm_detector = llm_detector

    async def detect(
        self,
        text: str,
        skip_layer3: bool = False,
    ) -> PipelineResult:
        """
        Run text through the detection cascade.

        Executes layers in sequence:
        1. Layer 1 (Rules) - ~0.1ms, catches obvious patterns
        2. Layer 2 (Embeddings) - ~100ms, catches semantic similarities
        3. Layer 3 (LLM) - ~500ms, catches sophisticated attacks

        Stops at the first layer that detects an injection.

        Args:
            text: The input text to analyze for prompt injection.
            skip_layer3: If True, skip the LLM layer (faster, cheaper).

        Returns:
            PipelineResult containing detection outcome and layer results.
        """
        start_time = time.perf_counter()
        layer_results: list[LayerResult] = []

        # Layer 1: Rules (fast regex)
        l1_result = self.rules_detector.detect(text)
        layer_results.append(l1_result)

        if l1_result.is_injection:
            total_latency = (time.perf_counter() - start_time) * 1000
            logger.info(
                f"Layer 1 detected injection: {l1_result.attack_type} "
                f"(confidence: {l1_result.confidence:.2f})"
            )
            return PipelineResult(
                is_injection=True,
                confidence=l1_result.confidence,
                attack_type=l1_result.attack_type,
                detected_by_layer=1,
                layer_results=layer_results,
                total_latency_ms=total_latency,
            )

        # Layer 2: Embeddings (semantic similarity)
        l2_result = await self.embeddings_detector.detect(text)
        layer_results.append(l2_result)

        if l2_result.is_injection:
            total_latency = (time.perf_counter() - start_time) * 1000
            logger.info(
                f"Layer 2 detected injection: {l2_result.attack_type} "
                f"(confidence: {l2_result.confidence:.2f})"
            )
            return PipelineResult(
                is_injection=True,
                confidence=l2_result.confidence,
                attack_type=l2_result.attack_type,
                detected_by_layer=2,
                layer_results=layer_results,
                total_latency_ms=total_latency,
            )

        # Layer 3: LLM Judge (reasoning)
        if not skip_layer3 and self.llm_detector is not None:
            l3_result = await self.llm_detector.detect(text)
            layer_results.append(l3_result)

            total_latency = (time.perf_counter() - start_time) * 1000

            if l3_result.is_injection:
                logger.info(
                    f"Layer 3 detected injection: {l3_result.attack_type} "
                    f"(confidence: {l3_result.confidence:.2f})"
                )
                return PipelineResult(
                    is_injection=True,
                    confidence=l3_result.confidence,
                    attack_type=l3_result.attack_type,
                    detected_by_layer=3,
                    layer_results=layer_results,
                    total_latency_ms=total_latency,
                )

            # Layer 3 ran but didn't detect
            return PipelineResult(
                is_injection=False,
                confidence=0.0,
                attack_type=None,
                detected_by_layer=None,
                layer_results=layer_results,
                total_latency_ms=total_latency,
            )

        # No detection, Layer 3 was skipped or not available
        total_latency = (time.perf_counter() - start_time) * 1000
        return PipelineResult(
            is_injection=False,
            confidence=0.0,
            attack_type=None,
            detected_by_layer=None,
            layer_results=layer_results,
            total_latency_ms=total_latency,
        )

    def has_layer3(self) -> bool:
        """Check if Layer 3 (LLM) is available."""
        return self.llm_detector is not None


__all__ = ["DetectionPipeline", "PipelineResult"]

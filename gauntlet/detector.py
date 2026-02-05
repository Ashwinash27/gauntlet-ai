"""Core Gauntlet detector with three-layer cascade.

Provides the Gauntlet class and detect() convenience function for
prompt injection detection.
"""

import logging
import time

from gauntlet.config import get_anthropic_key, get_openai_key
from gauntlet.layers.rules import RulesDetector
from gauntlet.models import DetectionResult, LayerResult

logger = logging.getLogger(__name__)


class Gauntlet:
    """Three-layer cascade prompt injection detector.

    Orchestrates detection through:
    - Layer 1: Rules (fast regex pattern matching) - always available
    - Layer 2: Embeddings (semantic similarity) - requires OpenAI key
    - Layer 3: LLM Judge (Claude reasoning) - requires Anthropic key

    The pipeline stops at the first layer that detects an injection.

    Examples:
        # Layer 1 only (zero config)
        g = Gauntlet()
        result = g.detect("ignore previous instructions")

        # All layers (BYOK)
        g = Gauntlet(openai_key="sk-...", anthropic_key="sk-ant-...")
        result = g.detect("subtle attack")

        # Auto-resolve keys from config/env
        g = Gauntlet()  # reads ~/.gauntlet/config.toml or env vars
    """

    def __init__(
        self,
        openai_key: str | None = None,
        anthropic_key: str | None = None,
        embedding_threshold: float = 0.55,
        embedding_model: str = "text-embedding-3-small",
        llm_model: str = "claude-3-haiku-20240307",
        llm_timeout: float = 3.0,
        confidence_threshold: float = 0.70,
    ) -> None:
        """Initialize the Gauntlet detector.

        Key resolution order:
        1. Constructor args
        2. Config file (~/.gauntlet/config.toml)
        3. Environment variables (OPENAI_API_KEY, ANTHROPIC_API_KEY)
        4. Layer 1 only (no keys needed)

        Args:
            openai_key: OpenAI API key for Layer 2.
            anthropic_key: Anthropic API key for Layer 3.
            embedding_threshold: Similarity threshold for Layer 2.
            embedding_model: OpenAI embedding model name.
            llm_model: Claude model name for Layer 3.
            llm_timeout: Timeout for Layer 3 API calls.
            confidence_threshold: Min confidence for Layer 3 detection.
        """
        # Resolve keys
        self._openai_key = openai_key or get_openai_key()
        self._anthropic_key = anthropic_key or get_anthropic_key()

        # Layer 1: Always available
        self._rules = RulesDetector()

        # Layer 2: Embeddings (lazy init)
        self._embeddings = None
        self._embedding_threshold = embedding_threshold
        self._embedding_model = embedding_model

        # Layer 3: LLM Judge (lazy init)
        self._llm = None
        self._llm_model = llm_model
        self._llm_timeout = llm_timeout
        self._confidence_threshold = confidence_threshold

    def _get_embeddings_detector(self):
        """Lazy-initialize Layer 2 detector."""
        if self._embeddings is None and self._openai_key:
            try:
                from gauntlet.layers.embeddings import EmbeddingsDetector
                self._embeddings = EmbeddingsDetector(
                    openai_key=self._openai_key,
                    threshold=self._embedding_threshold,
                    model=self._embedding_model,
                )
            except ImportError:
                logger.debug("Layer 2 deps not installed (openai, numpy)")
            except Exception as e:
                logger.warning("Failed to initialize Layer 2: %s", type(e).__name__)
        return self._embeddings

    def _get_llm_detector(self):
        """Lazy-initialize Layer 3 detector."""
        if self._llm is None and self._anthropic_key:
            try:
                from gauntlet.layers.llm_judge import LLMDetector
                self._llm = LLMDetector(
                    anthropic_key=self._anthropic_key,
                    model=self._llm_model,
                    timeout=self._llm_timeout,
                    confidence_threshold=self._confidence_threshold,
                )
            except ImportError:
                logger.debug("Layer 3 deps not installed (anthropic)")
            except Exception as e:
                logger.warning("Failed to initialize Layer 3: %s", type(e).__name__)
        return self._llm

    @property
    def available_layers(self) -> list[int]:
        """Return list of available layer numbers."""
        layers = [1]
        if self._openai_key:
            try:
                import numpy  # noqa: F401
                import openai  # noqa: F401
                layers.append(2)
            except ImportError:
                pass
        if self._anthropic_key:
            try:
                import anthropic  # noqa: F401
                layers.append(3)
            except ImportError:
                pass
        return layers

    def detect(
        self,
        text: str,
        layers: list[int] | None = None,
    ) -> DetectionResult:
        """Run text through the detection cascade.

        Args:
            text: The input text to analyze.
            layers: Specific layers to run (default: all available).
                    e.g., [1] for rules only, [1, 2] for rules + embeddings.

        Returns:
            DetectionResult with detection outcome and layer results.
        """
        if not text or not text.strip():
            return DetectionResult(
                is_injection=False,
                confidence=0.0,
                attack_type=None,
                detected_by_layer=None,
                layer_results=[],
                total_latency_ms=0.0,
            )

        start_time = time.perf_counter()
        layer_results: list[LayerResult] = []
        errors: list[str] = []
        layers_skipped: list[int] = []
        run_layers = layers or self.available_layers

        if layers:
            invalid = [l for l in layers if l not in (1, 2, 3)]
            if invalid:
                raise ValueError(f"Invalid layer numbers: {invalid}. Must be 1, 2, or 3.")

        def _build_result(
            is_injection: bool = False,
            confidence: float = 0.0,
            attack_type: str | None = None,
            detected_by_layer: int | None = None,
        ) -> DetectionResult:
            return DetectionResult(
                is_injection=is_injection,
                confidence=confidence,
                attack_type=attack_type,
                detected_by_layer=detected_by_layer,
                layer_results=layer_results,
                total_latency_ms=(time.perf_counter() - start_time) * 1000,
                errors=errors,
                layers_skipped=layers_skipped,
            )

        # Layer 1: Rules
        if 1 in run_layers:
            l1_result = self._rules.detect(text)
            layer_results.append(l1_result)

            if l1_result.error:
                errors.append(f"Layer 1 (rules): {l1_result.error}")

            if l1_result.is_injection:
                return _build_result(
                    is_injection=True,
                    confidence=l1_result.confidence,
                    attack_type=l1_result.attack_type,
                    detected_by_layer=1,
                )

        # Layer 2: Embeddings
        if 2 in run_layers:
            embeddings = self._get_embeddings_detector()
            if embeddings:
                l2_result = embeddings.detect(text)
                layer_results.append(l2_result)

                if l2_result.error:
                    errors.append(f"Layer 2 (embeddings): {l2_result.error}")

                if l2_result.is_injection:
                    return _build_result(
                        is_injection=True,
                        confidence=l2_result.confidence,
                        attack_type=l2_result.attack_type,
                        detected_by_layer=2,
                    )
            else:
                layers_skipped.append(2)

        # Layer 3: LLM Judge
        if 3 in run_layers:
            llm = self._get_llm_detector()
            if llm:
                l3_result = llm.detect(text)
                layer_results.append(l3_result)

                if l3_result.error:
                    errors.append(f"Layer 3 (llm_judge): {l3_result.error}")

                if l3_result.is_injection:
                    return _build_result(
                        is_injection=True,
                        confidence=l3_result.confidence,
                        attack_type=l3_result.attack_type,
                        detected_by_layer=3,
                    )
            else:
                layers_skipped.append(3)

        # No detection
        return _build_result()


def detect(text: str, **kwargs) -> DetectionResult:
    """Convenience function for quick detection.

    Uses Layer 1 (rules) only by default. Pass openai_key and/or
    anthropic_key for additional layers.

    Args:
        text: The input text to analyze.
        **kwargs: Passed to Gauntlet constructor.

    Returns:
        DetectionResult with detection outcome.

    Examples:
        # Layer 1 only
        result = detect("ignore previous instructions")

        # All layers
        result = detect("text", openai_key="sk-...", anthropic_key="sk-ant-...")
    """
    g = Gauntlet(**kwargs)
    return g.detect(text)


__all__ = ["Gauntlet", "detect"]

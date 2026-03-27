"""Core Gauntlet detector with three-layer cascade.

Provides the Gauntlet class and detect() convenience function for
prompt injection detection.
"""

import logging
import time

from gauntlet.config import get_anthropic_key, get_mode, get_openai_key, get_slm_model_path
from gauntlet.layers.rules import RulesDetector
from gauntlet._logging import _log_detection_event
from gauntlet.models import DetectionResult, LayerResult

logger = logging.getLogger(__name__)


class Gauntlet:
    """Three-layer cascade prompt injection detector.

    Orchestrates detection through:
    - Layer 1: Rules (fast regex pattern matching) - always available
    - Layer 2: Embeddings (semantic similarity) - OpenAI API (cloud) or BGE-small (slm)
    - Layer 3: LLM Judge - Claude API (cloud) or DeBERTa classifier (slm)

    The pipeline stops at the first layer that detects an injection.

    Examples:
        # Layer 1 only (zero config)
        g = Gauntlet()
        result = g.detect("ignore previous instructions")

        # Cloud mode - all layers (BYOK)
        g = Gauntlet(openai_key="sk-...", anthropic_key="sk-ant-...")
        result = g.detect("subtle attack")

        # SLM mode - all layers, no API keys, fully offline
        g = Gauntlet(mode="slm")
        result = g.detect("subtle attack")
    """

    def __init__(
        self,
        openai_key: str | None = None,
        anthropic_key: str | None = None,
        embedding_threshold: float = 0.80,
        embedding_model: str = "text-embedding-3-small",
        llm_model: str = "claude-3-haiku-20240307",
        llm_timeout: float = 3.0,
        confidence_threshold: float = 0.70,
        redis_url: str | None = None,
        cache_ttl: int = 3600,
        *,
        mode: str | None = None,
        slm_model_path: str | None = None,
    ) -> None:
        """Initialize the Gauntlet detector.

        Args:
            openai_key: OpenAI API key for Layer 2 (cloud mode).
            anthropic_key: Anthropic API key for Layer 3 (cloud mode).
            embedding_threshold: Similarity threshold for Layer 2.
            embedding_model: OpenAI embedding model name (cloud mode).
            llm_model: Claude model name for Layer 3 (cloud mode).
            llm_timeout: Timeout for Layer 3 API calls (cloud mode).
            confidence_threshold: Min confidence for Layer 3 detection.
            redis_url: Redis connection URL for caching (optional, opt-in).
            cache_ttl: Cache entry TTL in seconds (default: 3600).
            mode: "cloud" (default) or "slm" for local models. Resolved from
                  config/env (GAUNTLET_MODE) if not specified.
            slm_model_path: Path to SLM checkpoint directory (slm mode).
                            Defaults to training/checkpoints/deberta-v3-small-injection/best/
        """
        # Resolve mode: constructor > config > env > default "cloud"
        self._mode = mode or get_mode() or "cloud"
        if self._mode not in ("cloud", "slm"):
            raise ValueError(f"Invalid mode: {self._mode}. Must be 'cloud' or 'slm'.")

        # Resolve keys only in cloud mode
        if self._mode == "cloud":
            self._openai_key = openai_key or get_openai_key()
            self._anthropic_key = anthropic_key or get_anthropic_key()
        else:
            # SLM mode: skip key resolution entirely
            self._openai_key = None
            self._anthropic_key = None

        self._slm_model_path = slm_model_path or get_slm_model_path()

        # Cache (opt-in)
        self._cache = None
        if redis_url:
            try:
                from gauntlet.cache import RedisCache

                self._cache = RedisCache(url=redis_url, ttl=cache_ttl)
            except Exception as e:
                logger.warning("Failed to initialize cache: %s", type(e).__name__)

        # Layer 1: Always available
        self._rules = RulesDetector()

        # Layer 2: Embeddings (lazy init)
        self._embeddings = None
        self._embedding_threshold = embedding_threshold
        self._embedding_model = embedding_model

        # Layer 3: LLM/SLM Judge (lazy init)
        self._llm = None
        self._llm_model = llm_model
        self._llm_timeout = llm_timeout
        self._confidence_threshold = confidence_threshold

    def _get_embeddings_detector(self):
        """Lazy-initialize Layer 2 detector based on mode."""
        if self._embeddings is not None:
            return self._embeddings

        if self._mode == "slm":
            try:
                from gauntlet.layers.embeddings import EmbeddingsDetector

                self._embeddings = EmbeddingsDetector(
                    threshold=self._embedding_threshold,
                    mode="slm",
                )
            except ImportError:
                logger.debug("Layer 2 SLM deps not installed (sentence-transformers, numpy)")
            except Exception as e:
                logger.warning("Failed to initialize Layer 2 (SLM): %s", type(e).__name__)
        elif self._openai_key:
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
        """Lazy-initialize Layer 3 detector based on mode."""
        if self._llm is not None:
            return self._llm

        if self._mode == "slm":
            try:
                from gauntlet.layers.slm_judge import SLMDetector

                kwargs = {"confidence_threshold": self._confidence_threshold}
                if self._slm_model_path:
                    kwargs["model_path"] = self._slm_model_path
                self._llm = SLMDetector(**kwargs)
            except ImportError:
                logger.debug("Layer 3 SLM deps not installed (torch, transformers)")
            except Exception as e:
                logger.warning("Failed to initialize Layer 3 (SLM): %s", type(e).__name__)
        elif self._anthropic_key:
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

        if self._mode == "slm":
            try:
                import numpy  # noqa: F401
                import sentence_transformers  # noqa: F401

                layers.append(2)
            except ImportError:
                pass
            try:
                import torch  # noqa: F401
                import transformers  # noqa: F401

                layers.append(3)
            except ImportError:
                pass
        else:
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

        # Cache lookup
        if self._cache:
            cached = self._cache.get(text, run_layers)
            if cached is not None:
                logger.debug("Cache hit — returning cached result")
                return cached

        def _build_result(
            is_injection: bool = False,
            confidence: float = 0.0,
            attack_type: str | None = None,
            detected_by_layer: int | None = None,
        ) -> DetectionResult:
            result = DetectionResult(
                is_injection=is_injection,
                confidence=confidence,
                attack_type=attack_type,
                detected_by_layer=detected_by_layer,
                layer_results=layer_results,
                total_latency_ms=(time.perf_counter() - start_time) * 1000,
                errors=errors,
                layers_skipped=layers_skipped,
            )
            if self._cache:
                self._cache.set(text, run_layers, result)
            return result

        # Layer 1: Rules
        if 1 in run_layers:
            l1_result = self._rules.detect(text)
            layer_results.append(l1_result)
            _log_detection_event(
                text,
                1,
                l1_result.latency_ms,
                l1_result.is_injection,
                l1_result.attack_type,
                l1_result.confidence,
            )

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
                _log_detection_event(
                    text,
                    2,
                    l2_result.latency_ms,
                    l2_result.is_injection,
                    l2_result.attack_type,
                    l2_result.confidence,
                )

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
                _log_detection_event(
                    text,
                    3,
                    l3_result.latency_ms,
                    l3_result.is_injection,
                    l3_result.attack_type,
                    l3_result.confidence,
                )

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

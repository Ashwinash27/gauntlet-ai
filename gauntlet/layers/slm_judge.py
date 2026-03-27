"""Layer 3: Local SLM-based prompt injection detection.

Replaces the cloud-based LLM judge (Claude API) with a locally fine-tuned
DeBERTa-v3-small classifier. No API keys, no internet, no cost per inference.

Detection flow:
  Input text -> Tokenize -> DeBERTa forward pass -> Softmax -> confidence score

Requires: torch, transformers (already installed for training)
"""

import logging
import re
import threading
import time
from pathlib import Path

from gauntlet.models import LayerResult

logger = logging.getLogger(__name__)

# Default checkpoint from Phase 2 training
_DEFAULT_MODEL_PATH = (
    Path(__file__).parent.parent.parent / "training" / "checkpoints"
    / "deberta-v3-small-injection" / "best"
)

# Same categories as llm_judge.py for consistency
ATTACK_CATEGORIES = [
    "instruction_override",
    "jailbreak",
    "delimiter_injection",
    "data_extraction",
    "indirect_injection",
    "context_manipulation",
    "obfuscation",
    "hypothetical_framing",
    "multilingual_injection",
]

# Keywords for heuristic attack type classification
# (the binary classifier only outputs inject/benign, not attack type)
_CATEGORY_KEYWORDS = {
    "instruction_override": [
        "ignore", "disregard", "forget", "override", "previous instructions",
        "new instructions", "system prompt", "null and void",
    ],
    "jailbreak": [
        "DAN", "do anything now", "developer mode", "jailbreak", "STAN",
        "unrestricted", "no restrictions", "no limits",
    ],
    "delimiter_injection": [
        "```", "<|", "|>", "###", "---", "<system>", "</system>",
        "<instruction>", "BEGININSTRUCTION",
    ],
    "data_extraction": [
        "reveal", "show me your", "what are your instructions",
        "repeat your", "tell me your prompt", "secret", "password",
    ],
    "indirect_injection": [
        "when you see this", "if you read this", "hidden instruction",
        "embedded", "in the document",
    ],
    "context_manipulation": [
        "actually", "in reality", "the real instruction", "correction",
        "update:", "amendment", "the above is fake",
    ],
    "obfuscation": [
        "base64", "rot13", "hex", "encode", "decode", "\\x",
        "unicode", "leetspeak",
    ],
    "hypothetical_framing": [
        "hypothetically", "imagine", "roleplay", "pretend", "fiction",
        "for educational purposes", "what if", "in a story",
    ],
    "multilingual_injection": [
        "traduire", "übersetze", "traduce", "переведи",
        "ignorez", "vergessen", "ignora",
    ],
}


class SLMDetector:
    """Local fine-tuned classifier for prompt injection detection.

    This is Layer 3 of the detection cascade — designed to catch attacks
    that bypass Layer 1's regex patterns and Layer 2's embedding similarity.
    Uses the DeBERTa-v3-small model fine-tuned in Phase 2.

    Fail-open design: returns is_injection=False on any error.
    """

    def __init__(
        self,
        model_path: str | Path | None = None,
        confidence_threshold: float = 0.50,
        max_input_length: int = 10000,
        max_tokens: int = 256,
    ) -> None:
        """Initialize the SLM detector.

        Args:
            model_path: Path to the fine-tuned model checkpoint directory.
                        Defaults to training/checkpoints/deberta-v3-small-injection/best/
            confidence_threshold: Min confidence to flag as injection.
            max_input_length: Max character length before truncation.
            max_tokens: Max token length for tokenizer.
        """
        self._model_path = Path(model_path) if model_path else _DEFAULT_MODEL_PATH
        self.confidence_threshold = confidence_threshold
        self.max_input_length = max_input_length
        self.max_tokens = max_tokens

        # Lazy-loaded model and tokenizer
        self._model = None
        self._tokenizer = None
        self._lock = threading.Lock()

    def _ensure_loaded(self) -> None:
        """Lazy-load model and tokenizer on first use (thread-safe)."""
        if self._model is not None:
            return

        with self._lock:
            if self._model is not None:
                return

            import torch
            from transformers import (
                AutoModelForSequenceClassification,
                AutoTokenizer,
            )

            logger.info("Loading SLM model from %s", self._model_path)

            # use_fast=False: DeBERTa-v3 fast tokenizer is broken in
            # transformers >= 4.57 (convert_slow_tokenizer error)
            self._tokenizer = AutoTokenizer.from_pretrained(
                str(self._model_path),
                use_fast=False,
            )

            self._model = AutoModelForSequenceClassification.from_pretrained(
                str(self._model_path),
            )
            self._model.eval()

            self._torch = torch

            param_count = sum(p.numel() for p in self._model.parameters())
            logger.info("SLM model loaded: %.1fM params", param_count / 1e6)

    def _classify_attack_type(self, text: str) -> str | None:
        """Heuristic attack type classification based on keywords.

        The binary classifier only outputs inject/benign. This provides
        a best-guess attack category for the LayerResult.
        """
        text_lower = text.lower()
        best_category = None
        best_count = 0

        for category, keywords in _CATEGORY_KEYWORDS.items():
            count = sum(1 for kw in keywords if kw.lower() in text_lower)
            if count > best_count:
                best_count = count
                best_category = category

        return best_category if best_count > 0 else "prompt_injection"

    def _safe_result(self, latency_ms: float, error: str) -> LayerResult:
        """Return a fail-open result (not injection, zero confidence)."""
        return LayerResult(
            is_injection=False,
            confidence=0.0,
            attack_type=None,
            layer=3,
            latency_ms=latency_ms,
            details=None,
            error=error,
        )

    def detect(self, text: str) -> LayerResult:
        """Check text for prompt injection using the local SLM classifier.

        Args:
            text: The input text to analyze.

        Returns:
            LayerResult with detection outcome.
        """
        start_time = time.perf_counter()

        try:
            # Input validation
            if not text or not text.strip():
                latency_ms = (time.perf_counter() - start_time) * 1000
                return LayerResult(
                    is_injection=False,
                    confidence=0.0,
                    attack_type=None,
                    layer=3,
                    latency_ms=latency_ms,
                    details=None,
                )

            if len(text) > self.max_input_length:
                text = text[:self.max_input_length]

            # Load model if needed
            self._ensure_loaded()

            # Tokenize
            inputs = self._tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                padding="max_length",
                max_length=self.max_tokens,
                return_token_type_ids=False,
            )

            # Forward pass
            with self._torch.inference_mode():
                outputs = self._model(**inputs)
                logits = outputs.logits

                # Softmax -> [benign_prob, injection_prob]
                probs = self._torch.nn.functional.softmax(logits, dim=-1)
                injection_prob = float(probs[0, 1].item())
                injection_prob = max(0.0, min(1.0, injection_prob))

            latency_ms = (time.perf_counter() - start_time) * 1000

            is_injection = injection_prob >= self.confidence_threshold

            attack_type = None
            if is_injection:
                attack_type = self._classify_attack_type(text)

            return LayerResult(
                is_injection=is_injection,
                confidence=injection_prob,
                attack_type=attack_type,
                layer=3,
                latency_ms=latency_ms,
                details={
                    "model": "deberta-v3-small-injection",
                    "threshold": self.confidence_threshold,
                    "injection_probability": injection_prob,
                    "benign_probability": float(probs[0, 0].item()),
                },
            )

        except MemoryError as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.warning("SLM layer OOM after %.1fms: %s", latency_ms, e)
            return self._safe_result(latency_ms, f"OOM: {e}")

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(
                "SLM layer failed open after %.1fms: %s: %s",
                latency_ms, type(e).__name__, e,
            )
            logger.debug("SLM inference traceback:", exc_info=True)
            return self._safe_result(latency_ms, f"{type(e).__name__}: {e}")


__all__ = ["SLMDetector", "ATTACK_CATEGORIES"]

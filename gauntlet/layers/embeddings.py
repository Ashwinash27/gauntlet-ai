"""Layer 2: Embeddings-based prompt injection detection.

This module provides semantic similarity-based detection for prompt injection
attacks. It compares user input embeddings against pre-computed attack
embeddings using local numpy cosine similarity.

Detection flow: Input text -> OpenAI embedding -> Local cosine similarity -> threshold check

Requires: pip install gauntlet-ai[embeddings] (openai, numpy)
"""

import logging
import time
from dataclasses import dataclass
from pathlib import Path

from gauntlet.models import LayerResult

logger = logging.getLogger(__name__)

# Default paths for pre-computed data
_DATA_DIR = Path(__file__).parent.parent / "data"
_DEFAULT_EMBEDDINGS_PATH = _DATA_DIR / "embeddings.npz"
_DEFAULT_METADATA_PATH = _DATA_DIR / "metadata.json"


@dataclass
class SimilarityMatch:
    """A single similarity match from the embeddings database."""

    index: int
    category: str
    subcategory: str | None
    label: str
    similarity: float


class EmbeddingsDetector:
    """Semantic similarity-based detector using local cosine similarity.

    This is Layer 2 of the detection cascade - designed to catch attacks
    that bypass Layer 1's regex patterns by using semantic similarity
    to pre-computed attack embeddings shipped with the package.

    Requires an OpenAI API key for generating input embeddings.
    """

    def __init__(
        self,
        openai_key: str,
        threshold: float = 0.55,
        model: str = "text-embedding-3-small",
        embeddings_path: Path | None = None,
        metadata_path: Path | None = None,
    ) -> None:
        """Initialize the embeddings detector.

        Args:
            openai_key: OpenAI API key for generating embeddings.
            threshold: Similarity threshold (0.0-1.0). Default 0.55.
            model: Embedding model name.
            embeddings_path: Path to .npz file with pre-computed embeddings.
            metadata_path: Path to metadata JSON file.
        """
        try:
            import numpy as np
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "Layer 2 requires openai and numpy. "
                "Install with: pip install gauntlet-ai[embeddings]"
            )

        self._np = np
        self._client = OpenAI(api_key=openai_key, timeout=10.0)
        self.threshold = threshold
        self.model = model

        # Load pre-computed embeddings
        emb_path = embeddings_path or _DEFAULT_EMBEDDINGS_PATH
        meta_path = metadata_path or _DEFAULT_METADATA_PATH

        self._embeddings = None
        self._metadata = None

        if emb_path.exists():
            data = np.load(str(emb_path), allow_pickle=False)
            self._embeddings = data["embeddings"]
        else:
            logger.warning(f"Embeddings file not found: {emb_path}")

        if meta_path.exists():
            import json
            with open(meta_path) as f:
                self._metadata = json.load(f)
        else:
            logger.warning(f"Metadata file not found: {meta_path}")

    def _get_embedding(self, text: str) -> list[float]:
        """Generate embedding for input text using OpenAI API.

        Args:
            text: The input text to embed.

        Returns:
            List of floats representing the embedding vector.
        """
        response = self._client.embeddings.create(
            model=self.model,
            input=text,
        )
        return response.data[0].embedding

    def _cosine_similarity(self, query: list[float], threshold: float | None = None) -> list[tuple[int, float]]:
        """Compute cosine similarity between query and all stored embeddings.

        Args:
            query: The query embedding vector.
            threshold: Similarity threshold override. Uses self.threshold if None.

        Returns:
            List of (index, similarity) tuples sorted by similarity descending.
        """
        effective_threshold = threshold if threshold is not None else self.threshold
        np = self._np
        if self._embeddings is None:
            return []

        query_vec = np.array(query, dtype=np.float32)
        query_norm = np.linalg.norm(query_vec)
        if query_norm == 0:
            return []

        query_vec = query_vec / query_norm

        # Normalize stored embeddings (they should already be normalized, but just in case)
        norms = np.linalg.norm(self._embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        normalized = self._embeddings / norms

        similarities = normalized @ query_vec

        # Get indices sorted by similarity (descending)
        sorted_indices = np.argsort(similarities)[::-1]

        results = []
        for idx in sorted_indices:
            sim = float(similarities[idx])
            if sim < effective_threshold:
                break
            # Clamp to [0, 1] to handle floating-point precision
            sim = max(0.0, min(1.0, sim))
            results.append((int(idx), sim))

        return results

    def _get_match_metadata(self, index: int) -> dict:
        """Get metadata for a given embedding index."""
        if self._metadata and "patterns" in self._metadata:
            patterns = self._metadata["patterns"]
            if 0 <= index < len(patterns):
                return patterns[index]
        return {"category": "unknown", "subcategory": None, "label": "unknown"}

    def detect(self, text: str) -> LayerResult:
        """Check text for prompt injection using semantic similarity.

        Args:
            text: The input text to analyze.

        Returns:
            LayerResult with detection outcome.
        """
        start_time = time.perf_counter()

        try:
            if self._embeddings is None:
                latency_ms = (time.perf_counter() - start_time) * 1000
                return LayerResult(
                    is_injection=False,
                    confidence=0.0,
                    attack_type=None,
                    layer=2,
                    latency_ms=latency_ms,
                    details=None,
                    error="No pre-computed embeddings found",
                )

            embedding = self._get_embedding(text)
            matches = self._cosine_similarity(embedding)

            latency_ms = (time.perf_counter() - start_time) * 1000

            if matches:
                top_idx, top_sim = matches[0]
                meta = self._get_match_metadata(top_idx)
                return LayerResult(
                    is_injection=True,
                    confidence=top_sim,
                    attack_type=meta.get("category", "unknown"),
                    layer=2,
                    latency_ms=latency_ms,
                    details={
                        "similarity": top_sim,
                        "matched_category": meta.get("category"),
                        "matched_subcategory": meta.get("subcategory"),
                        "matched_label": meta.get("label"),
                        "threshold": self.threshold,
                        "total_matches": len(matches),
                    },
                )

            return LayerResult(
                is_injection=False,
                confidence=0.0,
                attack_type=None,
                layer=2,
                latency_ms=latency_ms,
                details={"threshold": self.threshold},
            )

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(f"Layer 2 embeddings detection failed: {e}")
            return LayerResult(
                is_injection=False,
                confidence=0.0,
                attack_type=None,
                layer=2,
                latency_ms=latency_ms,
                details=None,
                error=str(e),
            )

    def get_top_matches(self, text: str, top_k: int = 5) -> list[SimilarityMatch]:
        """Get top similarity matches for debugging/analysis.

        Args:
            text: The input text to analyze.
            top_k: Number of top matches to return.

        Returns:
            List of SimilarityMatch objects.
        """
        try:
            embedding = self._get_embedding(text)

            # Use lower threshold for debugging
            matches = self._cosine_similarity(embedding, threshold=0.3)

            results = []
            for idx, sim in matches[:top_k]:
                meta = self._get_match_metadata(idx)
                results.append(
                    SimilarityMatch(
                        index=idx,
                        category=meta.get("category", "unknown"),
                        subcategory=meta.get("subcategory"),
                        label=meta.get("label", "unknown"),
                        similarity=sim,
                    )
                )
            return results
        except Exception as e:
            logger.warning(f"get_top_matches failed: {e}")
            return []


__all__ = ["EmbeddingsDetector", "SimilarityMatch"]

"""Layer 2: Embeddings-based prompt injection detection.

This module provides semantic similarity-based detection for prompt injection
attacks. It compares user input embeddings against a database of known attack
embeddings using pgvector cosine similarity.

Detection flow: Input text -> OpenAI embedding -> Supabase pgvector search -> threshold check
"""

import logging
import time
from dataclasses import dataclass

from openai import AsyncOpenAI
from supabase import AsyncClient

from app.core.config import get_settings
from app.models.schemas import LayerResult

logger = logging.getLogger(__name__)


@dataclass
class SimilarityMatch:
    """A single similarity match from the embeddings database."""

    id: str
    attack_text: str
    category: str
    subcategory: str | None
    severity: float
    similarity: float


class EmbeddingsDetector:
    """
    Semantic similarity-based detector for prompt injection attacks.

    This is Layer 2 of the detection cascade - designed to catch attacks
    that bypass Layer 1's regex patterns by using semantic similarity
    to known attack embeddings stored in Supabase with pgvector.

    Features:
    - Uses OpenAI text-embedding-3-small (or large) for embeddings
    - Queries Supabase pgvector for cosine similarity search
    - Configurable similarity threshold (default 0.85)
    - Fail-open design: returns non-injection on errors

    Attributes:
        openai_client: Async OpenAI client for generating embeddings.
        supabase_client: Async Supabase client for similarity search.
        threshold: Similarity threshold for detection (0.0 to 1.0).
        model: OpenAI embedding model to use.
    """

    def __init__(
        self,
        openai_client: AsyncOpenAI,
        supabase_client: AsyncClient,
        threshold: float | None = None,
        model: str | None = None,
    ) -> None:
        """
        Initialize the embeddings detector.

        Args:
            openai_client: Async OpenAI client for generating embeddings.
            supabase_client: Async Supabase client for similarity search.
            threshold: Similarity threshold (0.0-1.0). Defaults to config value.
            model: Embedding model name. Defaults to config value.
        """
        settings = get_settings()
        self.openai_client = openai_client
        self.supabase_client = supabase_client
        self.threshold = threshold if threshold is not None else settings.embedding_threshold
        self.model = model or settings.embedding_model

    async def _get_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for input text using OpenAI API.

        Args:
            text: The input text to embed.

        Returns:
            List of floats representing the embedding vector.
        """
        response = await self.openai_client.embeddings.create(
            model=self.model,
            input=text,
        )
        return response.data[0].embedding

    async def _search_similar(
        self, embedding: list[float], threshold: float, limit: int
    ) -> list[SimilarityMatch]:
        """
        Search for similar attack embeddings in Supabase.

        Args:
            embedding: The query embedding vector.
            threshold: Minimum similarity threshold.
            limit: Maximum number of results to return.

        Returns:
            List of SimilarityMatch objects above threshold.
        """
        result = await self.supabase_client.rpc(
            "match_attack_embeddings",
            {
                "query_embedding": embedding,
                "match_threshold": threshold,
                "match_count": limit,
            },
        ).execute()

        matches = []
        for row in result.data or []:
            matches.append(
                SimilarityMatch(
                    id=row["id"],
                    attack_text=row["attack_text"],
                    category=row["category"],
                    subcategory=row.get("subcategory"),
                    severity=row["severity"],
                    similarity=row["similarity"],
                )
            )
        return matches

    async def detect(self, text: str) -> LayerResult:
        """
        Check text for prompt injection using semantic similarity.

        Args:
            text: The input text to analyze.

        Returns:
            LayerResult with detection outcome. Returns is_injection=True if
            any embedding matches above the configured threshold.

        Note:
            Fail-open design: Returns is_injection=False with error field
            on any failure to ensure service availability.
        """
        start_time = time.perf_counter()

        try:
            # Generate embedding for input text
            embedding = await self._get_embedding(text)

            # Search for similar attacks
            matches = await self._search_similar(
                embedding=embedding,
                threshold=self.threshold,
                limit=1,  # Only need top match for detection
            )

            latency_ms = (time.perf_counter() - start_time) * 1000

            if matches:
                top_match = matches[0]
                return LayerResult(
                    is_injection=True,
                    confidence=top_match.similarity,
                    attack_type=top_match.category,
                    layer=2,
                    latency_ms=latency_ms,
                    details={
                        "similarity": top_match.similarity,
                        "matched_category": top_match.category,
                        "matched_subcategory": top_match.subcategory,
                        "severity": top_match.severity,
                        "threshold": self.threshold,
                    },
                )

            # No similar attacks found
            return LayerResult(
                is_injection=False,
                confidence=0.0,
                attack_type=None,
                layer=2,
                latency_ms=latency_ms,
                details={"threshold": self.threshold},
            )

        except Exception as e:
            # Fail open: allow the request but log the error
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

    async def get_top_matches(self, text: str, top_k: int = 5) -> list[SimilarityMatch]:
        """
        Get top similarity matches for debugging/analysis.

        Args:
            text: The input text to analyze.
            top_k: Number of top matches to return.

        Returns:
            List of SimilarityMatch objects, sorted by similarity descending.
            Returns empty list on error.
        """
        try:
            embedding = await self._get_embedding(text)
            # Use lower threshold for debugging to see more matches
            return await self._search_similar(
                embedding=embedding,
                threshold=0.5,  # Lower threshold for debugging
                limit=top_k,
            )
        except Exception as e:
            logger.warning(f"get_top_matches failed: {e}")
            return []


__all__ = ["EmbeddingsDetector", "SimilarityMatch"]

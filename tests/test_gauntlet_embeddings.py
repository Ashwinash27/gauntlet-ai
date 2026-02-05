"""Tests for Gauntlet Layer 2: Embeddings-based prompt injection detection."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from gauntlet.models import LayerResult


# ---------------------------------------------------------------------------
# Helpers for creating fake embeddings data
# ---------------------------------------------------------------------------

def _make_embeddings_file(tmp_path: Path, n_vectors: int = 5, dim: int = 8) -> Path:
    """Create a temporary .npz file with random embeddings."""
    rng = np.random.default_rng(42)
    vectors = rng.random((n_vectors, dim)).astype(np.float32)
    # Normalize so cosine similarity computations are predictable
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors = vectors / norms
    path = tmp_path / "embeddings.npz"
    np.savez(str(path), embeddings=vectors)
    return path


def _make_metadata_file(tmp_path: Path, n_vectors: int = 5) -> Path:
    """Create a temporary metadata JSON file."""
    patterns = []
    for i in range(n_vectors):
        patterns.append({
            "category": f"category_{i}",
            "subcategory": f"sub_{i}",
            "label": f"label_{i}",
        })
    path = tmp_path / "metadata.json"
    path.write_text(json.dumps({"patterns": patterns}))
    return path


def _fake_openai_embedding(dim: int = 8) -> list[float]:
    """Return a deterministic fake embedding vector."""
    rng = np.random.default_rng(99)
    vec = rng.random(dim).astype(np.float32)
    vec = vec / np.linalg.norm(vec)
    return vec.tolist()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def embeddings_files(tmp_path: Path) -> tuple[Path, Path]:
    """Create temporary embeddings and metadata files."""
    emb_path = _make_embeddings_file(tmp_path, n_vectors=5, dim=8)
    meta_path = _make_metadata_file(tmp_path, n_vectors=5)
    return emb_path, meta_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEmbeddingsDetectorInit:
    """Tests for EmbeddingsDetector initialization."""

    @patch("openai.OpenAI")
    def test_init_with_embeddings_file(self, mock_openai_cls, embeddings_files: tuple[Path, Path]) -> None:
        """Should load embeddings and metadata when files exist."""
        from gauntlet.layers.embeddings import EmbeddingsDetector

        emb_path, meta_path = embeddings_files
        detector = EmbeddingsDetector(
            openai_key="sk-test-key",
            embeddings_path=emb_path,
            metadata_path=meta_path,
        )
        assert detector._embeddings is not None
        assert detector._embeddings.shape == (5, 8)
        assert detector._metadata is not None
        assert len(detector._metadata["patterns"]) == 5

    @patch("openai.OpenAI")
    def test_init_without_embeddings_file(self, mock_openai_cls, tmp_path: Path) -> None:
        """Should gracefully handle missing embeddings file."""
        from gauntlet.layers.embeddings import EmbeddingsDetector

        missing_emb = tmp_path / "nonexistent.npz"
        missing_meta = tmp_path / "nonexistent.json"
        detector = EmbeddingsDetector(
            openai_key="sk-test-key",
            embeddings_path=missing_emb,
            metadata_path=missing_meta,
        )
        assert detector._embeddings is None
        assert detector._metadata is None

    @patch("openai.OpenAI")
    def test_init_default_threshold(self, mock_openai_cls, embeddings_files: tuple[Path, Path]) -> None:
        """Should use default threshold of 0.55."""
        from gauntlet.layers.embeddings import EmbeddingsDetector

        emb_path, meta_path = embeddings_files
        detector = EmbeddingsDetector(
            openai_key="sk-test-key",
            embeddings_path=emb_path,
            metadata_path=meta_path,
        )
        assert detector.threshold == 0.55

    @patch("openai.OpenAI")
    def test_init_custom_threshold(self, mock_openai_cls, embeddings_files: tuple[Path, Path]) -> None:
        """Should accept custom threshold."""
        from gauntlet.layers.embeddings import EmbeddingsDetector

        emb_path, meta_path = embeddings_files
        detector = EmbeddingsDetector(
            openai_key="sk-test-key",
            threshold=0.80,
            embeddings_path=emb_path,
            metadata_path=meta_path,
        )
        assert detector.threshold == 0.80


class TestCosineSimilarity:
    """Tests for cosine similarity computation."""

    @patch("openai.OpenAI")
    def test_cosine_similarity_returns_sorted_results(
        self, mock_openai_cls, embeddings_files: tuple[Path, Path]
    ) -> None:
        """Should return matches sorted by similarity descending."""
        from gauntlet.layers.embeddings import EmbeddingsDetector

        emb_path, meta_path = embeddings_files
        detector = EmbeddingsDetector(
            openai_key="sk-test-key",
            threshold=0.0,  # very low to get all matches
            embeddings_path=emb_path,
            metadata_path=meta_path,
        )

        query = _fake_openai_embedding(dim=8)
        results = detector._cosine_similarity(query)
        assert len(results) > 0
        # Verify sorted by similarity descending
        similarities = [sim for _, sim in results]
        assert similarities == sorted(similarities, reverse=True)

    @patch("openai.OpenAI")
    def test_cosine_similarity_respects_threshold(
        self, mock_openai_cls, embeddings_files: tuple[Path, Path]
    ) -> None:
        """Should filter out results below threshold."""
        from gauntlet.layers.embeddings import EmbeddingsDetector

        emb_path, meta_path = embeddings_files
        detector = EmbeddingsDetector(
            openai_key="sk-test-key",
            threshold=0.99,  # very high threshold
            embeddings_path=emb_path,
            metadata_path=meta_path,
        )

        query = _fake_openai_embedding(dim=8)
        results = detector._cosine_similarity(query)
        # With threshold 0.99, almost certainly no matches from random vectors
        for _, sim in results:
            assert sim >= 0.99

    @patch("openai.OpenAI")
    def test_cosine_similarity_empty_when_no_embeddings(
        self, mock_openai_cls, tmp_path: Path
    ) -> None:
        """Should return empty list when no embeddings loaded."""
        from gauntlet.layers.embeddings import EmbeddingsDetector

        detector = EmbeddingsDetector(
            openai_key="sk-test-key",
            embeddings_path=tmp_path / "nonexistent.npz",
            metadata_path=tmp_path / "nonexistent.json",
        )
        query = _fake_openai_embedding(dim=8)
        results = detector._cosine_similarity(query)
        assert results == []

    @patch("openai.OpenAI")
    def test_cosine_similarity_zero_vector(
        self, mock_openai_cls, embeddings_files: tuple[Path, Path]
    ) -> None:
        """Should return empty list for zero vector query."""
        from gauntlet.layers.embeddings import EmbeddingsDetector

        emb_path, meta_path = embeddings_files
        detector = EmbeddingsDetector(
            openai_key="sk-test-key",
            threshold=0.0,
            embeddings_path=emb_path,
            metadata_path=meta_path,
        )
        zero_query = [0.0] * 8
        results = detector._cosine_similarity(zero_query)
        assert results == []


class TestDetect:
    """Tests for the detect() method."""

    @patch("openai.OpenAI")
    def test_detect_injection_above_threshold(
        self, mock_openai_cls, tmp_path: Path
    ) -> None:
        """Should detect injection when similarity exceeds threshold."""
        from gauntlet.layers.embeddings import EmbeddingsDetector

        # Create embeddings where one vector is very similar to our query
        dim = 8
        query_vec = np.array(_fake_openai_embedding(dim=dim), dtype=np.float32)
        # Store a near-identical vector plus some random ones
        rng = np.random.default_rng(0)
        vectors = rng.random((5, dim)).astype(np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        vectors = vectors / norms
        # Replace first vector with query itself (perfect match)
        vectors[0] = query_vec
        emb_path = tmp_path / "embeddings.npz"
        np.savez(str(emb_path), embeddings=vectors)
        meta_path = _make_metadata_file(tmp_path, n_vectors=5)

        detector = EmbeddingsDetector(
            openai_key="sk-test-key",
            threshold=0.55,
            embeddings_path=emb_path,
            metadata_path=meta_path,
        )

        # Mock the OpenAI embedding call to return the same vector
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=query_vec.tolist())]
        detector._client.embeddings.create = MagicMock(return_value=mock_response)

        result = detector.detect("ignore previous instructions")

        assert isinstance(result, LayerResult)
        assert result.is_injection is True
        assert result.layer == 2
        assert result.confidence >= 0.99  # near-perfect match
        assert result.attack_type == "category_0"
        assert result.details is not None
        assert "similarity" in result.details
        assert "threshold" in result.details

    @patch("openai.OpenAI")
    def test_detect_benign_below_threshold(
        self, mock_openai_cls, embeddings_files: tuple[Path, Path]
    ) -> None:
        """Should not detect injection when similarity is below threshold."""
        from gauntlet.layers.embeddings import EmbeddingsDetector

        emb_path, meta_path = embeddings_files
        detector = EmbeddingsDetector(
            openai_key="sk-test-key",
            threshold=0.99,  # very high threshold
            embeddings_path=emb_path,
            metadata_path=meta_path,
        )

        # Return a random embedding that won't be close to stored vectors
        mock_response = MagicMock()
        rng = np.random.default_rng(777)
        random_emb = rng.random(8).tolist()
        mock_response.data = [MagicMock(embedding=random_emb)]
        detector._client.embeddings.create = MagicMock(return_value=mock_response)

        result = detector.detect("Hello, how are you?")

        assert isinstance(result, LayerResult)
        assert result.is_injection is False
        assert result.layer == 2
        assert result.confidence == 0.0

    @patch("openai.OpenAI")
    def test_detect_no_embeddings_loaded(
        self, mock_openai_cls, tmp_path: Path
    ) -> None:
        """Should return non-injection result with error when no embeddings."""
        from gauntlet.layers.embeddings import EmbeddingsDetector

        detector = EmbeddingsDetector(
            openai_key="sk-test-key",
            embeddings_path=tmp_path / "nonexistent.npz",
            metadata_path=tmp_path / "nonexistent.json",
        )

        result = detector.detect("test text")

        assert result.is_injection is False
        assert result.layer == 2
        assert result.error is not None
        assert "No pre-computed embeddings" in result.error


class TestFailOpen:
    """Tests for fail-open behavior on API errors."""

    @patch("openai.OpenAI")
    def test_fail_open_on_api_error(
        self, mock_openai_cls, embeddings_files: tuple[Path, Path]
    ) -> None:
        """Should fail open (allow request) when OpenAI API raises an error."""
        from gauntlet.layers.embeddings import EmbeddingsDetector

        emb_path, meta_path = embeddings_files
        detector = EmbeddingsDetector(
            openai_key="sk-test-key",
            embeddings_path=emb_path,
            metadata_path=meta_path,
        )

        # Mock embedding call to raise an exception
        detector._client.embeddings.create = MagicMock(
            side_effect=Exception("API rate limit exceeded")
        )

        result = detector.detect("test text")

        assert result.is_injection is False
        assert result.layer == 2
        assert result.error is not None
        assert "rate limit" in result.error.lower()

    @patch("openai.OpenAI")
    def test_fail_open_on_timeout(
        self, mock_openai_cls, embeddings_files: tuple[Path, Path]
    ) -> None:
        """Should fail open on timeout errors."""
        from gauntlet.layers.embeddings import EmbeddingsDetector

        emb_path, meta_path = embeddings_files
        detector = EmbeddingsDetector(
            openai_key="sk-test-key",
            embeddings_path=emb_path,
            metadata_path=meta_path,
        )

        detector._client.embeddings.create = MagicMock(
            side_effect=TimeoutError("Connection timed out")
        )

        result = detector.detect("test text")

        assert result.is_injection is False
        assert result.error is not None


class TestResultFormat:
    """Tests for proper LayerResult format from embeddings layer."""

    @patch("openai.OpenAI")
    def test_positive_result_format(self, mock_openai_cls, tmp_path: Path) -> None:
        """Positive result should have all expected fields."""
        from gauntlet.layers.embeddings import EmbeddingsDetector

        dim = 8
        query_vec = np.array(_fake_openai_embedding(dim=dim), dtype=np.float32)
        vectors = np.zeros((3, dim), dtype=np.float32)
        vectors[0] = query_vec  # perfect match
        vectors[1] = -query_vec  # anti-match
        rng = np.random.default_rng(0)
        vectors[2] = rng.random(dim).astype(np.float32)
        vectors[2] /= np.linalg.norm(vectors[2])
        emb_path = tmp_path / "embeddings.npz"
        np.savez(str(emb_path), embeddings=vectors)
        meta_path = _make_metadata_file(tmp_path, n_vectors=3)

        detector = EmbeddingsDetector(
            openai_key="sk-test-key",
            threshold=0.55,
            embeddings_path=emb_path,
            metadata_path=meta_path,
        )
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=query_vec.tolist())]
        detector._client.embeddings.create = MagicMock(return_value=mock_response)

        result = detector.detect("test injection")

        assert result.layer == 2
        assert result.is_injection is True
        assert 0.0 <= result.confidence <= 1.0
        assert result.attack_type is not None
        assert result.latency_ms >= 0
        assert result.details is not None
        assert "similarity" in result.details
        assert "matched_category" in result.details
        assert "matched_subcategory" in result.details
        assert "matched_label" in result.details
        assert "threshold" in result.details
        assert "total_matches" in result.details

    @patch("openai.OpenAI")
    def test_negative_result_format(
        self, mock_openai_cls, embeddings_files: tuple[Path, Path]
    ) -> None:
        """Negative result should have correct format."""
        from gauntlet.layers.embeddings import EmbeddingsDetector

        emb_path, meta_path = embeddings_files
        detector = EmbeddingsDetector(
            openai_key="sk-test-key",
            threshold=0.99,
            embeddings_path=emb_path,
            metadata_path=meta_path,
        )
        mock_response = MagicMock()
        rng = np.random.default_rng(777)
        mock_response.data = [MagicMock(embedding=rng.random(8).tolist())]
        detector._client.embeddings.create = MagicMock(return_value=mock_response)

        result = detector.detect("Hello world")

        assert result.layer == 2
        assert result.is_injection is False
        assert result.confidence == 0.0
        assert result.attack_type is None
        assert result.latency_ms >= 0
        assert result.error is None
        assert result.details is not None
        assert "threshold" in result.details


class TestGetMatchMetadata:
    """Tests for metadata retrieval."""

    @patch("openai.OpenAI")
    def test_get_match_metadata_valid_index(
        self, mock_openai_cls, embeddings_files: tuple[Path, Path]
    ) -> None:
        """Should return metadata for valid index."""
        from gauntlet.layers.embeddings import EmbeddingsDetector

        emb_path, meta_path = embeddings_files
        detector = EmbeddingsDetector(
            openai_key="sk-test-key",
            embeddings_path=emb_path,
            metadata_path=meta_path,
        )
        meta = detector._get_match_metadata(0)
        assert meta["category"] == "category_0"
        assert meta["subcategory"] == "sub_0"
        assert meta["label"] == "label_0"

    @patch("openai.OpenAI")
    def test_get_match_metadata_out_of_range(
        self, mock_openai_cls, embeddings_files: tuple[Path, Path]
    ) -> None:
        """Should return defaults for out-of-range index."""
        from gauntlet.layers.embeddings import EmbeddingsDetector

        emb_path, meta_path = embeddings_files
        detector = EmbeddingsDetector(
            openai_key="sk-test-key",
            embeddings_path=emb_path,
            metadata_path=meta_path,
        )
        meta = detector._get_match_metadata(999)
        assert meta["category"] == "unknown"

    @patch("openai.OpenAI")
    def test_get_match_metadata_no_metadata(
        self, mock_openai_cls, tmp_path: Path
    ) -> None:
        """Should return defaults when no metadata loaded."""
        from gauntlet.layers.embeddings import EmbeddingsDetector

        emb_path = _make_embeddings_file(tmp_path)
        detector = EmbeddingsDetector(
            openai_key="sk-test-key",
            embeddings_path=emb_path,
            metadata_path=tmp_path / "nonexistent.json",
        )
        meta = detector._get_match_metadata(0)
        assert meta["category"] == "unknown"

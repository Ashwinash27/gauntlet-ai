"""Tests for Gauntlet Pydantic models."""

import pytest
from pydantic import ValidationError

from gauntlet.models import DetectionResult, LayerResult


# ---------------------------------------------------------------------------
# Tests: LayerResult
# ---------------------------------------------------------------------------

class TestLayerResult:
    """Tests for the LayerResult model."""

    def test_create_minimal_result(self) -> None:
        """Should create a LayerResult with required fields only."""
        result = LayerResult(is_injection=False, layer=1)
        assert result.is_injection is False
        assert result.layer == 1
        assert result.confidence == 0.0
        assert result.attack_type is None
        assert result.latency_ms == 0.0
        assert result.details is None
        assert result.error is None

    def test_create_full_injection_result(self) -> None:
        """Should create a LayerResult with all fields populated."""
        result = LayerResult(
            is_injection=True,
            confidence=0.95,
            attack_type="jailbreak",
            layer=1,
            latency_ms=1.5,
            details={"pattern_name": "dan_jailbreak"},
            error=None,
        )
        assert result.is_injection is True
        assert result.confidence == 0.95
        assert result.attack_type == "jailbreak"
        assert result.layer == 1
        assert result.latency_ms == 1.5
        assert result.details == {"pattern_name": "dan_jailbreak"}
        assert result.error is None

    def test_create_error_result(self) -> None:
        """Should create a LayerResult with error field."""
        result = LayerResult(
            is_injection=False,
            layer=2,
            error="API connection failed",
        )
        assert result.error == "API connection failed"

    # --- Confidence bounds ---

    def test_confidence_zero(self) -> None:
        """Should accept confidence of 0.0."""
        result = LayerResult(is_injection=False, confidence=0.0, layer=1)
        assert result.confidence == 0.0

    def test_confidence_one(self) -> None:
        """Should accept confidence of 1.0."""
        result = LayerResult(is_injection=True, confidence=1.0, layer=1)
        assert result.confidence == 1.0

    def test_confidence_midpoint(self) -> None:
        """Should accept confidence of 0.5."""
        result = LayerResult(is_injection=False, confidence=0.5, layer=1)
        assert result.confidence == 0.5

    def test_confidence_above_1_raises(self) -> None:
        """Should reject confidence above 1.0."""
        with pytest.raises(ValidationError):
            LayerResult(is_injection=True, confidence=1.1, layer=1)

    def test_confidence_below_0_raises(self) -> None:
        """Should reject confidence below 0.0."""
        with pytest.raises(ValidationError):
            LayerResult(is_injection=False, confidence=-0.1, layer=1)

    # --- Layer bounds ---

    def test_layer_1(self) -> None:
        """Should accept layer=1."""
        result = LayerResult(is_injection=False, layer=1)
        assert result.layer == 1

    def test_layer_2(self) -> None:
        """Should accept layer=2."""
        result = LayerResult(is_injection=False, layer=2)
        assert result.layer == 2

    def test_layer_3(self) -> None:
        """Should accept layer=3."""
        result = LayerResult(is_injection=False, layer=3)
        assert result.layer == 3

    def test_layer_0_raises(self) -> None:
        """Should reject layer=0."""
        with pytest.raises(ValidationError):
            LayerResult(is_injection=False, layer=0)

    def test_layer_4_raises(self) -> None:
        """Should reject layer=4."""
        with pytest.raises(ValidationError):
            LayerResult(is_injection=False, layer=4)

    def test_layer_negative_raises(self) -> None:
        """Should reject negative layer."""
        with pytest.raises(ValidationError):
            LayerResult(is_injection=False, layer=-1)

    # --- Latency bounds ---

    def test_latency_zero(self) -> None:
        """Should accept latency_ms of 0.0."""
        result = LayerResult(is_injection=False, layer=1, latency_ms=0.0)
        assert result.latency_ms == 0.0

    def test_latency_positive(self) -> None:
        """Should accept positive latency_ms."""
        result = LayerResult(is_injection=False, layer=1, latency_ms=123.45)
        assert result.latency_ms == 123.45

    def test_latency_negative_raises(self) -> None:
        """Should reject negative latency_ms."""
        with pytest.raises(ValidationError):
            LayerResult(is_injection=False, layer=1, latency_ms=-1.0)

    # --- Serialization ---

    def test_serializes_to_dict(self) -> None:
        """Should serialize to dictionary."""
        result = LayerResult(
            is_injection=True,
            confidence=0.95,
            attack_type="jailbreak",
            layer=1,
            latency_ms=2.0,
            details={"key": "value"},
        )
        data = result.model_dump()
        assert isinstance(data, dict)
        assert data["is_injection"] is True
        assert data["confidence"] == 0.95
        assert data["attack_type"] == "jailbreak"
        assert data["layer"] == 1
        assert data["latency_ms"] == 2.0
        assert data["details"] == {"key": "value"}
        assert data["error"] is None

    def test_serializes_to_json(self) -> None:
        """Should serialize to JSON string."""
        result = LayerResult(
            is_injection=False,
            layer=2,
            latency_ms=50.0,
        )
        json_str = result.model_dump_json()
        assert isinstance(json_str, str)
        assert '"is_injection":false' in json_str or '"is_injection": false' in json_str


# ---------------------------------------------------------------------------
# Tests: DetectionResult
# ---------------------------------------------------------------------------

class TestDetectionResult:
    """Tests for the DetectionResult model."""

    def test_create_minimal_result(self) -> None:
        """Should create a DetectionResult with required fields only."""
        result = DetectionResult(is_injection=False)
        assert result.is_injection is False
        assert result.confidence == 0.0
        assert result.attack_type is None
        assert result.detected_by_layer is None
        assert result.layer_results == []
        assert result.total_latency_ms == 0.0

    def test_create_full_injection_result(self) -> None:
        """Should create a DetectionResult with all fields populated."""
        layer_result = LayerResult(
            is_injection=True,
            confidence=0.95,
            attack_type="jailbreak",
            layer=1,
            latency_ms=1.5,
        )
        result = DetectionResult(
            is_injection=True,
            confidence=0.95,
            attack_type="jailbreak",
            detected_by_layer=1,
            layer_results=[layer_result],
            total_latency_ms=1.5,
        )
        assert result.is_injection is True
        assert result.confidence == 0.95
        assert result.attack_type == "jailbreak"
        assert result.detected_by_layer == 1
        assert len(result.layer_results) == 1
        assert result.total_latency_ms == 1.5

    def test_create_multi_layer_result(self) -> None:
        """Should create a DetectionResult with multiple layer results."""
        lr1 = LayerResult(is_injection=False, layer=1, latency_ms=0.5)
        lr2 = LayerResult(
            is_injection=True,
            confidence=0.88,
            attack_type="semantic_attack",
            layer=2,
            latency_ms=50.0,
        )
        result = DetectionResult(
            is_injection=True,
            confidence=0.88,
            attack_type="semantic_attack",
            detected_by_layer=2,
            layer_results=[lr1, lr2],
            total_latency_ms=50.5,
        )
        assert len(result.layer_results) == 2
        assert result.layer_results[0].layer == 1
        assert result.layer_results[1].layer == 2
        assert result.detected_by_layer == 2

    # --- Confidence bounds ---

    def test_confidence_bounds_valid(self) -> None:
        """Should accept confidence between 0.0 and 1.0."""
        for c in [0.0, 0.5, 1.0]:
            result = DetectionResult(is_injection=False, confidence=c)
            assert result.confidence == c

    def test_confidence_above_1_raises(self) -> None:
        """Should reject confidence above 1.0."""
        with pytest.raises(ValidationError):
            DetectionResult(is_injection=True, confidence=1.5)

    def test_confidence_below_0_raises(self) -> None:
        """Should reject confidence below 0.0."""
        with pytest.raises(ValidationError):
            DetectionResult(is_injection=False, confidence=-0.1)

    # --- detected_by_layer bounds ---

    def test_detected_by_layer_valid(self) -> None:
        """Should accept detected_by_layer 1, 2, or 3."""
        for layer in [1, 2, 3]:
            result = DetectionResult(
                is_injection=True,
                detected_by_layer=layer,
            )
            assert result.detected_by_layer == layer

    def test_detected_by_layer_none(self) -> None:
        """Should accept None for detected_by_layer."""
        result = DetectionResult(is_injection=False, detected_by_layer=None)
        assert result.detected_by_layer is None

    def test_detected_by_layer_0_raises(self) -> None:
        """Should reject detected_by_layer=0."""
        with pytest.raises(ValidationError):
            DetectionResult(is_injection=True, detected_by_layer=0)

    def test_detected_by_layer_4_raises(self) -> None:
        """Should reject detected_by_layer=4."""
        with pytest.raises(ValidationError):
            DetectionResult(is_injection=True, detected_by_layer=4)

    # --- total_latency_ms bounds ---

    def test_total_latency_zero(self) -> None:
        """Should accept total_latency_ms of 0.0."""
        result = DetectionResult(is_injection=False, total_latency_ms=0.0)
        assert result.total_latency_ms == 0.0

    def test_total_latency_positive(self) -> None:
        """Should accept positive total_latency_ms."""
        result = DetectionResult(is_injection=False, total_latency_ms=250.5)
        assert result.total_latency_ms == 250.5

    def test_total_latency_negative_raises(self) -> None:
        """Should reject negative total_latency_ms."""
        with pytest.raises(ValidationError):
            DetectionResult(is_injection=False, total_latency_ms=-1.0)

    # --- Serialization ---

    def test_serializes_to_dict(self) -> None:
        """Should serialize to dictionary including nested layer results."""
        lr = LayerResult(is_injection=True, confidence=0.90, layer=1, latency_ms=1.0)
        result = DetectionResult(
            is_injection=True,
            confidence=0.90,
            attack_type="instruction_override",
            detected_by_layer=1,
            layer_results=[lr],
            total_latency_ms=1.0,
        )
        data = result.model_dump()
        assert isinstance(data, dict)
        assert data["is_injection"] is True
        assert len(data["layer_results"]) == 1
        assert data["layer_results"][0]["layer"] == 1

    def test_serializes_to_json(self) -> None:
        """Should serialize to JSON string."""
        result = DetectionResult(is_injection=False)
        json_str = result.model_dump_json()
        assert isinstance(json_str, str)
        assert "is_injection" in json_str

    def test_round_trip_serialization(self) -> None:
        """Should survive a dict -> model round trip."""
        lr = LayerResult(
            is_injection=True,
            confidence=0.85,
            attack_type="data_extraction",
            layer=2,
            latency_ms=45.0,
            details={"similarity": 0.85},
        )
        original = DetectionResult(
            is_injection=True,
            confidence=0.85,
            attack_type="data_extraction",
            detected_by_layer=2,
            layer_results=[lr],
            total_latency_ms=45.0,
        )
        data = original.model_dump()
        restored = DetectionResult(**data)
        assert restored.is_injection == original.is_injection
        assert restored.confidence == original.confidence
        assert restored.detected_by_layer == original.detected_by_layer
        assert len(restored.layer_results) == len(original.layer_results)

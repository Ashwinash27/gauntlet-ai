"""Gauntlet - Prompt injection detection for LLM applications.

Runs locally. Bring your own keys.

Examples:
    # Layer 1 only (zero config, zero deps)
    from gauntlet import detect
    result = detect("ignore previous instructions")

    # All layers (BYOK)
    from gauntlet import Gauntlet
    g = Gauntlet(openai_key="sk-...", anthropic_key="sk-ant-...")
    result = g.detect("subtle attack")
"""

from gauntlet.detector import Gauntlet, detect
from gauntlet.models import DetectionResult, LayerResult

__version__ = "0.1.0"
__all__ = ["Gauntlet", "detect", "DetectionResult", "LayerResult"]

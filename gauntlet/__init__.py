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

import logging

from gauntlet.detector import Gauntlet, detect
from gauntlet._logging import setup_logging
from gauntlet.models import DetectionResult, LayerResult

# Library best practice: NullHandler so apps without logging config stay silent
logging.getLogger("gauntlet").addHandler(logging.NullHandler())

__version__ = "0.2.0"
__all__ = ["Gauntlet", "detect", "DetectionResult", "LayerResult", "setup_logging"]

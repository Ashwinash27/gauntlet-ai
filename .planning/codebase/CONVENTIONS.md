# Coding Conventions

**Analysis Date:** 2026-02-18

## Naming Patterns

**Files:**
- Module names use `snake_case`: `detector.py`, `embeddings.py`, `config.py`
- Test files use prefix pattern: `test_gauntlet_<module>.py`
- Layer modules grouped under `layers/` directory

**Functions:**
- Private/internal functions prefixed with underscore: `_get_embeddings_detector()`, `_cosine_similarity()`, `_parse_toml()`
- Public functions use `snake_case`: `detect()`, `load_config()`, `get_config_value()`
- Property decorators for computed attributes: `@property available_layers()`

**Variables:**
- Local variables use `snake_case`: `layer_results`, `run_layers`, `detection_threshold`
- Private instance variables prefixed with underscore: `self._embeddings`, `self._openai_key`, `self._rules`
- Constants in `UPPER_CASE`: `_DEFAULT_EMBEDDINGS_PATH`, `_CONFIG_FILE`, `CONFUSABLES`
- Dataclass fields use `snake_case`: `is_injection`, `confidence`, `attack_type`

**Types:**
- Pydantic models use `PascalCase`: `DetectionResult`, `LayerResult`, `SimilarityMatch`
- Type hints use union syntax: `str | None` (not `Optional[str]`)
- Custom exception classes use `PascalCase`: `GauntletError`, `ConfigError`, `DetectionError`

## Code Style

**Formatting:**
- Black formatter with line-length = 100 characters (configured in `pyproject.toml`)
- Target Python 3.11+
- Run: `black .` to format entire codebase

**Linting:**
- No `.eslintrc` or `.flake8` found; relies on Black for formatting
- Implicit linting through type hints and Pydantic validation

## Import Organization

**Order:**
1. Standard library imports: `import os`, `from pathlib import Path`, `import time`
2. Third-party imports: `from pydantic import BaseModel`, `import numpy as np`
3. Local imports: `from gauntlet.models import DetectionResult`
4. Type imports: `from typing import Pattern` (for type hints)

**Path Aliases:**
- No path aliases (no jsconfig/tsconfig equivalent) - uses relative imports from package root
- Imports always use full module path: `from gauntlet.detector import Gauntlet`

**Lazy Imports:**
- Heavy dependencies (openai, numpy, anthropic) imported inside functions/methods, not at module level
- Example in `gauntlet/detector.py`: Layer 2/3 detectors lazy-initialized in `_get_embeddings_detector()` and `_get_llm_detector()`
- Purpose: Avoid ImportError when optional dependencies aren't installed

## Error Handling

**Patterns:**
- Custom exception hierarchy rooted in `GauntletError` (see `gauntlet/exceptions.py`)
- Try/except blocks catch specific exceptions, not bare `except:`
- Fail-open strategy: Layers return `LayerResult` with `error` field instead of raising
- All tools/integrations wrap external calls in try/except to prevent cascade failures

**Example pattern:**
```python
try:
    import numpy as np
    from openai import OpenAI
except ImportError:
    raise ImportError(
        "Layer 2 requires openai and numpy. "
        "Install with: pip install gauntlet-ai[embeddings]"
    )
```

## Logging

**Framework:** Python's built-in `logging` module

**Patterns:**
- Each module creates logger: `logger = logging.getLogger(__name__)`
- Used sparingly for warnings and debug info: `logger.warning()`, `logger.debug()`
- Example in `gauntlet/detector.py`: `logger.warning("Failed to initialize Layer 2: %s", type(e).__name__)`
- No sensitive data logged (e.g., config keys are masked when displayed)

## Comments

**When to Comment:**
- Explain "why" not "what" - code should be self-documenting
- Unicode homoglyph mappings in `gauntlet/layers/rules.py` have detailed comments explaining attack vectors
- Security constraints documented prominently: "Raw user text is NEVER echoed directly to Claude"

**JSDoc/TSDoc:**
- No JSDoc style (Python project)
- Uses docstrings for all public functions, classes, and modules
- Docstring format: Google-style (see below)

**Docstring Format:**
All docstrings follow Google-style format with sections:
- One-line summary
- Extended description (if needed)
- Args: Parameter documentation with types
- Returns: Return value documentation
- Raises: Documented exceptions
- Examples: (for public APIs)

Example from `gauntlet/detector.py`:
```python
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
```

## Function Design

**Size:**
- Functions are focused and single-purpose
- Private methods extract logic to avoid large functions
- Example: `_build_result()` inner function in `detect()` method keeps logic DRY

**Parameters:**
- Type hints on all parameters (no untyped functions)
- Default arguments used for configuration: `embedding_threshold: float = 0.55`
- `**kwargs` used for optional pass-through: `detect(text: str, **kwargs) -> DetectionResult`

**Return Values:**
- Always return typed objects (Pydantic models or dataclasses)
- Never return `None` for errors - use `LayerResult.error` field
- Fail-open approach: Return result with error field rather than raising

**Example pattern from `gauntlet/models.py`:**
```python
class LayerResult(BaseModel):
    """Result from a single detection layer."""
    is_injection: bool
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    attack_type: str | None = None
    error: str | None = None  # Layer failed but returned False (fail-open)
```

## Module Design

**Exports:**
- Each module has explicit `__all__` listing public exports
- Example from `gauntlet/config.py`:
```python
__all__ = [
    "load_config",
    "get_config_value",
    "set_config_value",
    "list_config",
    "get_openai_key",
    "get_anthropic_key",
]
```

**Barrel Files:**
- Main `gauntlet/__init__.py` re-exports public API:
```python
from gauntlet.detector import Gauntlet, detect
from gauntlet.models import DetectionResult, LayerResult

__all__ = ["Gauntlet", "detect", "DetectionResult", "LayerResult"]
```

## Class Design

**Initialization:**
- Private attributes use underscore prefix
- Constructor resolves configuration with fallback chain:
  1. Constructor arguments
  2. Config file
  3. Environment variables
  4. Graceful degradation

Example from `gauntlet/detector.py`:
```python
def __init__(self, openai_key: str | None = None, ...):
    self._openai_key = openai_key or get_openai_key()
    self._embeddings = None  # Lazy-init
```

**Properties:**
- Use `@property` decorator for read-only computed attributes
- Example: `available_layers` property in `Gauntlet` class checks import availability

---

*Convention analysis: 2026-02-18*

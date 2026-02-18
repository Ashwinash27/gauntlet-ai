# Codebase Structure

**Analysis Date:** 2026-02-18

## Directory Layout

```
ArgusAI/
├── gauntlet/                    # Main package (installable as gauntlet-ai on PyPI)
│   ├── __init__.py              # Public API exports: Gauntlet, detect, DetectionResult, LayerResult
│   ├── detector.py              # Core orchestrator class and detect() function
│   ├── models.py                # Pydantic models: DetectionResult, LayerResult
│   ├── config.py                # Configuration management (~/.gauntlet/config.toml)
│   ├── exceptions.py            # Custom exceptions: GauntletError, ConfigError, DetectionError
│   ├── cli.py                   # Typer CLI: detect, scan, config commands
│   ├── mcp_server.py            # MCP server for Claude Code integration
│   ├── layers/                  # Detection layer implementations
│   │   ├── __init__.py          # Empty (package marker)
│   │   ├── rules.py             # Layer 1: Regex-based detection
│   │   ├── embeddings.py        # Layer 2: Semantic similarity detection
│   │   └── llm_judge.py         # Layer 3: LLM-based detection
│   └── data/                    # Pre-computed detection data
│       ├── embeddings.npz       # 500+ pre-computed attack embeddings (numpy binary)
│       └── metadata.json        # Attack pattern metadata (category, subcategory, label)
├── tests/                       # Test suite (pytest)
│   ├── __init__.py              # Package marker
│   ├── conftest.py              # Pytest fixtures and configuration
│   ├── test_gauntlet_rules.py      # Layer 1 tests (~850 lines, 30k test cases)
│   ├── test_gauntlet_embeddings.py # Layer 2 tests (mocking, similarity checks)
│   ├── test_gauntlet_llm_judge.py  # Layer 3 tests (LLM safety, sanitization)
│   ├── test_gauntlet_detector.py   # Orchestrator tests (cascade flow, error handling)
│   ├── test_gauntlet_models.py     # Pydantic model validation tests
│   └── test_gauntlet_config.py     # Config file management tests
├── pyproject.toml               # Build config: hatchling, optional deps, scripts
├── README.md                    # User documentation and usage guide
├── CLAUDE.md                    # Project instructions (this codebase)
├── LICENSE                      # MIT license
└── .gitignore                   # Standard Python gitignore
```

## Directory Purposes

**`gauntlet/`:**
- Purpose: Main package containing all detection logic and interfaces
- Contains: Detection layers, orchestrator, config management, CLI, MCP server
- Key files: `detector.py` (orchestrator), `models.py` (result types)

**`gauntlet/layers/`:**
- Purpose: Detection layer implementations (three separate detectors)
- Contains: `rules.py` (Layer 1 regex), `embeddings.py` (Layer 2 OpenAI), `llm_judge.py` (Layer 3 Claude)
- Design: Each layer is independent; all implement same interface (`.detect(text)` → `LayerResult`)

**`gauntlet/data/`:**
- Purpose: Pre-computed attack embeddings and metadata (shipped with package)
- Contains: `embeddings.npz` (binary numpy format), `metadata.json` (attack categories)
- Generated: Via external script (not in codebase; used for Gauntlet releases)
- Committed: Yes (to version control)

**`tests/`:**
- Purpose: Test suite with 330+ tests across 6 files
- Contains: Unit tests for each layer, integration tests for cascade, config tests
- Key pattern: Fixtures in `conftest.py`, per-layer test files, heavy mocking of external APIs
- Notable: `test_gauntlet_rules.py` is ~850 lines with parametrized test cases for 50+ patterns

## Key File Locations

**Entry Points:**

- `gauntlet/__init__.py`: Public API — exports `Gauntlet`, `detect()`, `DetectionResult`, `LayerResult`
- `gauntlet/cli.py`: CLI entry point — implements `detect`, `scan`, `config` commands via Typer
- `gauntlet/mcp_server.py`: MCP entry point — `serve()` function starts stdio server with two tools
- `gauntlet/detector.py`: Primary class — `Gauntlet` orchestrator and `detect()` convenience function

**Configuration:**

- `gauntlet/config.py`: Config file management at `~/.gauntlet/config.toml`
  - Functions: `get_config_value()`, `set_config_value()`, `load_config()`, `list_config()`
  - Key resolution: config file → env vars → None
  - Keys: `openai_key`, `anthropic_key`, `embedding_model`, `llm_model`, `llm_timeout`

**Core Logic:**

- `gauntlet/detector.py`: `Gauntlet` class with `detect()` method (orchestrator, 275 lines)
- `gauntlet/layers/rules.py`: `RulesDetector` class with 50+ regex patterns (400+ lines)
- `gauntlet/layers/embeddings.py`: `EmbeddingsDetector` class with OpenAI integration (250+ lines)
- `gauntlet/layers/llm_judge.py`: `LLMDetector` class with Claude integration (350+ lines)

**Data Models:**

- `gauntlet/models.py`: Pydantic models `DetectionResult` and `LayerResult` (84 lines)
- `gauntlet/exceptions.py`: Custom exceptions `GauntletError`, `ConfigError`, `DetectionError` (14 lines)

**Testing:**

- `tests/conftest.py`: Pytest fixtures (mocking helpers, test data)
- `tests/test_gauntlet_rules.py`: Layer 1 tests — pattern matching, unicode handling (~850 lines)
- `tests/test_gauntlet_embeddings.py`: Layer 2 tests — cosine similarity, threshold logic (~600 lines)
- `tests/test_gauntlet_llm_judge.py`: Layer 3 tests — sanitization, JSON parsing (~600 lines)
- `tests/test_gauntlet_detector.py`: Integration tests — cascade, error handling (~650 lines)
- `tests/test_gauntlet_models.py`: Pydantic validation tests (~450 lines)
- `tests/test_gauntlet_config.py`: Config file tests (~600 lines)

## Naming Conventions

**Files:**

- Python modules: `lowercase_with_underscores.py` (e.g., `embeddings.py`, `llm_judge.py`)
- Test files: `test_gauntlet_<module>.py` (e.g., `test_gauntlet_rules.py`)
- Data files: `lowercase_with_underscores.<ext>` (e.g., `embeddings.npz`, `metadata.json`)
- Package directories: `lowercase` (e.g., `gauntlet`, `layers`, `tests`)

**Directories:**

- Package: `lowercase` (e.g., `gauntlet`, `layers`)
- Test suite: `tests` (plural)
- Data: `data` (singular)

**Python code:**

- Classes: `PascalCase` (e.g., `Gauntlet`, `RulesDetector`, `EmbeddingsDetector`, `LLMDetector`, `DetectionResult`, `LayerResult`)
- Functions: `snake_case` (e.g., `detect()`, `get_openai_key()`, `normalize_unicode()`)
- Constants: `UPPER_CASE` (e.g., `CONFUSABLES`, `ATTACK_CATEGORIES`, `SUSPICIOUS_KEYWORDS`)
- Private methods: `_snake_case` (e.g., `_get_embeddings_detector()`, `_parse_toml()`)

**Pydantic models:**

- All use `BaseModel`
- All fields have type hints and Field descriptions
- Numeric fields have validators (e.g., `ge=0.0, le=1.0` for confidence)

## Where to Add New Code

**New detection pattern (regex):**
- Location: Add to `gauntlet/layers/rules.py` in the pattern definition section
- Test: Add test case(s) to `tests/test_gauntlet_rules.py`
- Pattern: Use `@dataclass` for pattern metadata, re.compile() with flags

**New detection layer (beyond 3):**
- Location: Create `gauntlet/layers/new_layer.py` with detector class implementing `.detect(text) -> LayerResult`
- Integration: Modify `Gauntlet` class in `gauntlet/detector.py` to initialize and call new layer
- Config: Add config keys to `gauntlet/config.py` `_KEY_MAP`
- CLI: Update `gauntlet/cli.py` to expose new layer options
- Test: Create `tests/test_gauntlet_new_layer.py` with comprehensive test cases

**New CLI command:**
- Location: Add function to `gauntlet/cli.py` decorated with `@app.command()`
- Pattern: Use Typer for argument parsing, Rich for output formatting
- Test: Add integration tests if complex

**New MCP tool:**
- Location: Add to `@server.list_tools()` and `@server.call_tool()` in `gauntlet/mcp_server.py`
- Pattern: Tools return `list[TextContent]` as JSON
- Test: Manual testing via Claude Code

**New configuration option:**
- Location: Add key to `_KEY_MAP` in `gauntlet/config.py`
- Pattern: Key name maps to environment variable name
- Usage: Accessible via `get_config_value(key)`, `set_config_value(key, value)`

## Special Directories

**`gauntlet/data/`:**
- Purpose: Pre-computed embeddings and metadata
- Generated: External script (not in this repo)
- Committed: Yes
- Contents:
  - `embeddings.npz`: Binary numpy format with 500+ attack vector embeddings (114 KB)
  - `metadata.json`: Attack pattern metadata with category, subcategory, label per index (2.7 KB)

**`.planning/codebase/`:**
- Purpose: GSD (Git Strategy Documents) directory for architecture/codebase analysis
- Generated: By GSD mapping tools
- Committed: Typically yes
- Contains: `.md` documents like `ARCHITECTURE.md`, `STRUCTURE.md`, `CONVENTIONS.md`, etc.

**`tests/__pycache__/`:**
- Purpose: Python bytecode cache
- Generated: Automatically by pytest
- Committed: No (in .gitignore)

## Import Patterns

**From gauntlet package (public API):**
```python
from gauntlet import Gauntlet, detect, DetectionResult, LayerResult
```

**From internal modules (private/testing):**
```python
from gauntlet.detector import Gauntlet, detect
from gauntlet.models import DetectionResult, LayerResult
from gauntlet.layers.rules import RulesDetector
from gauntlet.config import get_openai_key, load_config
```

**Lazy imports (inside functions/methods only):**
```python
# In __init__ or methods - not module level
from openai import OpenAI
from anthropic import Anthropic
import numpy as np
```

---

*Structure analysis: 2026-02-18*

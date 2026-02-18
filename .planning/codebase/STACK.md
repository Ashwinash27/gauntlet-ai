# Technology Stack

**Analysis Date:** 2026-02-18

## Languages

**Primary:**
- Python 3.11+ - Core library and all detection layers

## Runtime

**Environment:**
- Python 3.11, 3.12 (specified in `pyproject.toml`)

**Package Manager:**
- pip (via PyPI: `gauntlet-ai`)
- Lockfile: `pyproject.toml` (PEP 517/518 build system)

## Frameworks

**Core:**
- Pydantic 2.0.0+ - Data validation and serialization for all result models (`DetectionResult`, `LayerResult`)
  - Location: `gauntlet/models.py`

**Detection Layers:**
- Layer 1 - Standard library only (regex, unicodedata) - zero external deps
- Layer 2 - OpenAI 1.12.0+ - Text embeddings API
  - Optional dependency: `pip install gauntlet-ai[embeddings]`
  - Location: `gauntlet/layers/embeddings.py`
- Layer 3 - Anthropic 0.18.0+ - Claude LLM for semantic analysis
  - Optional dependency: `pip install gauntlet-ai[llm]`
  - Location: `gauntlet/layers/llm_judge.py`

**CLI:**
- Typer 0.9.0+ - CLI argument parsing
- Rich 13.0.0+ - Terminal output formatting
- Optional dependency: `pip install gauntlet-ai[cli]`
- Location: `gauntlet/cli.py`

**MCP (Model Context Protocol):**
- MCP 0.9.0+ - Server for Claude Code integration
- Optional dependency: `pip install gauntlet-ai[mcp]`
- Location: `gauntlet/mcp_server.py`

**Build/Dev:**
- hatchling - Build backend
- pytest 7.0.0+ - Test runner
- pytest-asyncio 0.21.0+ - Async test support
- pytest-cov 4.0.0+ - Coverage reporting
- black 23.0.0+ - Code formatter (line-length: 100)

## Key Dependencies

**Critical:**
- Pydantic 2.0.0+ - Core data structures for all detection results
  - Without it: Results cannot be serialized to JSON/dict

**Conditional (Feature Flags):**
- numpy 1.24.0+ (embeddings layer only) - Cosine similarity computation
- openai 1.12.0+ (embeddings layer only) - OpenAI embedding API client
- anthropic 0.18.0+ (LLM layer only) - Anthropic Claude client
- typer[all] 0.9.0+ (CLI only) - CLI framework with shell completion
- rich 13.0.0+ (CLI only) - Terminal output with colors/tables
- mcp 0.9.0+ (MCP server only) - Model Context Protocol server framework

## Configuration

**Environment:**
- `.env` file (NOT committed) - stores API keys for development
- `.env.example` (committed) - template showing required variables:
  - `OPENAI_API_KEY` - Optional, enables Layer 2
  - `ANTHROPIC_API_KEY` - Optional, enables Layer 3
  - `SUPABASE_URL` - Mentioned in example but not used in current codebase
  - `SUPABASE_KEY` - Mentioned in example but not used in current codebase
  - `GITHUB_TOKEN` - Mentioned in example but not used in current codebase
  - `ENVIRONMENT` - Optional, for dev/prod distinction

**Build:**
- `pyproject.toml` (lines 1-66) - Single source of truth for:
  - Package metadata (name: `gauntlet-ai`, version: 0.1.1)
  - Dependencies (base: Pydantic; optional: OpenAI, Anthropic, Typer, Rich, MCP)
  - Optional feature groups: `[embeddings]`, `[llm]`, `[cli]`, `[mcp]`, `[all]`, `[dev]`
  - Tool config: pytest, black, hatch build settings
  - Package entry point: `gauntlet` CLI command

**Config File:**
- `~/.gauntlet/config.toml` - User config directory (created at runtime)
  - Location: `gauntlet/config.py` manages this
  - Stores: API keys (`openai_key`, `anthropic_key`)
  - Stores: Model config (`embedding_model`, `embedding_threshold`, `llm_model`, `llm_timeout`)
  - Permissions: `0o600` (owner read/write only)
  - Format: Flat TOML with custom minimal parser (no tomli dependency)

## Platform Requirements

**Development:**
- Python 3.11 or 3.12
- pip or similar package manager
- Optional: venv for isolation
- Optional: git for version control

**Production:**
- Python 3.11 or 3.12
- Network access to OpenAI API (if using Layer 2)
- Network access to Anthropic API (if using Layer 3)
- Read access to `~/.gauntlet/config.toml` or environment variables for API keys

**Data Files:**
- `gauntlet/data/embeddings.npz` (114 KB) - Pre-computed attack embedding vectors
  - Shipped with wheel distribution
  - Used by Layer 2 for semantic similarity
- `gauntlet/data/metadata.json` (2.7 KB) - Attack pattern metadata and categories
  - Shipped with wheel distribution
  - Describes embedding indices and attack types

---

*Stack analysis: 2026-02-18*

# Architecture

**Analysis Date:** 2026-02-18

## Pattern Overview

**Overall:** Layered cascade with fail-open semantics.

Gauntlet implements a three-layer detection cascade where each layer is progressively more powerful and expensive. The cascade is designed to stop at the first detection, making the most common attacks fail fast in the cheapest layer. If any layer encounters an error, it fails open (allows request through with a warning) and passes control to the next layer.

**Key Characteristics:**
- **Cascade pattern:** Layers 1 → 2 → 3, each adds sophistication and cost
- **Lazy initialization:** Layers 2 and 3 only initialize if API keys are available and dependencies exist
- **Fail-open:** Errors don't block requests; they log and continue
- **Zero-trust for input:** All user input treated as potentially malicious; never echoed directly to LLMs
- **Configuration resolution chain:** Constructor args → config file (`~/.gauntlet/config.toml`) → environment variables → defaults

## Layers

**Layer 1: Rules (regex pattern matching):**
- Purpose: Fast, synchronous pattern-based detection of common injection attacks
- Location: `gauntlet/layers/rules.py`
- Contains: 50+ regex patterns across 9 attack categories, Unicode normalization for homoglyph attacks
- Depends on: Python standard library only (no external deps)
- Used by: `Gauntlet.detect()` - always runs first
- Cost: ~0.1ms, free
- Returns: `LayerResult` with confidence 0.0-1.0, attack_type string, pattern details

**Layer 2: Embeddings (semantic similarity):**
- Purpose: Semantic-based detection using pre-computed attack embeddings and local cosine similarity
- Location: `gauntlet/layers/embeddings.py`
- Contains: OpenAI embedding client, pre-loaded attack embeddings (.npz format), metadata lookup, cosine similarity matching
- Depends on: OpenAI API key, numpy, openai package
- Used by: `Gauntlet.detect()` after Layer 1 (only if Layer 1 didn't detect and openai_key is available)
- Cost: ~$0.00002 per check, ~700ms latency
- Data files: `gauntlet/data/embeddings.npz` (500+ pre-computed attack embeddings), `gauntlet/data/metadata.json` (attack metadata)
- Returns: `LayerResult` with confidence (clamped 0.0-1.0), attack category from metadata, similarity details

**Layer 3: LLM Judge (Claude analysis):**
- Purpose: Sophisticated reasoning-based detection for attacks that bypass Layers 1 and 2
- Location: `gauntlet/layers/llm_judge.py`
- Contains: Hardened system prompt, sanitization logic (alphanumeric + spaces only), Claude client, suspicious keyword detection
- Depends on: Anthropic API key, anthropic package
- Used by: `Gauntlet.detect()` after Layer 2 (only if Layer 2 didn't detect and anthropic_key is available)
- Cost: ~$0.0003 per check, ~1s latency
- Critical: Never echoes raw user text to Claude; only sends sanitized snippets and metadata
- Returns: `LayerResult` with confidence, attack_type, and reasoning details

## Data Flow

**Detect Request Flow:**

1. User calls `Gauntlet.detect(text)` or convenience function `detect(text)`
2. Input validation: empty/whitespace → return DetectionResult(is_injection=False)
3. Start timing with `perf_counter()`
4. **Layer 1 execution:** `RulesDetector.detect(text)` → returns `LayerResult`
   - If injection detected → return `DetectionResult(is_injection=True, detected_by_layer=1, ...)`
   - Otherwise continue
5. **Layer 2 execution** (if requested and openai_key available):
   - Lazy-init `EmbeddingsDetector` via `_get_embeddings_detector()`
   - Call `EmbeddingsDetector.detect(text)` → returns `LayerResult`
   - If injection detected → return `DetectionResult(is_injection=True, detected_by_layer=2, ...)`
   - Otherwise continue
6. **Layer 3 execution** (if requested and anthropic_key available):
   - Lazy-init `LLMDetector` via `_get_llm_detector()`
   - Call `LLMDetector.detect(text)` → returns `LayerResult`
   - If injection detected → return `DetectionResult(is_injection=True, detected_by_layer=3, ...)`
   - Otherwise continue
7. **No detection:** Return `DetectionResult(is_injection=False, detected_by_layer=None, ...)`
8. All `LayerResult` objects collected in `layer_results` list
9. Total latency calculated and included in response

**Error Handling in Data Flow:**

- Each layer catches exceptions and returns `LayerResult(is_injection=False, error="message")`
- Errors collected in `DetectionResult.errors` list for observability
- Layer skipped if dependencies missing or key not available → added to `layers_skipped` list
- Fail-open: errors never prevent result completion

**State Management:**

- No global state; each `Gauntlet` instance is independent
- Lazy initialization of expensive layers stored in `_embeddings` and `_llm` attributes
- `RulesDetector` instantiated eagerly (no deps)
- Configuration resolved once during `__init__` via `get_openai_key()` and `get_anthropic_key()`

## Key Abstractions

**DetectionResult:**
- Purpose: Complete result envelope for a single detection request
- Location: `gauntlet/models.py`
- Pattern: Pydantic BaseModel with type validation
- Fields: `is_injection` (bool), `confidence` (0.0-1.0), `attack_type` (str|None), `detected_by_layer` (1|2|3|None), `layer_results` (list[LayerResult]), `total_latency_ms`, `errors`, `layers_skipped`

**LayerResult:**
- Purpose: Result from a single detection layer
- Location: `gauntlet/models.py`
- Pattern: Pydantic BaseModel with type validation
- Fields: `is_injection` (bool), `confidence` (0.0-1.0), `attack_type` (str|None), `layer` (1|2|3), `latency_ms`, `details` (dict), `error` (str|None)

**Gauntlet (orchestrator):**
- Purpose: Main detection orchestrator; coordinates the three-layer cascade
- Location: `gauntlet/detector.py`
- Pattern: Class with configuration in `__init__`, detection in `detect(text)` method
- Responsibilities: Layer initialization, cascade control, error handling, result aggregation

**RulesDetector:**
- Purpose: Regex-based pattern detection
- Location: `gauntlet/layers/rules.py`
- Pattern: Class with pre-compiled regex patterns, Unicode normalization utilities
- Responsibilities: Pattern matching, confidence scoring (0.0-1.0), attack type classification

**EmbeddingsDetector:**
- Purpose: Semantic similarity detection via pre-computed embeddings
- Location: `gauntlet/layers/embeddings.py`
- Pattern: Class with lazy OpenAI client initialization
- Responsibilities: Text embedding generation, local cosine similarity computation, threshold matching

**LLMDetector:**
- Purpose: Reasoning-based detection via Claude
- Location: `gauntlet/layers/llm_judge.py`
- Pattern: Class with hardened system prompt, input sanitization
- Responsibilities: Text sanitization, Claude API calls, JSON parsing, confidence extraction

## Entry Points

**Python API (Library):**
- Location: `gauntlet/__init__.py` exports `Gauntlet`, `detect`, `DetectionResult`, `LayerResult`
- Triggers: Direct import and function call
- Responsibilities:
  - `detect(text, **kwargs)` → convenience function, creates Gauntlet and calls detect()
  - `Gauntlet(openai_key=..., anthropic_key=...).detect(text, layers=[1,2,3])` → full control

**CLI:**
- Location: `gauntlet/cli.py`, entry point via `gauntlet` command (defined in `pyproject.toml`)
- Main function: `gauntlet.cli:main` (lazy-loaded via Typer)
- Commands:
  - `gauntlet detect "text"` → Layer 1 only by default
  - `gauntlet detect --all` → All available layers
  - `gauntlet detect --layers 1,2` → Specific layers
  - `gauntlet detect --file input.txt` → From file
  - `gauntlet scan ./dir/` → Scan directory of files
  - `gauntlet config set openai_key sk-...` → Config management
  - `gauntlet config list` → List current config
- Triggers: Shell command invocation
- Responsibilities: Argument parsing, file I/O, rich-formatted output, exit codes

**MCP Server:**
- Location: `gauntlet/mcp_server.py`, entry point via `gauntlet mcp-serve`
- Server: Provides two tools to Claude Code:
  - `check_prompt(text)` → Run detection cascade
  - `scan_file(path)` → Read file and check
- Triggers: MCP protocol from Claude Code/Claude Desktop
- Responsibilities: Tool definition, MCP message handling, JSON serialization

## Error Handling

**Strategy:** Fail-open with detailed error tracking. No exceptions propagate to caller; all errors captured in `DetectionResult.errors` and `LayerResult.error`.

**Patterns:**

1. **Layer detection errors:** Caught inside `detect()` method, appended to `errors` list with layer name prefix
   ```python
   try:
       l1_result = self._rules.detect(text)
   except Exception as e:
       layer_results.append(LayerResult(..., error=str(e)))
       errors.append(f"Layer 1 (rules): {e}")
   ```

2. **Lazy initialization failures:** Caught in `_get_embeddings_detector()` and `_get_llm_detector()`
   - Missing dependencies (ImportError) → logged as debug, layer skipped
   - API key not available → layer skipped
   - Initialization exceptions → logged as warning, layer skipped

3. **API failures:** Each layer's API client wrapped in try-except
   - OpenAI API timeout/error in Layer 2 → LayerResult with error, continue to Layer 3
   - Anthropic API timeout/error in Layer 3 → LayerResult with error, return

4. **Invalid layer specification:** `detect(text, layers=[4])` → ValueError raised to caller (explicit error)

## Cross-Cutting Concerns

**Logging:**
- Framework: Python `logging` module
- Logger: `logging.getLogger(__name__)` per module
- Level usage:
  - DEBUG: Lazy init skips (missing deps), vendor API unavailability
  - WARNING: Layer init failures, API errors that fail-open
  - INFO: Not used
  - ERROR: Not used (fail-open pattern prevents errors bubbling)

**Validation:**
- Pydantic models validate DetectionResult and LayerResult fields
- Confidence values clamped to [0.0, 1.0] before assignment to LayerResult
- Layer numbers validated in `detect(text, layers=...)` → ValueError if not 1, 2, or 3
- Text input validated: empty/whitespace → return clean result

**Authentication:**
- API keys resolved via `config.py` functions: `get_openai_key()`, `get_anthropic_key()`
- Resolution chain: constructor arg → config file → env var → None
- Config file at `~/.gauntlet/config.toml` with 0o600 permissions (owner read/write only)
- Environment variables: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`

**Security (input handling):**
- Layer 1: Regex patterns match against raw text (safe)
- Layer 2: Raw text sent to OpenAI (OpenAI is trusted vendor)
- Layer 3: Raw text is **sanitized before Claude** (CRITICAL)
  - Only alphanumeric characters and spaces preserved
  - Metadata (keyword counts, length, patterns) sent instead of raw payload
  - LLMDetector system prompt hardened with security rules

---

*Architecture analysis: 2026-02-18*

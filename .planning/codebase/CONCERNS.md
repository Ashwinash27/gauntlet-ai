# Codebase Concerns

**Analysis Date:** 2026-02-18

## Tech Debt

**Layer 3 LLM Judge: Conflicting confidence signals**
- Issue: The LLM judge applies its own `confidence_threshold` (default 0.70) after Claude responds, but also stores `raw_is_injection` in details. This means Claude may say "is_injection: true" with confidence 0.65, but the layer will return `is_injection: false` because it didn't meet the threshold.
- Files: `gauntlet/layers/llm_judge.py` (lines 281-288)
- Impact: Confusing semantics—the "confidence" field in `LayerResult` may not reflect the actual verdict. Callers can't distinguish between "Claude said no" vs. "Claude said maybe but below threshold."
- Fix approach: Either (1) remove the threshold check and let Claude's confidence speak, or (2) rename the logic to be explicit: store both `raw_is_injection` and `threshold_is_injection` in the result.

**Rules Layer: 852-line monolith**
- Issue: `gauntlet/layers/rules.py` is a single 852-line file with ~50 regex patterns defined inline. Adding or modifying patterns requires scrolling through dense pattern definitions.
- Files: `gauntlet/layers/rules.py`
- Impact: Maintenance burden when adding attack categories or refining existing patterns. Hard to track pattern evolution or audit rules systematically.
- Fix approach: Extract pattern definitions into a structured data file (YAML or JSON) or separate modules by attack category (e.g., `patterns/instruction_override.py`, `patterns/jailbreak.py`). Keep the `detect()` logic in rules.py.

**LLM Judge: Fragile JSON parsing**
- Issue: `_parse_response()` uses a simple regex `r"\{[^{}]*\}"` to extract JSON. This fails on nested objects or if the LLM includes other braces in text. Falls back to "parse error" but doesn't retry or provide diagnostic info.
- Files: `gauntlet/layers/llm_judge.py` (lines 210-249)
- Impact: Production requests with malformed JSON responses silently degrade to `confidence: 0.0`. Users see no detection but no warning that Claude failed to respond properly.
- Fix approach: Use a proper JSON parser with error recovery. Log the full response text when JSON parsing fails. Consider adding a diagnostic mode that returns the raw response.

**Config TOML parser: No nested structure support**
- Issue: `_parse_toml()` in `gauntlet/config.py` (lines 31-51) only handles flat `key = "value"` pairs. No section headers, arrays, or tables. This is fine for current use but limits future config extensions.
- Files: `gauntlet/config.py` (lines 31-51)
- Impact: Can't add structured config like per-layer settings without breaking the parser or moving to a real TOML library.
- Fix approach: Replace with `tomllib` (Python 3.11+) or keep minimal parser but document its scope clearly in the docstring.

**Embeddings Layer: Pre-computed embeddings are immutable**
- Issue: The `embeddings.npz` and `metadata.json` shipped with the package are static. Updating attack patterns requires rebuilding the wheel. No mechanism to load custom embeddings at runtime.
- Files: `gauntlet/layers/embeddings.py` (lines 79-97), `gauntlet/data/embeddings.npz`
- Impact: Can't quickly add new attack vectors or A/B test embeddings without a new release. Users can't provide domain-specific attack examples.
- Fix approach: Add optional `embeddings_dir` config param so users can provide updated `.npz` and `metadata.json` files at startup. Keep the defaults for zero-config use.

## Known Bugs

**Layer 3: Model name is hardcoded in detector, not configurable**
- Issue: `detector.py` passes `model="claude-3-haiku-20240307"` (hardcoded in line 46), but this is outdated. Anthropic has moved to `claude-3-5-haiku`. Users can't easily switch to newer models.
- Files: `gauntlet/detector.py` (line 46), `gauntlet/layers/llm_judge.py` (line 117)
- Impact: Users are stuck on an older model, missing performance/cost improvements. No way to upgrade without editing code.
- Fix approach: Make the default model name configurable in `gauntlet/config.py`, similar to `llm_timeout` and `embedding_threshold`. Allow env var `GAUNTLET_LLM_MODEL` and config file override.

**Cascading detection: Doesn't detect if earlier layers timeout but later layers would**
- Issue: If Layer 2 times out (OpenAI slow), it returns error but `is_injection=False`, so Layer 3 never runs. The error is logged but not surfaced in a way that makes it clear detection was incomplete.
- Files: `gauntlet/detector.py` (lines 206-224)
- Impact: A genuinely dangerous injection might pass Layer 2 (timeout) and never reach Layer 3 due to cascade stopping logic.
- Fix approach: Distinguish between "layer checked and passed" vs. "layer failed to check." Only stop cascade on positive detection, not on errors. Track skipped layers separately (already done in `layers_skipped`, but the cascade logic doesn't use it).

## Security Considerations

**Sanitization in Layer 3 is lossy**
- Risk: `_sanitize_text()` removes all non-alphanumeric characters except spaces (lines 145-151). This means a prompt like `<?xml><prompt>eval(...)`, when sanitized to `xml prompt eval`, loses the critical XML structure and encoding hints that indicate an attack.
- Files: `gauntlet/layers/llm_judge.py` (lines 145-151)
- Current mitigation: The `_extract_characteristics()` method does detect XML tags (`has_xml_tags`) before sanitization, so some structural signals are preserved via metadata.
- Recommendations:
  - Log what was stripped (for debugging/validation)
  - Consider a "tokens" sanitization mode that preserves delimiters as token boundaries (`<|>`, `[|]`) so structure is visible to Claude
  - Test whether lossy sanitization misses real attacks that would be obvious if structure were preserved

**No rate limiting on OpenAI/Anthropic API calls**
- Risk: A user with the library could accidentally or maliciously call `detect()` in a tight loop, burning API budget fast ($0.00002/check for embeddings * 1000 = $0.02 per second).
- Files: `gauntlet/layers/embeddings.py` (lines 99-112), `gauntlet/layers/llm_judge.py` (lines 268-274)
- Current mitigation: None.
- Recommendations:
  - Add optional client-side rate limiting (e.g., max checks per second)
  - Document best practices for production (e.g., batch processing, caching)
  - Consider adding a `cache` layer that memoizes results for identical inputs (already in detector, but no TTL to prevent unbounded memory)

**Layer 1 Unicode normalization: Cyrillic character handling**
- Risk: The Cyrillic lookalike mappings in `CONFUSABLES` (lines 38-50) may be incomplete. For example, `ю` (U+044E) normalizes to `y` but isn't explicitly in the map; it relies on NFKC normalization. If NFKC behavior changes in future Python versions, the normalization breaks.
- Files: `gauntlet/layers/rules.py` (lines 37-84, 102-104)
- Current mitigation: Tests include Cyrillic cases, so regressions would be caught.
- Recommendations:
  - Document the explicit assumption that NFKC handles unmapped Unicode
  - Add a test for `ю` specifically to ensure it normalizes as expected
  - Consider moving confusables to a data file with version pinning

## Performance Bottlenecks

**Layer 2: Embedding API calls are synchronous and block**
- Problem: Each call to Layer 2 blocks for ~700ms waiting for OpenAI (per README). If the text is large (10,000 chars), the embedding generation is slow.
- Files: `gauntlet/layers/embeddings.py` (lines 99-112, 189)
- Cause: The detector is synchronous-only (by design, per CLAUDE.md). Each layer waits for the previous one. No batching or async support.
- Improvement path: For the library API, this is acceptable (synchronous, simple). For high-throughput applications (e.g., MCP server handling multiple requests), consider adding an async variant or batching layer.

**Layer 1: Regex compilation happens at instantiation, not module load**
- Problem: Every time a `RulesDetector` is created, all ~50 regex patterns are re-compiled. If many detectors are created in a loop, this is wasteful.
- Files: `gauntlet/layers/rules.py` (lines 123-700 define patterns, lines 757-758 store them)
- Cause: Patterns are defined as module-level constants (`INJECTION_PATTERNS`), but they're re-assigned in `__init__`. This is harmless but suggests the `__init__` could be optimized away.
- Improvement path: Remove the `__init__` and store patterns at module level, or cache compiled regex globally. Negligible impact since detector creation is cheap (<1ms), but worth clarifying.

**MCP Server: No caching between requests**
- Problem: Each call to `check_prompt` or `scan_file` creates a new `Gauntlet` instance and re-initializes all layers. If the MCP server handles many requests, this is inefficient.
- Files: `gauntlet/mcp_server.py` (lines 34-35)
- Cause: The server creates a single `detector` globally, but lazy-initialization of layers happens per-request inside the detect loop.
- Improvement path: Pre-initialize layers at server startup so they're reused across requests.

## Fragile Areas

**Layer 3: Parsing LLM responses**
- Files: `gauntlet/layers/llm_judge.py` (lines 210-249)
- Why fragile: Claude's response is parsed with a simple regex. If Claude includes a JSON-like structure in the reasoning field (e.g., `{"example": "attack"}`), the regex might extract a nested brace and fail. The recovery path returns default values with zero confidence, which silently downgrades security.
- Safe modification: Add comprehensive tests for malformed responses (missing JSON, nested objects, non-ASCII in reasoning). Use a JSON parser that can extract the main object even if there are extra characters.
- Test coverage: Gaps in `test_gauntlet_llm_judge.py`—there are tests for timeout and API errors, but not for parsing edge cases (nested JSON, missing fields, non-string reasoning).

**Layer 2: Metadata lookup relies on index ordering**
- Files: `gauntlet/layers/embeddings.py` (lines 157-163)
- Why fragile: The metadata list (`patterns[index]`) must be in sync with the embeddings array row order. If the NPZ or metadata.json are regenerated out of sync, indices mismatch silently.
- Safe modification: Add a checksum or versioning field to metadata.json that matches the embeddings file. Validate on load.
- Test coverage: No tests for mismatched metadata; `test_gauntlet_embeddings.py` uses mock data.

**MCP Server: Path traversal protection is incomplete**
- Files: `gauntlet/mcp_server.py` (lines 81-98)
- Why fragile: The code checks that the path is within the current working directory and blocks hidden files, but doesn't handle symlinks. A symlink pointing outside cwd would bypass the check.
- Safe modification: Use `Path.resolve()` before checking, or use `pathlib.Path.is_relative_to()` (Python 3.12+).
- Test coverage: No tests for symlink attacks.

## Scaling Limits

**Embeddings database size is fixed**
- Current capacity: 112K embeddings.npz file with ~500 attack vectors (estimated from README)
- Limit: Adding more patterns requires rebuilding the wheel. At 500+ vectors, cosine similarity becomes slow (though still <1s).
- Scaling path: If attack library grows beyond 1000+ vectors, consider:
  - Hierarchical clustering to quickly filter similar vectors before full comparison
  - Separate embeddings files for different attack categories
  - Lazy loading of embeddings (only load categories relevant to deployment)

**Regex pattern count**
- Current capacity: ~50 patterns in Layer 1
- Limit: At 100+ patterns, regex compilation time and matching time become noticeable (though still <5ms).
- Scaling path: If attack rules grow significantly, consider moving to a trie-based pattern matcher or migrating to a DFA library.

**Config file at `~/.gauntlet/config.toml`**
- Current capacity: Flat key-value pairs (currently 6 keys)
- Limit: If per-layer settings are needed (e.g., different thresholds for different use cases), the flat structure breaks.
- Scaling path: Migrate to nested TOML or use environment variable prefixes (`GAUNTLET_LAYER2_THRESHOLD`, etc.).

## Dependencies at Risk

**Anthropic SDK: Model deprecation**
- Risk: `claude-3-haiku-20240307` (hardcoded in detector.py line 46) will eventually be deprecated. Gauntlet will stop working without a code update.
- Impact: Users stuck on old models, missing performance/cost improvements.
- Migration plan: Already identified in "Known Bugs" section—make model name configurable via config file and env var.

**OpenAI SDK: Embedding model changes**
- Risk: `text-embedding-3-small` (hardcoded in detector.py line 45) is relatively new. If OpenAI deprecates it, embeddings layer fails.
- Impact: Layer 2 stops working, cascade moves to Layer 3 (or fails if no Anthropic key).
- Migration plan: Same as Anthropic—make configurable.

**NumPy: Floating-point precision**
- Risk: The cosine similarity computation (line 141-152 in embeddings.py) can return values like `1.0000001` due to floating-point rounding. The code clamps to [0.0, 1.0], but this is brittle.
- Impact: Edge cases where similarity is exactly 1.0 might be clamped unpredictably across Python/NumPy versions.
- Migration plan: Always use `numpy.clip()` explicitly and add a test to verify the behavior is stable.

## Missing Critical Features

**No offline batch processing mode**
- Problem: Gauntlet detects one input at a time. For applications that process large logs or datasets, this means making N API calls (one per message). No built-in batching.
- Blocks: High-volume security audits, log analysis tools, batch validation pipelines.

**No distributed caching**
- Problem: Each application instance has its own in-memory cache (if any). No shared cache (Redis, etc.) to avoid duplicate detections across multiple processes.
- Blocks: Microservice deployments, multi-tenant systems.

**No telemetry or metrics export**
- Problem: No hooks to export detection metrics (counts, latencies, confidence scores) for monitoring or alerting.
- Blocks: Production monitoring, A/B testing Layer 2 vs. Layer 3, cost tracking.

**No fine-tuning or feedback loop**
- Problem: If a detection is wrong (false positive or false negative), there's no mechanism to retrain or adjust thresholds.
- Blocks: Improving accuracy over time, domain-specific tuning.

## Test Coverage Gaps

**Layer 3: LLM response parsing edge cases**
- What's not tested: Malformed JSON (nested braces, missing fields, extra characters), non-ASCII in reasoning, Unicode in category name.
- Files: `gauntlet/layers/llm_judge.py` (lines 210-249)
- Risk: Parser fails silently and returns default values (is_injection=False), potentially allowing attacks through.
- Priority: High

**Layer 2: Metadata mismatch**
- What's not tested: Embeddings and metadata files are out of sync (index mismatch, missing patterns).
- Files: `gauntlet/layers/embeddings.py` (lines 157-163)
- Risk: Silent metadata corruption when embeddings are updated.
- Priority: Medium

**MCP Server: Path traversal and symlinks**
- What's not tested: Symlink attacks, paths with `..` that escape cwd, hidden files.
- Files: `gauntlet/mcp_server.py` (lines 81-98)
- Risk: File access outside intended directory.
- Priority: High

**Detector: Cascade behavior on layer timeouts**
- What's not tested: Layer 2 times out (but Layer 3 would detect the attack). Verify that Layer 3 still runs or that the timeout is reported clearly.
- Files: `gauntlet/detector.py` (lines 206-244)
- Risk: Real attacks slip through when a layer times out.
- Priority: High

**Config: Invalid TOML syntax**
- What's not tested: Malformed TOML (unquoted strings, invalid characters in values).
- Files: `gauntlet/config.py` (lines 31-51)
- Risk: Config parsing silently ignores invalid lines instead of failing explicitly.
- Priority: Low

---

*Concerns audit: 2026-02-18*

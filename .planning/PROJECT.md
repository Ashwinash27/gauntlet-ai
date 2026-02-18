# Gauntlet AI

## What This Is

A prompt injection detection library for LLM applications, published on PyPI as `gauntlet-ai`. It runs a 3-layer detection cascade (regex patterns, embedding similarity, LLM judge) and is designed for developers integrating AI into their products who need to protect against prompt injection attacks. Currently at v0.1.1 with a working core — this milestone upgrades it to production-ready v0.2.0.

## Core Value

Accurate, fast prompt injection detection that developers can drop into any Python application with `pip install gauntlet-ai` and a single function call.

## Requirements

### Validated

- [x] 3-layer cascade detection (regex → embeddings → LLM judge) — existing
- [x] Layer 1: 51 regex patterns across 9 attack categories with Unicode normalization — existing
- [x] Layer 2: OpenAI embedding similarity against shipped attack vectors — existing
- [x] Layer 3: Claude LLM judge with hardened prompt and input sanitization — existing
- [x] CLI with detect, scan, config, and mcp-serve commands — existing
- [x] MCP server for Claude Code integration — existing
- [x] Pydantic result models (DetectionResult, LayerResult) — existing
- [x] Config management via ~/.gauntlet/config.toml with env var fallback — existing
- [x] 218 tests across 6 test files — existing
- [x] Published on PyPI as gauntlet-ai — existing
- [x] Fail-open error handling (errors don't block requests) — existing
- [x] Lazy initialization of optional layers — existing

### Active

- [ ] Real adversarial evaluation dataset (~4,500 samples: 3,500 malicious + 1,000 benign)
- [ ] Benchmark script measuring Precision/Recall/F1 across all 3 layer configs
- [ ] Expand attack embeddings from 20 placeholders to 500+ real OpenAI vectors
- [ ] FastAPI REST API with /detect and /health endpoints
- [ ] Structured JSON logging using Python stdlib (zero new deps)
- [ ] Dockerfile and docker-compose.yml for containerized deployment
- [ ] GitHub Actions CI (Python 3.11 + 3.12 matrix, pytest, black)
- [ ] Updated README with CI badge, Mermaid diagram, benchmark table, comparison table
- [ ] Version bump to 0.2.0 with new `api` extra in pyproject.toml

### Out of Scope

- Async API rewrite — library is synchronous by design, API wraps with asyncio.to_thread()
- structlog dependency — using Python stdlib logging with custom JSONFormatter instead
- Frontend dashboard — this is a library, not a product
- Rate limiting in API — left to the deployer
- Authentication in API — left to the deployer
- GPU-accelerated embeddings — overkill for this use case

## Context

- **GitHub**: Ashwinash27/gauntlet-ai
- **PyPI**: gauntlet-ai (v0.1.1)
- **Current state**: Core detection works well. Missing production-readiness: no eval dataset, only 20 placeholder embeddings, no REST API, no containerization, no CI.
- **Motivation**: Match resume claims and 2026 AI Engineer hiring expectations. Demonstrate end-to-end engineering: detection accuracy, API design, observability, deployment, CI/CD.
- **Codebase map**: .planning/codebase/ (7 documents, 1,366 lines)

## Constraints

- **Zero new core deps**: Only Pydantic remains as core dependency. Logging uses stdlib. FastAPI/uvicorn are optional extras.
- **Backward compatibility**: Existing `detect()` API and CLI must not break.
- **Python 3.11+**: Minimum supported version.
- **Sequential execution**: Tasks 1-8 done in order, commit after each.
- **Real embeddings**: Task 2 will call OpenAI API with real key to generate 500+ embeddings.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| stdlib logging over structlog | Zero new deps, same JSON output capability | -- Pending |
| create_app() factory pattern for API | Standard FastAPI pattern, testable with lifespan | -- Pending |
| asyncio.to_thread() for API | Keep core library synchronous, wrap at API boundary | -- Pending |
| Smart benchmark key detection | Run Layer 1 only if no keys, all 3 if keys set | -- Pending |
| 4,500 eval samples (3,500 malicious + 1,000 benign) | Large enough for meaningful metrics, includes public research sources | -- Pending |
| Separate core vs full benchmark reporting | Core set F1 is resume number, full set tests robustness | -- Pending |

---
*Last updated: 2026-02-18 after initialization*

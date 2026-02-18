# External Integrations

**Analysis Date:** 2026-02-18

## APIs & External Services

**Layer 2 - Text Embeddings (Optional):**
- OpenAI API - Text embedding service
  - SDK/Client: `openai>=1.12.0`
  - Auth: Environment variable `OPENAI_API_KEY` or config file
  - Endpoint: OpenAI embeddings API (`embeddings.create()`)
  - Model: `text-embedding-3-small` (configurable via `embedding_model` parameter)
  - Used in: `gauntlet/layers/embeddings.py` - generates embeddings for user input, compares to pre-computed attack embeddings
  - Cost: ~$0.00002 per check
  - Latency: ~700ms
  - Failure mode: Fails open (returns non-injection) with warning

**Layer 3 - LLM Judge (Optional):**
- Anthropic Claude API - LLM-based semantic analysis
  - SDK/Client: `anthropic>=0.18.0`
  - Auth: Environment variable `ANTHROPIC_API_KEY` or config file
  - Model: `claude-3-haiku-20240307` (configurable via `llm_model` parameter)
  - Used in: `gauntlet/layers/llm_judge.py` - analyzes sanitized text characteristics and metadata
  - Cost: ~$0.0003 per check
  - Latency: ~1s
  - Timeout: 3.0 seconds (configurable)
  - Failure mode: Fails open (returns non-injection) with warning
  - Security: Raw user text is NEVER sent to Claude - only sanitized alphanumeric snippet + extracted metadata

## Data Storage

**Databases:**
- Not used - Gauntlet is a stateless detection library

**File Storage:**
- Local filesystem only - No external cloud storage
- Pre-computed embeddings: `gauntlet/data/embeddings.npz` (shipped in wheel)
- Attack metadata: `gauntlet/data/metadata.json` (shipped in wheel)
- Config file: `~/.gauntlet/config.toml` (user-specific, created on first `set_config_value()`)

**Caching:**
- In-memory caching: Not currently implemented
- Each `detect()` call is stateless and independent
- No cross-request state

## Authentication & Identity

**Auth Provider:**
- Custom config resolution chain (no OAuth/SSO)
  - Priority: 1. Constructor args → 2. Config file → 3. Environment variables → 4. Fallback to Layer 1 only

**Implementation:**
- API keys loaded by:
  - Constructor parameters: `Gauntlet(openai_key="sk-...", anthropic_key="sk-ant-...")`
  - Config file: `~/.gauntlet/config.toml` (managed via `gauntlet config set` CLI)
  - Environment variables: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`
- `gauntlet/config.py` handles all resolution with fallback chain
- Config file stored with restrictive permissions (`0o600`)

## Monitoring & Observability

**Error Tracking:**
- None - Library logs warnings but does not integrate with external error services
- Errors are captured in `DetectionResult.errors` list for caller inspection

**Logs:**
- Python logging module (stdlib)
- Logger: `logging.getLogger(__name__)` per module
- Log level: DEBUG (layer initialization), WARNING (API failures, parse failures)
- No external log aggregation
- Locations:
  - `gauntlet/detector.py` - Layer initialization and cascade flow
  - `gauntlet/layers/embeddings.py` - OpenAI API failures
  - `gauntlet/layers/llm_judge.py` - Claude API failures and JSON parse failures
  - `gauntlet/config.py` - Config file read errors

**Metrics:**
- Per-layer latency: Captured in `LayerResult.latency_ms`
- Total cascade latency: Captured in `DetectionResult.total_latency_ms`
- Available in all result objects for caller to log/monitor

## CI/CD & Deployment

**Hosting:**
- PyPI - Package index for `gauntlet-ai`
- GitHub - Repository at `https://github.com/Ashwinash27/gauntlet-ai`
- Distributed as wheel: `gauntlet-0.1.1-py3-none-any.whl`

**CI Pipeline:**
- Not detected in codebase (no GitHub Actions, GitLab CI, etc.)

**Installation:**
```bash
pip install gauntlet-ai                    # Layer 1 only
pip install gauntlet-ai[embeddings]        # + Layer 2
pip install gauntlet-ai[llm]               # + Layer 3
pip install gauntlet-ai[cli]               # + CLI tools
pip install gauntlet-ai[mcp]               # + MCP server
pip install gauntlet-ai[all,dev]           # Everything
```

## Environment Configuration

**Required env vars:**
- None (Layer 1 works zero-config)

**Optional env vars:**
- `OPENAI_API_KEY` - Enables Layer 2 (OpenAI text embeddings)
- `ANTHROPIC_API_KEY` - Enables Layer 3 (Claude LLM judge)

**Secrets location:**
- Environment variables (preferred for CI/CD)
- `~/.gauntlet/config.toml` (user machine)
- `.env` file (development only, listed in `.gitignore`)

**Configuration options:**
- `embedding_model` (default: `text-embedding-3-small`)
- `embedding_threshold` (default: 0.55)
- `llm_model` (default: `claude-3-haiku-20240307`)
- `llm_timeout` (default: 3.0 seconds)

Set via CLI:
```bash
gauntlet config set embedding_model text-embedding-3-large
gauntlet config set embedding_threshold 0.60
gauntlet config list
```

## Webhooks & Callbacks

**Incoming:**
- None - Gauntlet is a detection library, not a server (except MCP server mode)

**Outgoing:**
- None - No callbacks or webhooks to external services

**MCP Server:**
- `gauntlet mcp-serve` - Starts MCP server for Claude Code integration
  - Listens on stdio
  - Provides two tools: `check_prompt` and `scan_file`
  - Location: `gauntlet/mcp_server.py`
  - No network exposure (stdio-based communication)

---

*Integration audit: 2026-02-18*

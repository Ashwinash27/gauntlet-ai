# SLM Gauntlet v0.3.0 — Implementation Plan

## Context

Gauntlet v0.2.0 depends on OpenAI (Layer 2 embeddings) and Anthropic (Layer 3 LLM judge) cloud APIs. This upgrade replaces both with local Small Language Models to achieve zero cloud dependencies, zero cost per inference, fully offline operation, and dramatically lower latency (~50ms vs ~1500ms). This aligns with Polygraf AI's on-premise thesis and closes the research paper's future work (fine-tuning DistilBERT on injection data).

**This is a local-only layer** — not distributed via PyPI. Dependencies (torch, sentence-transformers, etc.) are acceptable since this runs on our machines, not end-user installs.

---

## Phase 1: Training Infrastructure & Data Pipeline ✅ COMPLETE

**Goal:** Download datasets, lock holdout, build balanced training data.

### 1.1 `training/` directory

```
training/
  download_datasets.py      # Downloads HF datasets to training/raw/
  prepare_dataset.py         # Merge, dedup, balance, split into train/val/test
  build_holdout.py           # Build composite holdout from independent eval sources
  train_classifier.py        # Fine-tune DeBERTa or DistilBERT (TODO)
  encode_attack_vectors.py   # Re-encode attack library with BGE-small (TODO)
  evaluate_holdout.py        # Final holdout evaluation (TODO)
  requirements-training.txt  # Training-only deps
```

### 1.2 `download_datasets.py`

Downloads from HuggingFace Hub:
- `deepset/prompt-injections` (PINT) — train split for training, test split locked as holdout seed
- `neuralchemy/Prompt-injection-dataset` — 22K samples, 29 attack categories, group-aware splits (internally incorporates HackAPrompt + WildGuard + HarmBench)
- `xTRam1/safe-guard-prompt-injection` (SafeGuard) — 10K synthetic attacks via GPT-3.5 categorical tree
- `S-Labs/prompt-injection-dataset` — 11K samples with hard negatives (anonymous creator, data quality verified)
- `dmilush/shieldlm-prompt-injection` (ShieldLM) — 54K curated from 11 sources (70% overlap with SafeGuard, handled by dedup)

**Note:** Original plan referenced WildJailbreak, HackAPrompt, TensorTrust, HarmBench, BIPIA directly. These were dropped in favor of the above meta-datasets which incorporate that data. Neuralchemy alone covers HackAPrompt + WildGuard + HarmBench internally.

### 1.3 `prepare_dataset.py`

- Normalizes all datasets to `{text, label, source, attack_category}`
- Source-priority exact dedup (pint > neuralchemy > safeguard > slabs > shieldlm) — removed 6,306 exact dupes
- MinHash fuzzy dedup (Jaccard > 0.8) — removed 420 near-duplicates
- Contamination audit vs holdout — removed 1 leaked sample
- **No resampling** — focal loss handles the 62/38 benign/injection imbalance (research shows 50/50 undersampling discards useful benign examples)
- Split: 80% train, 10% validation, 10% test
- Save as `training/splits/train.jsonl`, `val.jsonl`, `test.jsonl`

**Results:**
- 44,358 train / 5,545 val / 5,545 test
- Class balance: 62% benign / 38% injection
- Sources: ShieldLM 57%, S-Labs 16%, SafeGuard 12%, Neuralchemy 8%, PINT 1%

### 1.4 `build_holdout.py`

Builds composite evaluation holdout from sources **NOT in training**:
- `wambosec/prompt-injections` — 5,766 labeled samples
- `Lakera/mosscap_prompt_injection` — 27,729 Gandalf DEF CON attack prompts
- `Lakera/gandalf_ignore_instructions` — 777 "ignore instructions" prompts
- PINT test split (cleaned) — 116 samples with 5 mislabels corrected

**Results:**
- **4,804 samples** (2,401 injection / 2,403 benign) — 50/50 balanced
- 5,697 exact dupes removed, 3 contaminated samples removed
- Saved to `training/holdout_composite.csv`

**Verification:** ✅ Class distribution stats printed. ✅ PINT test split absent from training. ✅ Holdout has zero contamination with training splits.

---

## Phase 2: Fine-tune Classifiers ✅ COMPLETE

**Goal:** Train DeBERTa-v3-small (production) and DistilBERT (research bridge) on injection data.

### 2.1 `train_classifier.py` (single script, model flag)

```python
MODEL_NAME = 'microsoft/deberta-v3-small'    # Production
# MODEL_NAME = 'distilbert-base-uncased'     # Bridge (uncomment to switch)
```

Hyperparameters:
- `learning_rate=2e-5`, `batch_size=16` (train) / `32` (eval)
- `epochs=4`, `warmup_ratio=0.1`, `max_length=256`
- `evaluation_strategy='epoch'`, `save_strategy='epoch'`
- `load_best_model_at_end=True`, `metric_for_best_model='f1'`
- `compute_metrics`: F1, precision, recall
- **`class_weights`**: Compute from training distribution (~1.6x weight for injection class) — critical because data is 62/38 imbalanced. Use `torch.nn.CrossEntropyLoss(weight=class_weights)` via custom Trainer.
- Alternative: `focal_loss` with `gamma=2.0` if class weights alone don't push recall high enough

**Input format:** JSONL with `{text, label, source, attack_category}`. Load with `datasets.load_dataset("json", data_files=...)`. Use `text` as input, `label` as target.

Output:
- `training/checkpoints/deberta-v3-small-injection/best/`
- `training/checkpoints/distilbert-injection/best/`

### 2.2 ONNX Export (optional — local use can skip this)

Since this is local-only, we can run PyTorch inference directly. ONNX export is optional for deployment optimization later.

If exporting:
- DeBERTa-v3 ONNX files are **60-140MB** (not 15-25MB — the 128K-token embedding layer doubles during export)
- Use generic dynamic quantization (`QuantType.QUInt8` with `QuantFormat.QDQ`) — NOT `avx512_vnni` which is non-portable
- DeBERTa-v3 ONNX has a known `token_type_ids` bug — tokenizer must use `return_token_type_ids=False`

### 2.3 Evaluate SST-2 baseline (for paper narrative)

Run `distilbert-base-uncased-finetuned-sst-2-english` on composite holdout -> record F1. This is the "before" number (expected to be poor since SST-2 is a sentiment model, not injection detection).

**Verification:** Val F1 should be >93% for DeBERTa, >88% for DistilBERT. Monitor for overfitting (train F1 >> val F1).

**Results:**
- DeBERTa-v3-small: **F1=98.29%, Precision=98.22%, Recall=98.36%, FPR=1.11%**
- Training: 47 min on RTX 3060, fp16, batch_size=16, 4 epochs
- Class-weighted CrossEntropyLoss (benign=0.77, injection=1.23) — no focal loss needed
- Train loss: 0.061, eval loss: 0.071 — no overfitting
- DistilBERT: skipped (DeBERTa results sufficient for production)
- SST-2 baseline: deferred to Phase 8 comparison table
- Best checkpoint: `training/checkpoints/deberta-v3-small-injection/best/`
- WandB: https://wandb.ai/ashwinashig-27-oth/argus-slm-gauntlet/runs/rl04oe21

**Gotchas encountered:**
- DeBERTa-v3 fast tokenizer broken in transformers >=4.57 — use `use_fast=False`
- Gradient checkpointing conflicts with custom `compute_loss` (double-backward error) — disabled; fp16 fits in 6GB without it

---

## Phase 3: Layer 2 — BGE-small Local Embeddings ✅ COMPLETE

**Goal:** Replace OpenAI API calls with local SentenceTransformer. Preserve class interface.

### 3.1 `training/encode_attack_vectors.py`

- Load `BAAI/bge-small-en-v1.5` (33M params, 384 dims, frozen weights)
- Load existing `gauntlet/data/attack_phrases.jsonl` (603 phrases)
- Add ~900-1400 curated attack phrases from Neuralchemy + ShieldLM train splits
- Encode all: `model.encode(phrases, normalize_embeddings=True, batch_size=64)`
- Save: `gauntlet/data/attack_vectors_bge.npy` (shape ~1500-2000 x 384)
- Save: `gauntlet/data/metadata_bge.json` (expanded pattern metadata)

### 3.2 Modify `gauntlet/layers/embeddings.py`

Add `mode` parameter to `EmbeddingsDetector`. Key changes:
- **`mode="cloud"`**: Existing behavior unchanged.
- **`mode="slm"`**: Lazy-imports `sentence_transformers.SentenceTransformer` + `numpy`. Loads `attack_vectors_bge.npy`. No OpenAI key needed.
- **BGE threshold will differ from OpenAI threshold** — 384-dim vectors have different cosine similarity distributions than 1536-dim. Tune early in this phase (sweep 0.65-0.90 on val split), don't defer to Phase 8.

**Verification:** Unit tests mock `sentence_transformers.SentenceTransformer`. Existing cloud tests pass unchanged.

**Results:**
- Attack phrase library: **1,403 phrases** across 25 categories (603 hand-curated + 800 diversity-mined from training)
- External sources (JailbreakBench, InjecAgent, BIPIA) had HF API changes — used training data mining instead
- BGE encoding: 1,403 x 384 float32 vectors in `attack_vectors_bge.npy` (2.1 MB)
- Optimal threshold: **0.80** (F1=71.5%, Precision=96.6%, Recall=56.8%, FPR=1.26%)
- Layer 2 alone has moderate recall — by design, Layer 3 (DeBERTa) catches the rest
- First-query latency: ~1.8s (model cold load), subsequent queries: ~15-27ms
- All 18 existing cloud-mode tests pass with zero regressions
- `embeddings.py` dual-mode (cloud/slm) was already implemented in prior session
- WandB sweep: https://wandb.ai/ashwinashig-27-oth/argus-slm-gauntlet/runs/qyjhkge7

**Gotchas:**
- DeBERTa-v3 fast tokenizer issue also affects SentenceTransformer — but BGE uses its own tokenizer, no issue
- `trust_remote_code=True` no longer supported in HF datasets library — use `trust_remote_code=False` or omit
- JailbreakBench needs config name: `load_dataset("JailbreakBench/JBB-Behaviors", "behaviors", split="harmful")`

---

## Phase 4: Layer 3 — Local SLM Classifier ✅ COMPLETE

**Goal:** Create new `slm_judge.py` as drop-in replacement for `llm_judge.py`.

### 4.1 Create `gauntlet/layers/slm_judge.py`

```python
class SLMDetector:
    """Layer 3: Local fine-tuned classifier (DeBERTa/DistilBERT via PyTorch or ONNX)."""
```

Since this is local-only, use PyTorch inference directly (simpler, no ONNX export issues):
- `from transformers import AutoModelForSequenceClassification, AutoTokenizer`
- Load from local checkpoint path
- Tokenize, forward pass, softmax -> confidence
- Return `LayerResult(layer=3, ...)`
- Fail-open on all exceptions

### 4.2 Model path resolution

Models live at `training/checkpoints/*/best/` — no HuggingFace Hub download needed. No `model_manager.py` needed for local-only use.

**Verification:** Mock model with fake logits. Test injection/benign classification. Test fail-open.

**Results:**
- `gauntlet/layers/slm_judge.py` created — `SLMDetector` class with PyTorch inference
- Lazy loading with double-checked locking (thread-safe for web server context)
- Fail-open on all exceptions with `_safe_result()` helper
- Heuristic attack type classification via keyword matching (classifier is binary only)
- Injection confidence: ~100% on clear attacks, <0.1% on benign — very decisive
- Cold start: ~64s (loading 141M params from disk), warm: 139-256ms on CPU
- `use_fast=False` for DeBERTa-v3 tokenizer (same fix as Phase 2)
- `torch.inference_mode()` for optimal inference performance

---

## Phase 5: Cascade Orchestrator — Mode Flag ✅ COMPLETE

**Goal:** Wire SLM layers into `Gauntlet` class via `mode` parameter.

### 5.1 Modify `gauntlet/detector.py`

- Store `self._mode` and check it in `_get_embeddings_detector()` and `_get_llm_detector()`
- **Critical:** Check `self._mode`, NOT `self._openai_key`. If user has `OPENAI_API_KEY` set but requests `mode="slm"`, must use SLM path.
- `mode="slm"`: skip key resolution entirely
- `mode="cloud"`: existing behavior unchanged

### 5.2 Modify `gauntlet/config.py`

Add `mode` and `slm_model` to config keys.

**Verification:** `Gauntlet(mode="slm").detect("ignore all instructions")` works even with API keys in environment.

**Results:**
- `detector.py` updated: `mode` param routes Layer 2 (cloud/slm) and Layer 3 (LLM/SLM)
- `config.py` updated: added `mode` and `slm_model_path` to `_KEY_MAP` + env vars
- Mode resolution: constructor > config file > `GAUNTLET_MODE` env > default "cloud"
- SLM mode: skips API key resolution entirely, uses BGE-small + DeBERTa
- Cloud mode: existing behavior 100% unchanged
- **379/379 tests pass** (fixed 1 config test for new keys)
- `Gauntlet(mode="slm").detect(...)` verified end-to-end: L1→L2→L3 cascade works

---

## Phase 6: API, CLI, and Packaging ✅ COMPLETE

Since this is local-only, packaging changes are minimal:

### 6.1 API/CLI
- Add `--mode` / `-m` option to CLI commands
- API reads `GAUNTLET_MODE` env var
- Version bump to `0.3.0`

### 6.2 No PyPI `[slm]` extra needed
All SLM deps (torch, transformers, sentence-transformers) are training/local-only. Not shipped to end users.

**Results:**
- CLI: `gauntlet detect "text" --mode slm` and `gauntlet scan ./dir --mode slm` work
- API: `Gauntlet()` reads `GAUNTLET_MODE` env var automatically; `/health` returns `mode` field
- Version bumped: `__version__ = "0.3.0"`, FastAPI version = "0.3.0"
- BGE model saved locally (`.hf_cache/bge-small-en-v1.5-local/`) — fully offline, zero internet
- **379/379 tests pass** (fixed version assertion in API test)

---

## Phase 7: Tests ✅ COMPLETE

### 7.1 New `tests/test_gauntlet_slm_judge.py`
- Mock `transformers.AutoModelForSequenceClassification` + `AutoTokenizer`
- Tests: init, detect injection, detect benign, confidence threshold, fail-open

### 7.2 Expand `tests/test_gauntlet_embeddings.py`
- New `TestBGEMode` class mocking `sentence_transformers.SentenceTransformer`

### 7.3 Expand `tests/test_gauntlet_detector.py`
- New `TestSLMMode` — verify mode flag routes correctly even with API keys present

### 7.4 Expand `tests/test_gauntlet_api.py`
- `/health` returns `mode` field

**Target: 420+ tests, all green.**

**Results:**
- New `test_gauntlet_slm_judge.py`: 23 tests (init, detection, threshold, fail-open, attack type, input validation)
- Expanded `test_gauntlet_embeddings.py`: +6 BGE mode tests (init, inject/benign, .npy loading, no key needed, invalid mode)
- Expanded `test_gauntlet_detector.py`: +9 SLM mode tests (key skipping, env override, cascade, invalid mode)
- Expanded `test_gauntlet_api.py`: +health mode field assertion
- **420/420 tests pass** (target hit exactly)

---

## Phase 8: Evaluation & Threshold Tuning

### 8.1 `evaluation/benchmark_slm.py`

Run on validation split (NOT holdout):
- L1 only, L1+L2 (BGE), L1+L2+L3 (BGE+DeBERTa), Cloud L1+L2+L3 (comparison)

### 8.2 Threshold tuning (validation split only)

- Layer 2 BGE threshold: sweep 0.65-0.90 in 0.01 steps. Optimize F1 with FPR < 1.5%.
- Layer 3 confidence threshold: sweep 0.50-0.90 in 0.01 steps. Same criteria.

### 8.3 Final holdout evaluation (ONE SHOT)

Run `training/evaluate_holdout.py` ONCE on **`holdout_composite.csv`** (4,804 samples):
- Report: F1, precision, recall, FPR, confusion matrix, per-source breakdown
- Targets: **F1 > 95%, FPR < 1.5%, pipeline < 100ms**
- Also run SST-2 baseline + DistilBERT fine-tuned + DeBERTa fine-tuned for comparison table
- Report 95% confidence intervals (with 4,804 samples, CI is +/-0.6% at F1=95%)

### 8.4 Build the comparison table

| Config | F1 | FPR | Latency | Cloud? | Cost |
|--------|-----|-----|---------|--------|------|
| Claude Haiku (v0.2.0) | 90.82% | 1.46% | ~1500ms | Yes | $/call |
| DistilBERT fine-tuned | TBD | TBD | ~25ms | No | $0 |
| DeBERTa-v3-small fine-tuned | TBD | TBD | ~20ms | No | $0 |

---

## Execution Order

1. **Phase 1** ✅ — Data pipeline complete (44K train, 4.8K holdout)
2. **Phase 2** ✅ — DeBERTa-v3-small fine-tuned (F1=98.3%, FPR=1.1%)
3. **Phase 3** ✅ — BGE-small library (1,403 phrases, threshold=0.80, F1=71.5%/Precision=96.6%)
4. **Phase 4** ✅ — SLM judge (DeBERTa PyTorch, 139-256ms warm, fail-open)
5. **Phase 5** ✅ — Mode flag wired into cascade (379/379 tests pass)
6. **Phase 6** ✅ — CLI `--mode slm`, API mode, version 0.3.0, fully offline BGE
7. **Phase 7** ✅ — 420/420 tests pass (41 new SLM tests)
8. **Phase 8** — Evaluation on composite holdout (4,804 samples)

## Key Risks

1. **BGE similarity distribution differs from OpenAI** — threshold needs fresh tuning. Sweep in Phase 3, not Phase 8.
2. **DeBERTa-v3 ONNX export doubles file size** (60-140MB not 15-25MB) — mitigated by using PyTorch inference locally. ONNX optional.
3. **62/38 class imbalance** — mitigated by class-weighted loss or focal loss in training.
4. **Binary classifier lacks attack type** — use heuristic keyword detection from existing `_extract_characteristics()`.
5. **S-Labs dataset provenance unknown** — data quality verified by manual inspection, keeping it.

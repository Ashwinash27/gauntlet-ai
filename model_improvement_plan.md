# Gauntlet SLM v0.3.1 — Model Improvement Plan

## Problem Statement

Gauntlet SLM v0.3.0 has strong recall but catastrophic false positive rates on out-of-distribution benign text:

| Model | NotInject FPR | ProtectAI F1 | ProtectAI FPR | ProtectAI Recall |
|-------|--------------|--------------|---------------|-----------------|
| **Gauntlet SLM v0.3.0** | **60.5%** | 0.632 | 44.2% | 73.1% |
| ProtectAI v2 | 42.8% | 0.452 | 23.2% | 38.2% |
| Meta Prompt Guard 2 | 6.5% | 0.426 | 9.4% | 30.4% |
| deepset v3 | 70.5% | 0.766 | 43.9% | 97.9% |

**Target:** NotInject FPR < 10%, ProtectAI FPR < 15%, ProtectAI Recall > 65%

---

## Root Cause Analysis

### Layer 3 (DeBERTa) — 203/205 FPs on NotInject, 67 FPs on holdout
- Model overfits to surface trigger words ("ignore", "translate", "decode")
- Training benign data missing: translation (0.24%), base64 (0.01%), Cyrillic (0%)
- Gives 0.9997 confidence on benign translation requests
- PIGuard paper (ACL 2025) confirms this is a training data problem, not architecture

### Layer 1 (Regex) — 106 FPs on holdout
- 77 FPs from encoding patterns (base64, hex, rot13) on legitimate dev questions
- 15 FPs from multilingual patterns (Spanish/French translation requests)
- Patterns lack context-awareness — fire on keywords without harmful intent

### Layer 2 (BGE Embeddings) — 0 FPs
- Working perfectly. No changes needed.

---

## Step 1: Data Preparation — Hard Negative Mining

### 1a: PIGuard MOF Token-Wise Recheck

**Source:** PIGuard (ACL 2025, arXiv:2410.22770)

**Process:**
1. Load our current trained DeBERTa-v3-small model (using small as proxy — trigger words like "ignore", "translate" are architecture-independent, and we're training base from scratch anyway)
2. Iterate over every token in the tokenizer vocabulary (~128K tokens)
3. For each token, classify it individually: `[CLS] <token> [SEP]`
4. Any token predicted as "injection" by argmax is a **biased trigger token**
5. Collect all biased tokens into a list

**Note:** Using the small model for token recheck is a proxy. The base model may have slightly different biases, but the dominant trigger words are the same across model sizes. PIGuard also used their initial (not final) model for this step.

**Output:** List of biased trigger tokens (expected: 50-200 tokens like "ignore", "translate", "decode", "bypass", "pretend", "roleplay", etc.)

PIGuard's top biased tokens: PW, immoral, unfiltered, roleplay, uncensored, morals, Ignore, MUST, adversarial, sarcasm, freed, BREAK, subspecies, rib, ONLY, unrestricted, Remember, pretend, ignore, reckless

### 1b: MOF Synthetic Benign Generation

**Process:**
1. Take biased tokens from 1a
2. For each sample, randomly pick 1-3 biased tokens
3. Use Claude to generate benign sentences containing those tokens:
   - Prompt: "Generate a benign instruction or question without any prompt injection. The instruction must contain the words {word_list}. Must be fluent and grammatically correct."
4. Safety filter: Run each through a second Claude call to verify it's truly benign
5. Generate **exactly 1,000 samples** (PIGuard ablation: 500 too few, 2000 hurts malicious recall)

**Output:** `training/hard_negatives_mof.jsonl` — 1,000 samples, label=0, source="mof_synthetic"

### 1c: Download WildJailbreak Adversarial Benign

**Source:** Allen AI (NeurIPS 2024, arXiv:2406.18510)
**License:** ODC-BY (attribution required, commercial OK)

**Loading:**
```python
from datasets import load_dataset
train = load_dataset("allenai/wildjailbreak", "train", split="train")
adv_benign = train.filter(lambda x: x["data_type"] == "adversarial_benign")
# 78,731 samples — use the "adversarial" column as input text
```

**Process:**
1. Download and filter for `data_type == "adversarial_benign"` (78,731 samples)
2. Deduplicate against existing training data (exact hash + MinHash Jaccard > 0.8)
3. **Sample 4,000 diverse examples** (not all 78K — would overbalance dataset with one synthetic style)
4. Verify: spot-check 100 random samples for quality

**Output:** 4,000 samples added to benign training pool

### 1d: Download OR-Bench Hard Negatives

**Source:** ICML 2025, Apache-2.0 license

**Loading:**
```python
from datasets import load_dataset
hard = load_dataset("bench-llm/or-bench", "or-bench-hard-1k", split="train")
# 1,319 benign samples that trigger over-refusal
# Columns: prompt, category
```

**Process:**
1. Load the hard-1k config (1,319 curated hard negatives)
2. Deduplicate against existing training data
3. Add all (small enough to include entirely)

**Output:** ~1,300 samples added to benign training pool

### 1e: Download XSTest v2 Benign Prompts

**Source:** arXiv:2308.01263, CC-BY-4.0 license

**Loading:**
```python
from datasets import load_dataset
ds = load_dataset("natolambert/xstest-v2-copy", split="prompts")
safe = ds.filter(lambda x: not x["type"].startswith("contrast_"))
# 250 safe prompts with dual-meaning trigger words
# Use "prompt" column as input text
```

**Process:**
1. Filter for non-contrast types (250 safe prompts)
2. These contain: homonyms ("kill a process"), figurative language ("bomb a test"), safe targets, safe contexts

**Output:** 250 samples added to benign training pool

### 1f: Targeted Synthetic Samples for Specific Gaps

**Generate with Claude** for categories with near-zero representation:
- Translation requests: 200 samples (Spanish, French, German, Chinese, Russian, Arabic)
- Encoding/decoding questions: 100 samples (base64, hex, ROT13, URL encoding)
- Non-ASCII code discussions: 100 samples (Cyrillic, Greek, CJK in code)
- "Ignore"/"instructions"/"system" in benign context: 100 samples

**Output:** `training/hard_negatives_targeted.jsonl` — 500 samples

### Step 1 Totals

| Source | Samples | Type |
|--------|---------|------|
| MOF synthetic (1b) | 1,000 | Trigger-word benign (synthetic) |
| WildJailbreak (1c) | 4,000 | Adversarial benign (synthetic - GPT-4) |
| OR-Bench hard (1d) | ~1,300 | Over-refusal benign (curated) |
| XSTest v2 (1e) | 250 | Dual-meaning benign (human-crafted) |
| Targeted synthetic (1f) | 500 | Gap-filling benign (synthetic - Claude) |
| **Total new benign** | **~7,050** | **~78% synthetic, ~22% curated/human** |

**New dataset composition:**
- Original: 34,151 benign + 21,297 injection = 55,448 (1.6:1)
- New: **41,201 benign + 21,297 injection = 62,498 (1.9:1)**
- Synthetic is ~11% of total dataset (7,050 / 62,498) — acceptable ratio
- Can push to 3:1 by adding more WildJailbreak if needed, but prefer real data

---

## Step 2: Rebuild Training Splits

**Process:**
1. Merge all new benign samples into unified format: `{text, label=0, source, attack_category="none"}`
2. Run deduplication against existing training data AND holdout_composite.csv (contamination check)
3. Stratified split: 80% train / 10% val / 10% test
4. Save as `training/splits/train_v2.jsonl`, `val_v2.jsonl`, `test_v2.jsonl`
5. Keep original v1 splits untouched as backup

**Validation with DuckDB MCP:**
- Check class balance per split
- Check source distribution
- Verify no holdout contamination
- Check text length distribution for data leakage signals

---

## Step 3: Implement Focal Loss Training

### 3a: Focal Loss Implementation

**Formula:** `FL(p_t) = -alpha_t * (1 - p_t)^gamma * log(p_t)`

**In train_classifier.py**, modify `WeightedTrainer.compute_loss()`:
```python
# Get softmax probabilities
probs = F.softmax(logits, dim=-1)
# Probability of true class
p_t = probs.gather(1, labels.unsqueeze(1)).squeeze(1)
# Standard CE loss with class weights as alpha
ce_loss = F.cross_entropy(logits, labels, weight=alpha_weights, reduction='none')
# Apply focal modulation
focal_loss = ((1 - p_t) ** gamma) * ce_loss
loss = focal_loss.mean()
```

**Class-weighted focal loss** (recommended): Keep existing inverse-frequency weights as alpha, ADD focal gamma modulation on top. Gives both data-driven class balancing AND hard-example focusing.

### 3b: Model Configuration Changes

In `train_classifier.py`:
- Line 34: `MODEL_NAME = "microsoft/deberta-v3-base"` (was `small`)
- Lines 39-40: Checkpoint dir → `deberta-v3-base-injection-v2`
- Add CLI args: `--gamma` (default 2.0), `--alpha_scale` (default 1.0)
- Add FPR to evaluation metrics display
- `use_fast=False` still required for DeBERTa-v3

### 3c: Memory Planning (RTX 3060 6GB)

DeBERTa-v3-base = 184M total params (86M backbone + 98M embedding):
- Model in fp16: ~368MB
- Optimizer states: ~1.47GB
- Activations (batch=16, seq=256): ~1.5-2.5GB
- **Total: ~3.7-4.7GB — fits in 6GB without gradient checkpointing**
- If OOM: reduce batch to 8, grad_accum=2

### 3d: Hyperparameters — Use PIGuard's Proven Values First

**Skip Optuna for the first training run.** Each trial is ~2hrs on RTX 3060, and 12-20 trials = 1-2 days of GPU time. Instead:

**First run:** Use PIGuard's proven hyperparams + focal loss defaults:
- lr=2e-5, epochs=3, batch=32 (or 16 if OOM), gamma=2.0, class-weighted alpha
- If this hits targets → done
- If not → THEN use Optuna to search gamma ∈ [1.0, 3.0] and lr ∈ [1e-5, 3e-5]

---

## Step 4: Train DeBERTa-v3-base

**CRITICAL: Retrain FROM SCRATCH, not fine-tune from v0.3.0 checkpoint.**
PIGuard ablation showed fine-tuning from biased checkpoint only achieves 75% avg vs 83.5% from scratch.

**Hyperparameters (starting point):**
- Base model: `microsoft/deberta-v3-base`
- Learning rate: 2e-5 (or Optuna-selected)
- Batch size: 16 (fp16)
- Epochs: 3-4 (early stopping patience=2)
- Max length: 256
- Warmup ratio: 0.1
- Weight decay: 0.01
- Loss: Focal loss (gamma=2.0, class-weighted alpha)
- Seed: 42

**Monitor during training:**
- Val F1 (primary)
- Val FPR (secondary — NEW, was not tracked before)
- Train/val loss convergence

**Track with WandB** (already integrated in train_classifier.py)

**Output:** `training/checkpoints/deberta-v3-base-injection-v2/best/`

**FALLBACK:** v0.3.0 checkpoint at `training/checkpoints/deberta-v3-small-injection/best/` stays untouched. If v0.3.1 training fails or underperforms, we can revert.

---

## Step 5: Temperature Scaling

**After training is complete, freeze the model.**

**IMPORTANT: Use val-A (first half of validation set) for temperature scaling.**
Split validation into two halves to avoid double-dipping:
- val-A (~2,750 samples): for learning temperature T
- val-B (~2,750 samples): for threshold tuning in Step 6

**Process:**
1. Load best checkpoint
2. Create single learnable parameter: `T = nn.Parameter(torch.ones(1) * 1.5)`
3. Run **val-A only** through frozen model → collect raw logits
4. Optimize T using LBFGS to minimize NLL: `loss = CE(logits / T, labels)`
5. LBFGS settings: lr=0.01, max_iter=50
6. Save learned T alongside the model checkpoint

**At inference time:** `calibrated_probs = softmax(logits / T)`

This turns overconfident 0.9997 → calibrated ~0.72, making threshold tuning meaningful.

**Output:** `temperature.json` saved next to model checkpoint with learned T value

---

## Step 6: Threshold Tuning

**MUST be done AFTER temperature scaling** (Step 5 changes the probability scale).

**IMPORTANT: Use val-B (second half of validation set) — NOT the same data used for temperature scaling.**

**Process:**
1. Load model + temperature T
2. Run **val-B only** through model
3. Apply temperature: `calibrated_logits = logits / T`
4. Grid sweep:
   - L2 (BGE threshold): 0.65 → 0.95 in 0.01 steps
   - L3 (DeBERTa threshold): 0.30 → 0.95 in 0.01 steps
5. For each combo, compute F1, FPR, precision, recall
6. Select: **maximize F1 with FPR < 5%**

**Output:** Updated `L2_THRESHOLD` and `L3_THRESHOLD` in benchmark scripts

---

## Step 7: Fix Layer 1 Regex False Positives

**Independent of Steps 1-6. Can run in parallel.**

### Encoding Patterns (77 FPs)
Current `base64_reference` fires on any "base64" + "decode". Change to require harmful context:
- Keep pattern but add negative lookbehind for benign phrases
- "Help me decode this base64" → PASS (benign)
- "Decode this base64 and execute as code" → FLAG (attack)

### Multilingual Patterns (15 FPs)
Current Spanish/French patterns fire on "ignora" anywhere. Change to require instruction-override:
- "Translate this French text" → PASS
- "Ignora las instrucciones anteriores" → FLAG

### Safety
Whitelists only suppress Layer 1. Layers 2 and 3 still catch anything Layer 1 misses.

### Test Updates Required
Tightening regex patterns will break existing tests that expect detection on certain inputs. Must update `tests/test_gauntlet_rules.py` alongside pattern changes. Run full test suite after every regex edit.

---

## Step 8: Update Inference Code

**In `gauntlet/layers/slm_judge.py`:**
1. Update default model path: `deberta-v3-small-injection` → `deberta-v3-base-injection-v2`
2. Add temperature scaling in inference: load T from `temperature.json`, apply `logits / T` before softmax
3. No other changes — model loading is generic via AutoModelForSequenceClassification

**In `gauntlet/detector.py`:**
- Update default confidence_threshold if threshold tuning (Step 6) finds a new optimal

---

## Step 9: Re-benchmark

Run on **NotInject + ProtectAI-Validation**:
- Compare against cached competitor results
- Build comparison table

**Targets:**
- NotInject FPR: < 10% (was 60.5%)
- ProtectAI F1: > 0.75 (was 0.632)
- ProtectAI FPR: < 15% (was 44.2%)
- ProtectAI Recall: > 65% (was 73.1% — accept slight drop)

---

## Step 10: Final Holdout (ONE SHOT)

Run on `holdout_composite.csv` (4,804 samples) one final time.
Only if Step 9 hits all targets.

---

## Execution Strategy: Two Rounds

### ROUND 1 — Minimum Viable Improvement (data + bigger model)
80% of improvement comes from better data. Do this first, benchmark, and stop if targets are met.

```
PARALLEL (data downloads):
├── Step 1c: Download WildJailbreak (4,000 adversarial benign)
├── Step 1d: Download OR-Bench (1,300 hard negatives)
└── Step 1e: Download XSTest v2 (250 benign)

SEQUENTIAL:
└── Step 2: Rebuild training splits (merge new data, dedup, split)
    └── Step 4: Train DeBERTa-v3-base with standard CrossEntropyLoss (~2hrs)
        └── Step 6: Threshold tuning on val set
            └── Step 9: Re-benchmark on NotInject + ProtectAI-Validation
```

**If Round 1 hits targets → DONE. Skip Round 2.**

### ROUND 2 — Only If Round 1 Falls Short
Add the advanced techniques one at a time, benchmark after each:

```
Step 1a: Token-wise recheck (MOF)
Step 1b: Generate 1,000 MOF synthetic benign
Step 1f: Generate 500 targeted synthetic samples
Step 3: Implement focal loss (gamma=2.0, class-weighted alpha)
Step 5: Temperature scaling (val-A)
Step 6: Re-tune thresholds (val-B)
Step 7: Fix Layer 1 regex
Step 8: Update inference code
Step 9: Re-benchmark
Step 10: Final holdout (if targets met)
```

---

## MCP Tools Used

| MCP | When | Why |
|-----|------|-----|
| **DuckDB** | Step 2 | Analyze training data distributions, check class balance, verify no holdout contamination |
| **Optuna** | Step 3d | Hyperparameter search for focal loss gamma/alpha + learning rate |
| **WandB** | Step 4 | Track training runs, compare metrics across experiments |

---

## Files Changed

| File | Change | Step |
|------|--------|------|
| `training/train_classifier.py` | Model name, focal loss, checkpoint path, FPR metric | 3 |
| `training/prepare_data_v2.py` | New script to merge hard negatives + rebuild splits | 2 |
| `training/token_recheck.py` | New script for MOF token-wise recheck | 1a |
| `training/generate_mof.py` | New script for MOF synthetic generation | 1b |
| `training/download_hard_negatives.py` | New script to download WildJailbreak/OR-Bench/XSTest | 1c-e |
| `training/temperature_scaling.py` | New script for post-training calibration | 5 |
| `gauntlet/layers/slm_judge.py` | Model path, temperature scaling in inference | 8 |
| `gauntlet/layers/rules.py` | Tighten encoding/multilingual patterns | 7 |
| `gauntlet/detector.py` | Optional threshold update | 8 |
| `training/benchmark_gauntlet.py` | Updated thresholds | 9 |

---

## Key Research Sources

| Source | Key Insight | Paper |
|--------|-----------|-------|
| **PIGuard** | MOF: token-wise recheck + 1K synthetic benign → 87.3% NotInject | ACL 2025, arXiv:2410.22770 |
| **Meta Prompt Guard 2** | Energy-based loss, 6.5% FPR, mDeBERTa-v3-base | HuggingFace model card |
| **WildJailbreak** | 78K adversarial benign samples | NeurIPS 2024, arXiv:2406.18510 |
| **OR-Bench** | 80K over-refusal benign, 1.3K hard subset | ICML 2025 |
| **XSTest v2** | 250 dual-meaning trigger word benign | arXiv:2308.01263 |
| **ModernBERT vs DeBERTa** | DeBERTa-v3 wins on classification accuracy | arXiv:2504.08716 |
| **Focal Loss** | Asymmetric alpha + gamma for FPR reduction | Lin et al. (RetinaNet) |
| **Temperature Scaling** | Single-param post-hoc calibration | Guo et al. ICML 2017 |

---

## Constraints & Risks

- **Fully offline CPU inference < 300ms** — DeBERTa-v3-base at 30-80ms, within budget
- **holdout_composite.csv untouched** until Step 10 — dedup ALL new data against holdout BEFORE training (Step 2)
- **Retrain from scratch** (PIGuard finding) — do NOT fine-tune from biased v0.3.0 checkpoint
- **1,000 MOF samples optimal** — more hurts malicious recall per PIGuard ablation
- **WildJailbreak is GPT-4 generated** — spot-check 100 samples for quality before adding; capped at 4,000 to avoid synthetic style dominance
- **420 existing tests must pass** after inference code changes — regex changes (Step 7) WILL break some tests, update them
- **Recall may drop from 73.1% to ~65-70%** — acceptable per user priority (low FPR first)
- **v0.3.0 checkpoint preserved** as fallback — new model trains to separate directory
- **Val set split into A/B** — temperature scaling on val-A, threshold tuning on val-B, no double-dipping
- **MOF token recheck uses small model as proxy** — acceptable since trigger words are architecture-independent
- **Skip Optuna initially** — use PIGuard's proven hyperparams first, only tune if targets not met

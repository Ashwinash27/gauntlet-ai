# Gauntlet v0.3.0 — Interview Prep Notes

> These notes document every step of building the SLM upgrade, explaining the **what**, **why**, and **tradeoffs** so you can walk through the entire process in an interview.

---

## Project Overview

**Gauntlet** is a prompt injection detection library for LLM applications. It runs a 3-layer cascade:
1. **Layer 1 — Rules**: Regex pattern matching (zero dependencies, ~1ms)
2. **Layer 2 — Embeddings**: Semantic similarity against known attack vectors
3. **Layer 3 — LLM Judge**: AI classifier that reasons about the input

**v0.2.0** uses cloud APIs (OpenAI for embeddings, Anthropic Claude for judge). **v0.3.0** replaces both with local models — zero cloud cost, full offline, ~20x lower latency.

### Interview talking points:
- "We had a working cloud-based system but needed to eliminate API costs and latency for production use"
- "The key architectural decision was keeping the cascade design but swapping cloud layers for local ONNX models"
- "DeBERTa-v3-small was chosen over DistilBERT based on research showing 94.6% F1 vs ~88% — the 6% gap matters for security"

---

## Phase 1: Training Data Pipeline

### What we're building
A production-grade data pipeline that downloads, cleans, deduplicates, and splits datasets for fine-tuning a DeBERTa-v3-small prompt injection classifier.

### Dataset Selection (Interview Gold)

**Original plan**: 8 datasets. **Final plan**: 4+1. Here's why each was kept or dropped:

| Dataset | Decision | Why |
|---------|----------|-----|
| PINT (deepset) | **KEEP** — holdout | Gold standard benchmark, 128-row test split LOCKED for final eval |
| Neuralchemy | **KEEP** | 22K samples, 29 attack categories — best category coverage |
| SafeGuard | **KEEP** | 10K clean labeled pairs |
| S-Labs | **KEEP** | 15K samples, good diversity |
| ShieldLM | **KEEP** (with caution) | 54K samples but **contains SafeGuard inside it** — requires source-aware dedup |
| WildJailbreak | **DROPPED** | 262K rows but adversarial pairs format — not direct injection classification |
| HackAPrompt | **DROPPED** | Real attack submissions but extremely noisy, many partial/broken prompts |
| Pliny | **DROPPED** | Image-based challenges — our classifier is text-only |
| HarmBench | **DROPPED** | Harmful requests ≠ prompt injections (different threat model) |
| TensorTrust | **DROPPED** | Game-based attacks too narrow, doesn't generalize |

**Interview talking point**: "Dataset curation was as important as model choice. We dropped 60% of our original datasets after research revealed quality issues — Pliny was image-based, HarmBench conflated harmful requests with prompt injections, and HackAPrompt had too much noise."

### Data Contamination Problem (Key Technical Challenge)

**The problem**: ShieldLM (~54K samples) contains SafeGuard (~10K samples) *verbatim*. If you naively merge both, you get duplicated data that inflates metrics — the model memorizes these samples and performs artificially well on them.

**Why it's hard to detect**:
- Exact text matching catches identical copies
- But some copies have minor modifications (whitespace, punctuation)
- Standard dedup (`drop_duplicates`) only catches exact matches

**Our solution — 3-tier dedup**:
1. **Source-priority exact dedup**: Sort by data quality (pint > neuralchemy > safeguard > slabs > shieldlm), keep highest-priority copy
2. **MinHash fuzzy dedup**: Uses Locality-Sensitive Hashing (LSH) with word-level 3-shingles. Jaccard threshold 0.8 catches near-duplicates that differ by ~20% of words
3. **Holdout contamination audit**: Separate pass against the locked PINT test set with higher threshold (0.9) to catch any test-set leakage

**Interview talking points**:
- "We discovered ShieldLM contained SafeGuard inside it during our dataset audit — this would have caused evaluation leakage"
- "We used MinHash LSH for fuzzy deduplication — it's O(n) insert and query, not O(n²), so it scales to 100K+ samples in under a minute"
- "The contamination audit uses a higher Jaccard threshold (0.9 vs 0.8) because we want to be aggressive about removing holdout leaks but not over-remove legitimate similar training samples"

### Technical Concepts to Know for Interviews

#### MinHash LSH (Locality-Sensitive Hashing)
- **What**: Probabilistic data structure for estimating Jaccard similarity between sets
- **How**: Each text → set of word shingles → MinHash signature (128 hash values) → LSH bands
- **Why not exact matching**: "ignore all previous" and "ignore  all  previous" (extra spaces) are different strings but the same attack
- **Complexity**: O(n) vs O(n²) for pairwise comparison
- **Library**: `datasketch` — Python implementation

#### Focal Loss (used later in training, but important context)
- **What**: Modified cross-entropy that down-weights easy examples and focuses on hard ones
- **Why**: With class-weighted loss instead of 50/50 resampling, we preserve the natural data distribution. Focal loss with γ=2 means the model spends more gradient on the examples it gets wrong
- **Interview talking point**: "We chose focal loss over resampling because undersampling discards data and oversampling causes memorization. Focal loss preserves the full dataset while addressing imbalance"

#### Hard Negatives
- **What**: Benign prompts that contain "suspicious" trigger words
- **Why**: Without these, the model learns "if text contains 'ignore instructions' → injection". But "Please summarize the previous instructions from the meeting" is perfectly benign
- **Examples**: "What does 'system prompt' mean?", "Write a function that bypasses the cache"
- **Interview talking point**: "Hard negatives teach the classifier the difference between discussing injection attacks and actually performing them — it's the difference between a book about lockpicking and actually picking a lock"

### Pipeline Architecture

```
[Download] → [Load & Harmonize Labels] → [Source-Priority Exact Dedup]
     ↓
[MinHash Fuzzy Dedup] → [Holdout Contamination Audit] → [Add Hard Negatives]
     ↓
[Class Distribution Analysis] → [Stratified Split 80/10/10] → [Save JSONL + Stats]
```

**Output schema**: `{"text": "...", "label": 0|1, "source": "pint|neuralchemy|...", "attack_category": "..."|null}`

**Target**: 60-80K samples, natural class distribution (~2-3:1 injection:benign), synthetic data capped at 25%.

### Files Changed

| File | What changed | Why |
|------|-------------|-----|
| `download_datasets.py` | 8→5 datasets, holdout protection | Research showed 4 datasets were low quality or wrong format |
| `prepare_dataset.py` | Complete rewrite: source-aware dedup, MinHash, contamination audit, hard negatives | Original had exact-only dedup and naive 50/50 resampling |
| `requirements-training.txt` | Added datasketch, xxhash | MinHash needs datasketch; fast hashing needs xxhash |

---

## How to Talk About This in Interviews

### "Tell me about a data quality problem you solved"
> "While building a prompt injection classifier, I discovered that one of our largest training datasets (54K samples) contained another dataset (10K samples) verbatim inside it. Naive deduplication wouldn't catch the partial overlaps. I implemented a 3-tier deduplication pipeline: source-priority exact matching, MinHash LSH for fuzzy dedup, and a separate contamination audit against our holdout test set. The MinHash approach runs in O(n) time, handling 100K samples in under a minute."

### "How do you handle class imbalance?"
> "Rather than the common approach of 50/50 resampling — which either discards majority data or memorizes minority data — we preserved the natural distribution and used focal loss during training. Focal loss down-weights easy examples so the model focuses gradient on the hard cases. We also generated 750 hand-crafted hard negatives: benign prompts containing trigger words like 'ignore instructions' in legitimate contexts."

### "Walk me through your ML pipeline"
> "We built a 10-stage data pipeline: download from HuggingFace, label harmonization across 5 different schemas, source-priority exact dedup, MinHash fuzzy dedup, holdout contamination audit, hard negative generation, synthetic data capping, class distribution analysis, stratified train/val/test split, and stats reporting. Each stage outputs metrics so we can audit the pipeline's behavior."

### "Why these specific datasets?"
> "We evaluated 30+ HuggingFace datasets and narrowed to 4 based on three criteria: (1) binary text classification format — we dropped image-based and adversarial-pair datasets, (2) label quality — we dropped noisy game submissions, (3) attack diversity — we kept datasets covering 29+ attack categories. The key insight was that dataset quality matters more than quantity for a security classifier."

---

*Notes will be updated as each phase progresses.*

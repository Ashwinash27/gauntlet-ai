
# Paper Checklist — What We Need Before Submitting

## Our Models

| Model | What it is | Checkpoint |
|-------|-----------|------------|
| Binary v3 | DeBERTa-v3-base, focal loss, hard negatives + MOF | `checkpoints/deberta-v3-base-injection-v3/best` |
| NLI | DeBERTa-v3-base, fine-tuned NLI format | `checkpoints/deberta-v3-base-nli-injection/best` |
| **Ensemble** | Binary + NLI, both-agree at 0.92/0.85 | Both above |
| Binary v2 | DeBERTa-v3-base, standard CE, hard negatives only | `checkpoints/deberta-v3-base-injection-v2/best` |

Plus cascade layers:
- L1: Regex (50+ patterns) + adversarial preprocessing
- L2: BGE-small embeddings (1,403 vectors, threshold 0.89)

**Best system:** Ensemble (L1 + L2 + Binary + NLI at 0.92/0.85)

## Our Best Numbers (Ensemble, 0.92/0.85)

| Metric | Gauntlet Ensemble | Meta PG2 | ProtectAI v2 | deepset |
|--------|-------------------|----------|-------------|---------|
| NotInject FPR | **4.1%** | 6.5% | 42.8% | 70.5% |
| PAI FPR | **5.5%** | 9.4% | 23.2% | 43.9% |
| PAI F1 | 0.701 | 0.426 | 0.452 | 0.766 |
| PAI Recall | 57.8% | 30.4% | 38.2% | 97.9% |

---

## P0 — Paper REJECTED without these

### [ ] 1. More Benchmarks (need 4+ total)

Current: NotInject (339) + ProtectAI-Validation (3,227) = 2 benchmarks

Need to add:

| Dataset | Samples | HuggingFace ID | Status |
|---------|---------|---------------|--------|
| deepset/prompt-injections | 662 | `deepset/prompt-injections` | NOT RUN |
| JailbreakBench | 200 | `JailbreakBench/JBB-Behaviors` | NOT RUN |
| PINT | 4,314 | Private (requested from Lakera) | WAITING |

**What to run:** All 5 of our configs (L1, L1+L2, L1+L2+Binary, L1+L2+NLI, Ensemble) + all 3 competitors (Meta PG2, ProtectAI, deepset) on ALL benchmarks. Same machine, same code.

**Effort:** 2-3 hours (inference only, no retraining)

### [ ] 2. Bootstrap Confidence Intervals

**Why:** "4.1% FPR vs 6.5%" on 339 samples = 14 vs 22 errors. Might not be statistically significant.

**What to do:** Bootstrap resample 1000x on each benchmark, report 95% CI for all metrics.

**Also:** McNemar's test for head-to-head comparisons (Gauntlet vs Meta PG2, etc.)

**Effort:** 1 hour (just math on existing predictions)

### [ ] 3. Multiple Random Seeds

**Why:** Single training run = maybe we got lucky. Reviewers require mean ± std across 3+ seeds.

**What to do:** Retrain both Binary v3 and NLI models with seeds {42, 123, 456}. Report mean and standard deviation of all metrics.

**Effort:** ~18-24 hours GPU (6 training runs: 3 binary × ~3.5hrs + 3 NLI × ~2hrs)

**Plan:** Run overnight. 2 runs per night × 3 nights. Or use Colab.

### [ ] 4. Formal Ablation Table

**What to run on ALL benchmarks:**

| Row | Config | What it tests |
|-----|--------|--------------|
| 1 | Full Ensemble (L1+L2+Binary+NLI) | Our best system |
| 2 | L1 only | Regex baseline |
| 3 | L1 + L2 | + embeddings value |
| 4 | L1 + L2 + Binary v3 only | Single model cascade |
| 5 | L1 + L2 + NLI only | NLI-only cascade |
| 6 | Binary v3 only (no L1, no L2) | Is cascade needed? |
| 7 | NLI only (no L1, no L2) | Is cascade needed? |
| 8 | Ensemble with OR (either flags) | Is both-agree needed? |
| 9 | Binary with CE loss (v2) | Does focal loss matter? |
| 10 | Zero-shot NLI (no fine-tuning) | How much does training add? |
| 11 | No adversarial preprocessing | Does sanitization matter? |
| 12 | NLI without MNLI mixing | Does forgetting prevention matter? |

**Effort:** 2 hours (inference only on existing checkpoints, except rows 9 and 12 which need existing v2 checkpoint and a separate NLI run)

---

## P1 — Borderline reject without these

### [ ] 5. Error Analysis Section

**What to write:**

**False Positives (what we flag incorrectly):**
- Chinese text with security-adjacent words (28/50 at lower thresholds)
- English text with trigger words: "BREAK the CODE", "ensure INSTRUCTIONS"
- Roleplay queries: "engage in a roleplay where you are a librarian"
- Per-category FPR breakdown

**False Negatives (what we miss):**
- Subtle social engineering without explicit injection keywords
- Code injection ("include this code snippet") — NLI model misses these
- Multi-turn attacks (we're single-turn only)
- Per-category recall breakdown

**Include:** 4-6 qualitative examples with explanations

**Effort:** 2 hours (analysis + writing)

### [ ] 6. Latency Benchmarks

**Table to produce:**

| Component | Mean Latency | P95 Latency | Hardware |
|-----------|-------------|-------------|----------|
| L1 (regex + preprocessing) | ? ms | ? ms | CPU |
| L2 (BGE embeddings) | ? ms | ? ms | GPU |
| L3 Binary | ? ms | ? ms | GPU |
| L3 NLI | ? ms | ? ms | GPU |
| L3 Ensemble (both models) | ? ms | ? ms | GPU |
| Full cascade (end-to-end) | ? ms | ? ms | GPU |
| Meta PG2 | ? ms | ? ms | GPU |
| ProtectAI v2 | ? ms | ? ms | GPU |

**Also:** Cascade flow — what % of inputs resolved at each layer:
- "X% caught by L1 (< 1ms)"
- "Y% caught by L2 (~15ms)"
- "Z% reached L3 (~100ms)"

**Effort:** 1 hour

### [ ] 7. Threshold Sensitivity Plot

**What:** Plot FPR and F1 as functions of binary threshold (x-axis) and NLI threshold (color/separate lines). Show that 0.92/0.85 is in a stable region, not on a cliff.

We already have the grid sweep data. Just needs visualization.

**Effort:** 1 hour

---

## P2 — Makes paper strong (optional)

### [ ] 8. Score Distribution Histograms

Plot binary_score and nli_score distributions for:
- True injections (ProtectAI-Validation)
- True benign (ProtectAI-Validation)
- NotInject benign (the tricky ones)

Shows visually why the ensemble works — different score patterns for each model.

### [ ] 9. Cascade Flow Diagram

Sankey or bar chart showing:
- 3,227 PAI inputs → L1 catches 660 → L2 catches 81 → L3 catches 168 → 483 missed

### [ ] 10. Adversarial Robustness Eval

Generate adversarial variants of test attacks:
- Zero-width char insertion
- Homoglyph substitution
- Whitespace insertion
- Base64 encoding

Run with and without preprocessing. Show preprocessing improves recall.

### [ ] 11. Cross-Dataset Generalization (if time)

Train on dataset A, test on dataset B. Shows model generalizes vs overfits.

---

## Paper Structure (ACL Format, ~8 pages)

```
1. Title
2. Abstract (200 words)
3. Introduction (1 page)
4. Related Work (1 page)
   - Prompt injection detection (Meta PG2, PIGuard, ProtectAI, deepset)
   - NLI for text classification (Yin 2019, Laurer 2023)
   - Cascade/ensemble methods for safety
5. Method (2 pages)
   - 3-layer cascade architecture
   - NLI framing for injection detection (the novel contribution)
   - Binary + NLI ensemble (both-agree strategy)
   - Adversarial preprocessing
   - Training details (data, hyperparameters, focal loss)
6. Experiments (2 pages)
   - Benchmarks (4+ datasets)
   - Main results table (8 systems × 4 benchmarks)
   - Ablation table
   - Zero-shot NLI finding
   - Confidence intervals + significance tests
7. Analysis (1 page)
   - Error analysis (FPs and FNs with examples)
   - Cascade flow analysis
   - Latency comparison
   - Threshold sensitivity
8. Limitations (0.5 page)
   - English-only
   - No indirect injection
   - Single-turn only
   - Benchmark limitations (NotInject size, PAI-Val not academic)
9. Conclusion (0.5 page)
10. References
Appendix: Full hyperparameters, dataset details, additional results
```

---

## Reproducibility Checklist (ACL Required)

- [ ] Code released (GitHub: Ashwinash27/gauntlet-slm)
- [ ] Model checkpoints released (HuggingFace Hub — TODO)
- [ ] Training data instructions (all public sources, scripts provided)
- [ ] All hyperparameters listed
- [ ] 3+ random seeds with mean ± std
- [ ] Bootstrap confidence intervals
- [ ] Statistical significance tests (McNemar's)
- [ ] Software versions (Python, PyTorch, transformers, CUDA)
- [ ] Compute budget (GPU type, training hours)
- [ ] Limitations section

---

## Execution Plan

### Day 1 (Today): No retraining needed
- [ ] Run deepset benchmark (all models)
- [ ] Run JailbreakBench benchmark (all models)
- [ ] Run bootstrap CIs on all existing results
- [ ] Run full ablation table
- [ ] Run latency benchmarks
- [ ] Generate threshold sensitivity plot data

### Day 2-4: Multi-seed training (overnight runs)
- [ ] Binary v3 seed=123
- [ ] Binary v3 seed=456
- [ ] NLI seed=123
- [ ] NLI seed=456
- [ ] Benchmark all seed variants
- [ ] Compute mean ± std

### Day 5-7: Writing
- [ ] Draft paper in ACL LaTeX template
- [ ] Generate all figures (score distributions, cascade flow, threshold plot)
- [ ] Write error analysis
- [ ] Submit to arxiv

---

## Target Venues

| Venue | Deadline | Difficulty | Fit |
|-------|----------|-----------|-----|
| arxiv preprint | Anytime | Free | Start here |
| EMNLP 2026 workshop (TrustNLP/SecLLM) | ~Aug 2026 | Medium | Good fit |
| EMNLP 2026 main | ~May 2026 | High | Possible with strong results |
| NAACL 2026 | ~Oct 2026 | High | Good backup |

---

## Files in paper/

| File | What it is |
|------|-----------|
| PAPER_CHECKLIST.md | This file — tracks what we need |
| PAPER_LOG.md | Complete history of all experiments and decisions |
| model_improvement_plan.md | Original improvement plan from Round 1 |
| plan.md | Initial project plan |

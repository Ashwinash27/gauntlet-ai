# Project Cleanup TODO

## Current State (April 2026)

### Two repos:
- `gauntlet-ai` (origin) — API + cloud mode + everything
- `gauntlet-slm` (slm remote) — SLM-focused fork

### Completed:

- [x] **Separate SLM-specific files clearly**
  - training/ is all SLM
  - paper/ is all SLM (PAPER_LOG.md, benchmarks, writeup)
  - slm_judge.py = SLM, llm_judge.py = cloud
  - embeddings.py = dual mode (cloud=OpenAI, slm=BGE)
  - detector.py = shared (mode="cloud" or mode="slm")

- [x] **Remove stale files**
  - Deleted: slm_gauntlet_upgrade_spec.docx, demo.py
  - Moved to paper/: PAPER_LOG.md, model_improvement_plan.md, plan.md

- [x] **Update .gitignore for training artifacts**
  - training/splits/, splits_v2/ (old) now gitignored
  - training/raw/, hard_negatives/, CSVs, NPZ files gitignored
  - training/checkpoints/ already gitignored

- [x] **Update README_SLM.md with latest results**
  - NLI approach + hypothesis design
  - 4-benchmark results (NotInject, PAI-Val, deepset, JailbreakBench)
  - Bootstrap 95% CIs + McNemar's test
  - Multi-seed validation (Binary 98.28%+/-0.11%, NLI 98.20%+/-0.06%)
  - Adversarial preprocessing section
  - Ensemble explanation (both-agree, 0.92/0.85 thresholds)
  - 444 tests badge

- [x] **Clean up training/ directory** (via .gitignore)
  - splits/ (v1) — gitignored (old)
  - splits_v2/ — gitignored (old)
  - splits_v3/ — gitignored (current binary, large)
  - splits_nli/ — gitignored (current NLI, large)
  - checkpoints/ — gitignored (model weights)

### Models (for reference):
- `deberta-v3-small-injection` — v0.3.0 (OLD, superseded)
- `deberta-v3-base-injection-v2` — Round 1 (OLD, superseded)
- `deberta-v3-base-injection-v3` — Round 2 binary with focal loss (CURRENT)
- `deberta-v3-base-nli-injection` — NLI model (CURRENT)

### Key results preserved:
- paper/benchmark_all_results.json — 8 systems x 4 benchmarks
- paper/PAPER_LOG.md — full experiment history (sections 1-15)
- training/biased_tokens.json — MOF token recheck results
- Multi-seed: Binary 98.28%+/-0.11%, NLI 98.20%+/-0.06%
- Bootstrap CIs in PAPER_LOG.md
- Ensemble thresholds: binary=0.92, nli=0.85
- 444 tests passing

### Remaining:
- [ ] Fix slm remote auth (PAT expired) and push latest

"""Phase 8 Step 1: Cascade threshold tuning (L2 + L3 joint sweep).

Pre-computes all layer scores on the validation split, then sweeps a 2D grid
of (L2_bge_threshold × L3_deberta_threshold) to find the cascade configuration
that maximizes F1 with FPR <= 1.5%.

The cascade logic: flag if L1 OR L2 OR L3 fires (early-exit in production,
but for tuning we pre-compute all scores and simulate any threshold combo).

Usage:
    python training/tune_cascade_thresholds.py
    python training/tune_cascade_thresholds.py --no_wandb
    python training/tune_cascade_thresholds.py --l3_only  # skip L2 re-encoding
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score, confusion_matrix

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "gauntlet" / "data"
SPLITS_DIR = Path(__file__).parent / "splits"
HF_CACHE = PROJECT_ROOT / ".hf_cache"
BGE_LOCAL = HF_CACHE / "bge-small-en-v1.5-local"
CHECKPOINT_DIR = (
    Path(__file__).parent / "checkpoints" / "deberta-v3-small-injection" / "best"
)

ATTACK_VECTORS_PATH = DATA_DIR / "attack_vectors_bge.npy"
BGE_MODEL = "BAAI/bge-small-en-v1.5"

# Grid ranges
L2_MIN, L2_MAX, L2_STEP = 0.65, 0.92, 0.01
L3_MIN, L3_MAX, L3_STEP = 0.30, 0.95, 0.01
FPR_CEILING = 0.015


def compute_l1_flags(texts: list[str]) -> np.ndarray:
    """Run Layer 1 (rules) on all texts, return binary flag array."""
    from gauntlet.layers.rules import RulesDetector

    detector = RulesDetector()
    flags = np.zeros(len(texts), dtype=np.int32)
    for i, text in enumerate(texts):
        result = detector.detect(text)
        flags[i] = int(result.is_injection)
    return flags


def compute_l2_scores(texts: list[str]) -> np.ndarray:
    """Encode texts with BGE-small and compute max cosine similarity
    against the attack vector library. Returns float array of max sims."""
    from sentence_transformers import SentenceTransformer

    print("  Loading BGE-small model...")
    if BGE_LOCAL.exists():
        model = SentenceTransformer(str(BGE_LOCAL))
    else:
        model = SentenceTransformer(BGE_MODEL, cache_folder=str(HF_CACHE))

    print("  Loading attack vectors...")
    attack_vectors = np.load(str(ATTACK_VECTORS_PATH), allow_pickle=False)
    print(f"  Attack library: {attack_vectors.shape[0]} vectors, {attack_vectors.shape[1]} dims")

    print(f"  Encoding {len(texts)} texts...")
    embeddings = model.encode(
        texts, normalize_embeddings=True,
        batch_size=64, show_progress_bar=True,
    )

    print("  Computing cosine similarities...")
    # (N_val x 384) @ (384 x N_attack) -> (N_val x N_attack)
    similarities = embeddings @ attack_vectors.T
    max_sims = similarities.max(axis=1)

    return max_sims.astype(np.float64)


def compute_l3_scores(texts: list[str]) -> np.ndarray:
    """Run DeBERTa forward pass on all texts, return injection probability array."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    print(f"  Loading DeBERTa from {CHECKPOINT_DIR}...")
    tokenizer = AutoTokenizer.from_pretrained(str(CHECKPOINT_DIR), use_fast=False)
    model = AutoModelForSequenceClassification.from_pretrained(str(CHECKPOINT_DIR))
    model.eval()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    print(f"  Device: {device}")

    scores = np.zeros(len(texts), dtype=np.float64)
    batch_size = 32

    print(f"  Running inference on {len(texts)} texts (batch_size={batch_size})...")
    for start in range(0, len(texts), batch_size):
        end = min(start + batch_size, len(texts))
        batch_texts = texts[start:end]

        inputs = tokenizer(
            batch_texts,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=256,
            return_token_type_ids=False,
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.inference_mode():
            logits = model(**inputs).logits
            probs = torch.nn.functional.softmax(logits, dim=-1)
            injection_probs = probs[:, 1].cpu().numpy()

        scores[start:end] = injection_probs

        if (start // batch_size) % 20 == 0:
            pct = end / len(texts) * 100
            print(f"    {end}/{len(texts)} ({pct:.0f}%)")

    return scores


def sweep_grid(
    labels: np.ndarray,
    l1_flags: np.ndarray,
    l2_scores: np.ndarray,
    l3_scores: np.ndarray,
) -> dict:
    """Sweep 2D threshold grid and find best cascade configuration."""

    l2_thresholds = np.arange(L2_MIN, L2_MAX + 0.001, L2_STEP)
    l3_thresholds = np.arange(L3_MIN, L3_MAX + 0.001, L3_STEP)

    n_benign = (labels == 0).sum()
    n_inject = (labels == 1).sum()

    best_f1 = 0.0
    best_config = None
    all_results = []

    # Also track best recall at 1% FPR for benchmark comparison
    best_recall_at_1pct = 0.0
    best_config_1pct = None

    for l2_t in l2_thresholds:
        l2_flags = (l2_scores >= l2_t).astype(np.int32)

        for l3_t in l3_thresholds:
            l3_flags = (l3_scores >= l3_t).astype(np.int32)

            # Cascade: flag if ANY layer fires
            preds = np.maximum(l1_flags, np.maximum(l2_flags, l3_flags))

            f1 = f1_score(labels, preds, pos_label=1, zero_division=0)
            precision = precision_score(labels, preds, pos_label=1, zero_division=0)
            recall = recall_score(labels, preds, pos_label=1, zero_division=0)

            # FPR = FP / (FP + TN) = FP / n_benign
            fp = int(((preds == 1) & (labels == 0)).sum())
            fpr = fp / n_benign if n_benign > 0 else 0.0

            result = {
                "l2_threshold": round(float(l2_t), 3),
                "l3_threshold": round(float(l3_t), 3),
                "f1": round(f1, 5),
                "precision": round(precision, 5),
                "recall": round(recall, 5),
                "fpr": round(fpr, 5),
                "fp": fp,
            }
            all_results.append(result)

            # Best F1 with FPR constraint
            if f1 > best_f1 and fpr <= FPR_CEILING:
                best_f1 = f1
                best_config = result

            # Best recall at 1% FPR
            if fpr <= 0.01 and recall > best_recall_at_1pct:
                best_recall_at_1pct = recall
                best_config_1pct = result

    return {
        "best_config": best_config,
        "best_config_recall_at_1pct_fpr": best_config_1pct,
        "all_results": all_results,
        "grid_size": len(all_results),
        "l2_range": [L2_MIN, L2_MAX, L2_STEP],
        "l3_range": [L3_MIN, L3_MAX, L3_STEP],
    }


def print_summary(
    labels: np.ndarray,
    l1_flags: np.ndarray,
    l2_scores: np.ndarray,
    l3_scores: np.ndarray,
    grid_results: dict,
) -> None:
    """Print detailed summary of tuning results."""

    n_total = len(labels)
    n_inject = (labels == 1).sum()
    n_benign = (labels == 0).sum()

    # L1 stats
    l1_caught = (l1_flags & labels).sum()
    l1_fp = (l1_flags & (1 - labels)).sum()

    print(f"\n{'=' * 70}")
    print("LAYER CONTRIBUTION ANALYSIS")
    print(f"{'=' * 70}")
    print(f"  Total samples: {n_total} ({n_inject} injection, {n_benign} benign)")
    print(f"  L1 (rules):    catches {l1_caught}/{n_inject} injections "
          f"({l1_caught/n_inject*100:.1f}%), {l1_fp} false positives")

    best = grid_results["best_config"]
    if best:
        l2_t = best["l2_threshold"]
        l3_t = best["l3_threshold"]

        l2_flags = (l2_scores >= l2_t).astype(np.int32)
        l3_flags = (l3_scores >= l3_t).astype(np.int32)

        # What each layer catches independently (of injections not caught by prior layers)
        l2_new = ((l2_flags == 1) & (l1_flags == 0) & (labels == 1)).sum()
        l3_new = ((l3_flags == 1) & (l1_flags == 0) & (l2_flags == 0) & (labels == 1)).sum()

        print(f"  L2 (BGE@{l2_t:.2f}): catches {l2_new} additional injections beyond L1")
        print(f"  L3 (DeBERTa@{l3_t:.2f}): catches {l3_new} additional injections beyond L1+L2")
        print(f"  Total caught: {l1_caught + l2_new + l3_new}/{n_inject} "
              f"({(l1_caught + l2_new + l3_new)/n_inject*100:.1f}%)")

        print(f"\n{'=' * 70}")
        print("BEST CASCADE CONFIGURATION (FPR <= 1.5%)")
        print(f"{'=' * 70}")
        print(f"  L2 threshold: {best['l2_threshold']}")
        print(f"  L3 threshold: {best['l3_threshold']}")
        print(f"  F1:           {best['f1']:.5f}")
        print(f"  Precision:    {best['precision']:.5f}")
        print(f"  Recall:       {best['recall']:.5f}")
        print(f"  FPR:          {best['fpr']:.5f} ({best['fp']} false positives)")

    best_1pct = grid_results.get("best_config_recall_at_1pct_fpr")
    if best_1pct:
        print(f"\n  Recall @ 1% FPR: {best_1pct['recall']:.5f} "
              f"(L2={best_1pct['l2_threshold']}, L3={best_1pct['l3_threshold']})")

    print(f"{'=' * 70}")


def main():
    parser = argparse.ArgumentParser(description="Cascade threshold tuning (L2 + L3)")
    parser.add_argument("--no_wandb", action="store_true", help="Skip WandB logging")
    parser.add_argument("--l3_only", action="store_true",
                        help="Skip L2 re-encoding (use cached BGE results)")
    args = parser.parse_args()

    print("=" * 70)
    print("Phase 8 Step 1: Cascade Threshold Tuning")
    print("=" * 70)

    # Load validation split
    print("\n[1/5] Loading validation split...")
    val = pd.read_json(SPLITS_DIR / "val.jsonl", lines=True)
    texts = val["text"].tolist()
    labels = val["label"].values
    print(f"  {len(val)} samples (injection: {(labels==1).sum()}, benign: {(labels==0).sum()})")

    # Step 1: L1 flags
    print("\n[2/5] Computing Layer 1 (rules) flags...")
    t0 = time.perf_counter()
    l1_flags = compute_l1_flags(texts)
    l1_time = time.perf_counter() - t0
    print(f"  L1 flagged {l1_flags.sum()} samples in {l1_time:.1f}s")

    # Step 2: L2 scores
    print("\n[3/5] Computing Layer 2 (BGE) similarity scores...")
    t0 = time.perf_counter()
    l2_scores = compute_l2_scores(texts)
    l2_time = time.perf_counter() - t0
    print(f"  L2 scores computed in {l2_time:.1f}s")
    print(f"  Score stats: mean={l2_scores.mean():.4f}, "
          f"std={l2_scores.std():.4f}, min={l2_scores.min():.4f}, max={l2_scores.max():.4f}")

    # Step 3: L3 scores
    print("\n[4/5] Computing Layer 3 (DeBERTa) injection probabilities...")
    t0 = time.perf_counter()
    l3_scores = compute_l3_scores(texts)
    l3_time = time.perf_counter() - t0
    print(f"  L3 scores computed in {l3_time:.1f}s")
    print(f"  Score stats: mean={l3_scores.mean():.4f}, "
          f"std={l3_scores.std():.4f}, min={l3_scores.min():.4f}, max={l3_scores.max():.4f}")

    # Step 4: Grid sweep
    print("\n[5/5] Sweeping 2D threshold grid...")
    t0 = time.perf_counter()
    grid_results = sweep_grid(labels, l1_flags, l2_scores, l3_scores)
    sweep_time = time.perf_counter() - t0
    print(f"  Swept {grid_results['grid_size']} configurations in {sweep_time:.3f}s")

    # Print summary
    print_summary(labels, l1_flags, l2_scores, l3_scores, grid_results)

    # Save results
    output_path = Path(__file__).parent / "cascade_threshold_results.json"

    # Cache raw scores for later use (holdout eval, etc.)
    scores_path = Path(__file__).parent / "val_cached_scores.npz"
    np.savez_compressed(
        str(scores_path),
        l1_flags=l1_flags,
        l2_scores=l2_scores,
        l3_scores=l3_scores,
        labels=labels,
    )
    print(f"\nCached scores saved to: {scores_path}")

    output = {
        "best_config": grid_results["best_config"],
        "best_recall_at_1pct_fpr": grid_results["best_config_recall_at_1pct_fpr"],
        "grid_size": grid_results["grid_size"],
        "l2_range": grid_results["l2_range"],
        "l3_range": grid_results["l3_range"],
        "fpr_ceiling": FPR_CEILING,
        "val_samples": len(val),
        "timing": {
            "l1_seconds": round(l1_time, 1),
            "l2_seconds": round(l2_time, 1),
            "l3_seconds": round(l3_time, 1),
            "grid_sweep_seconds": round(sweep_time, 3),
        },
        "l1_stats": {
            "flagged": int(l1_flags.sum()),
            "true_positives": int((l1_flags & labels).sum()),
            "false_positives": int((l1_flags & (1 - labels)).sum()),
        },
        "l2_score_stats": {
            "mean": round(float(l2_scores.mean()), 4),
            "std": round(float(l2_scores.std()), 4),
            "injection_mean": round(float(l2_scores[labels == 1].mean()), 4),
            "benign_mean": round(float(l2_scores[labels == 0].mean()), 4),
        },
        "l3_score_stats": {
            "mean": round(float(l3_scores.mean()), 4),
            "std": round(float(l3_scores.std()), 4),
            "injection_mean": round(float(l3_scores[labels == 1].mean()), 4),
            "benign_mean": round(float(l3_scores[labels == 0].mean()), 4),
        },
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Results saved to: {output_path}")

    # WandB logging
    if not args.no_wandb:
        try:
            import wandb

            wandb.init(
                project="argus-slm-gauntlet",
                name="cascade-threshold-sweep",
                config={
                    "l2_range": grid_results["l2_range"],
                    "l3_range": grid_results["l3_range"],
                    "fpr_ceiling": FPR_CEILING,
                    "val_samples": len(val),
                },
            )

            best = grid_results["best_config"]
            if best:
                wandb.log({
                    "best_l2_threshold": best["l2_threshold"],
                    "best_l3_threshold": best["l3_threshold"],
                    "best_f1": best["f1"],
                    "best_precision": best["precision"],
                    "best_recall": best["recall"],
                    "best_fpr": best["fpr"],
                })

            # Log heatmap data: top configs by F1
            top_results = sorted(
                grid_results["all_results"],
                key=lambda r: r["f1"],
                reverse=True,
            )[:50]
            table = wandb.Table(
                columns=["l2_threshold", "l3_threshold", "f1", "precision", "recall", "fpr"],
                data=[[r["l2_threshold"], r["l3_threshold"], r["f1"],
                       r["precision"], r["recall"], r["fpr"]] for r in top_results],
            )
            wandb.log({"top_configs": table})
            wandb.finish()
            print("WandB logging complete")
        except Exception as e:
            print(f"WandB logging failed: {e}")

    print("\nDone! Use the best thresholds for holdout evaluation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

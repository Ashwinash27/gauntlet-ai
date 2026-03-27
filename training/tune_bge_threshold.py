"""Tune BGE-small cosine similarity threshold for Layer 2.

Sweeps threshold 0.65-0.90 on the VALIDATION split (never holdout).
Finds the threshold that maximizes F1 with FPR < 1.5%.

Logs results to WandB.

Usage:
    python training/tune_bge_threshold.py
    python training/tune_bge_threshold.py --no_wandb
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent.parent / "gauntlet" / "data"
SPLITS_DIR = Path(__file__).parent / "splits"
HF_CACHE = Path(__file__).parent.parent / ".hf_cache"

ATTACK_VECTORS_PATH = DATA_DIR / "attack_vectors_bge.npy"
BGE_MODEL = "BAAI/bge-small-en-v1.5"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no_wandb", action="store_true")
    parser.add_argument("--min_threshold", type=float, default=0.65)
    parser.add_argument("--max_threshold", type=float, default=0.92)
    parser.add_argument("--step", type=float, default=0.01)
    args = parser.parse_args()

    print("=" * 60)
    print("Phase 3: BGE Threshold Tuning")
    print("=" * 60)

    # Load attack vectors
    print("\n[1/4] Loading attack vectors...")
    attack_vectors = np.load(str(ATTACK_VECTORS_PATH), allow_pickle=False)
    print(f"  Attack library: {attack_vectors.shape[0]} vectors, {attack_vectors.shape[1]} dims")

    # Load BGE model
    print("\n[2/4] Loading BGE-small model...")
    model = SentenceTransformer(BGE_MODEL, cache_folder=str(HF_CACHE))

    # Load validation split
    print("\n[3/4] Loading + encoding validation split...")
    val = pd.read_json(SPLITS_DIR / "val.jsonl", lines=True)
    print(f"  Val samples: {len(val)} (injection: {(val['label']==1).sum()}, benign: {(val['label']==0).sum()})")

    # Encode val texts
    val_texts = val["text"].tolist()
    val_labels = val["label"].values

    val_embeddings = model.encode(
        val_texts, normalize_embeddings=True,
        batch_size=64, show_progress_bar=True,
    )
    print(f"  Encoded: {val_embeddings.shape}")

    # Compute max similarity for each val sample against attack library
    print("\n  Computing cosine similarities...")
    # Matrix multiply: (N_val x 384) @ (384 x N_attack) -> (N_val x N_attack)
    similarities = val_embeddings @ attack_vectors.T
    max_sims = similarities.max(axis=1)

    print(f"  Max similarity stats: mean={max_sims.mean():.4f}, "
          f"std={max_sims.std():.4f}, min={max_sims.min():.4f}, max={max_sims.max():.4f}")

    # Injection vs benign similarity distributions
    inj_sims = max_sims[val_labels == 1]
    ben_sims = max_sims[val_labels == 0]
    print(f"  Injection max-sim: mean={inj_sims.mean():.4f}, median={np.median(inj_sims):.4f}")
    print(f"  Benign max-sim:    mean={ben_sims.mean():.4f}, median={np.median(ben_sims):.4f}")

    # Threshold sweep
    print(f"\n[4/4] Sweeping thresholds {args.min_threshold:.2f} to {args.max_threshold:.2f}...")

    thresholds = np.arange(args.min_threshold, args.max_threshold + 0.001, args.step)
    results = []

    best_f1 = 0
    best_threshold = 0
    best_result = None

    for threshold in thresholds:
        preds = (max_sims >= threshold).astype(int)
        f1 = f1_score(val_labels, preds, average="binary", pos_label=1)
        precision = precision_score(val_labels, preds, average="binary",
                                     pos_label=1, zero_division=0)
        recall = recall_score(val_labels, preds, average="binary", pos_label=1)
        recall_benign = recall_score(val_labels, preds, average="binary", pos_label=0)
        fpr = 1.0 - recall_benign

        result = {
            "threshold": round(float(threshold), 3),
            "f1": round(f1, 5),
            "precision": round(precision, 5),
            "recall": round(recall, 5),
            "fpr": round(fpr, 5),
        }
        results.append(result)

        # Best F1 with FPR constraint
        if f1 > best_f1 and fpr <= 0.015:
            best_f1 = f1
            best_threshold = threshold
            best_result = result

        # Also track unconstrained best for reporting
        if f1 > best_f1 and best_result is None:
            best_f1 = f1
            best_threshold = threshold
            best_result = result

    # Print sweep results
    print(f"\n{'Threshold':>10} {'F1':>8} {'Precision':>10} {'Recall':>8} {'FPR':>8}")
    print("-" * 50)
    for r in results:
        marker = " <-- BEST" if r["threshold"] == round(best_threshold, 3) else ""
        print(f"  {r['threshold']:>8.3f} {r['f1']:>8.5f} {r['precision']:>10.5f} "
              f"{r['recall']:>8.5f} {r['fpr']:>8.5f}{marker}")

    print(f"\n{'=' * 60}")
    print(f"Best threshold: {best_threshold:.3f}")
    print(f"  F1:        {best_result['f1']:.5f}")
    print(f"  Precision: {best_result['precision']:.5f}")
    print(f"  Recall:    {best_result['recall']:.5f}")
    print(f"  FPR:       {best_result['fpr']:.5f}")
    print(f"{'=' * 60}")

    # Save results
    output_path = Path(__file__).parent / "bge_threshold_results.json"
    output = {
        "best_threshold": round(best_threshold, 3),
        "best_result": best_result,
        "all_results": results,
        "attack_library_size": int(attack_vectors.shape[0]),
        "val_samples": len(val),
        "similarity_stats": {
            "injection_mean": round(float(inj_sims.mean()), 4),
            "injection_median": round(float(np.median(inj_sims)), 4),
            "benign_mean": round(float(ben_sims.mean()), 4),
            "benign_median": round(float(np.median(ben_sims)), 4),
        },
    }
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to: {output_path}")

    # WandB logging
    if not args.no_wandb:
        try:
            import wandb
            wandb.init(
                project="argus-slm-gauntlet",
                name=f"bge-threshold-sweep-{len(attack_vectors)}phrases",
                config={
                    "model": BGE_MODEL,
                    "attack_library_size": int(attack_vectors.shape[0]),
                    "val_samples": len(val),
                    "min_threshold": args.min_threshold,
                    "max_threshold": args.max_threshold,
                    "step": args.step,
                },
            )

            # Log sweep as a table
            for r in results:
                wandb.log({
                    "threshold": r["threshold"],
                    "f1": r["f1"],
                    "precision": r["precision"],
                    "recall": r["recall"],
                    "fpr": r["fpr"],
                })

            wandb.log({
                "best_threshold": best_threshold,
                "best_f1": best_result["f1"],
                "best_fpr": best_result["fpr"],
            })

            wandb.finish()
            print("WandB logging complete")
        except Exception as e:
            print(f"WandB logging failed: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Phase 8 Step 2: One-shot holdout evaluation.

Runs the full Gauntlet cascade (L1 -> L2 -> L3) in SLM mode on the
holdout_composite.csv dataset (4,804 samples never seen during training
or threshold tuning).

This script should be run ONCE. The numbers it produces are final.

Usage:
    python training/evaluate_holdout.py
    python training/evaluate_holdout.py --no_wandb
"""

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

# ---------------------------------------------------------------------------
# Paths & Config
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent
HOLDOUT_PATH = Path(__file__).parent / "holdout_composite.csv"

# Tuned thresholds from Step 1 (cascade_threshold_results.json)
L2_THRESHOLD = 0.89
L3_THRESHOLD = 0.49


def run_cascade_evaluation(texts: list[str], labels: np.ndarray, sources: list[str]) -> dict:
    """Run full Gauntlet cascade on all samples and collect detailed metrics."""
    sys.path.insert(0, str(PROJECT_ROOT))
    from gauntlet.layers.rules import RulesDetector
    from gauntlet.layers.embeddings import EmbeddingsDetector
    from gauntlet.layers.slm_judge import SLMDetector

    # Initialize layers
    print("  Initializing Layer 1 (rules)...")
    l1 = RulesDetector()

    print(f"  Initializing Layer 2 (BGE embeddings, threshold={L2_THRESHOLD})...")
    l2 = EmbeddingsDetector(threshold=L2_THRESHOLD, mode="slm")

    print(f"  Initializing Layer 3 (DeBERTa, threshold={L3_THRESHOLD})...")
    l3 = SLMDetector(confidence_threshold=L3_THRESHOLD)
    # Warm up L3 (first call loads model)
    print("  Warming up DeBERTa (first inference)...")
    _ = l3.detect("warmup text")
    print("  All layers ready.")

    n = len(texts)
    predictions = np.zeros(n, dtype=np.int32)
    detected_by_layer = np.zeros(n, dtype=np.int32)  # 0 = not detected
    confidences = np.zeros(n, dtype=np.float64)
    latencies = np.zeros(n, dtype=np.float64)

    print(f"\n  Running cascade on {n} samples...")
    t_start = time.perf_counter()

    for i, text in enumerate(texts):
        sample_start = time.perf_counter()

        # Layer 1: Rules
        r1 = l1.detect(text)
        if r1.is_injection:
            predictions[i] = 1
            detected_by_layer[i] = 1
            confidences[i] = r1.confidence
            latencies[i] = (time.perf_counter() - sample_start) * 1000
            continue

        # Layer 2: BGE Embeddings
        r2 = l2.detect(text)
        if r2.is_injection:
            predictions[i] = 1
            detected_by_layer[i] = 2
            confidences[i] = r2.confidence
            latencies[i] = (time.perf_counter() - sample_start) * 1000
            continue

        # Layer 3: DeBERTa
        r3 = l3.detect(text)
        if r3.is_injection:
            predictions[i] = 1
            detected_by_layer[i] = 3
            confidences[i] = r3.confidence
            latencies[i] = (time.perf_counter() - sample_start) * 1000
            continue

        # Not detected
        predictions[i] = 0
        detected_by_layer[i] = 0
        confidences[i] = r3.confidence  # L3's score even though not flagged
        latencies[i] = (time.perf_counter() - sample_start) * 1000

        if (i + 1) % 500 == 0:
            elapsed = time.perf_counter() - t_start
            rate = (i + 1) / elapsed
            eta = (n - i - 1) / rate
            print(f"    {i+1}/{n} ({(i+1)/n*100:.0f}%) - " f"{rate:.1f} samples/s - ETA {eta:.0f}s")

    total_time = time.perf_counter() - t_start
    print(
        f"  Cascade complete: {n} samples in {total_time:.1f}s " f"({n/total_time:.1f} samples/s)"
    )

    # ---------------------------------------------------------------
    # Compute metrics
    # ---------------------------------------------------------------
    n_benign = int((labels == 0).sum())
    n_inject = int((labels == 1).sum())

    f1 = f1_score(labels, predictions, pos_label=1, zero_division=0)
    precision = precision_score(labels, predictions, pos_label=1, zero_division=0)
    recall = recall_score(labels, predictions, pos_label=1, zero_division=0)

    tn, fp, fn, tp = confusion_matrix(labels, predictions, labels=[0, 1]).ravel()
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    # Layer contribution
    layer_tp = defaultdict(int)
    layer_fp = defaultdict(int)
    for i in range(n):
        layer = int(detected_by_layer[i])
        if predictions[i] == 1 and labels[i] == 1:
            layer_tp[layer] += 1
        elif predictions[i] == 1 and labels[i] == 0:
            layer_fp[layer] += 1

    # Per-source breakdown
    source_metrics = {}
    for src in sorted(set(sources)):
        mask = np.array([s == src for s in sources])
        src_labels = labels[mask]
        src_preds = predictions[mask]
        src_n = int(mask.sum())
        src_inject = int((src_labels == 1).sum())
        src_benign = int((src_labels == 0).sum())

        if src_n == 0:
            continue

        src_tp = int(((src_preds == 1) & (src_labels == 1)).sum())
        src_fp = int(((src_preds == 1) & (src_labels == 0)).sum())
        src_fn = int(((src_preds == 0) & (src_labels == 1)).sum())
        src_tn = int(((src_preds == 0) & (src_labels == 0)).sum())

        src_f1 = f1_score(src_labels, src_preds, pos_label=1, zero_division=0)
        src_prec = precision_score(src_labels, src_preds, pos_label=1, zero_division=0)
        src_recall = recall_score(src_labels, src_preds, pos_label=1, zero_division=0)
        src_fpr = src_fp / src_benign if src_benign > 0 else 0.0

        source_metrics[src] = {
            "total": src_n,
            "injection": src_inject,
            "benign": src_benign,
            "tp": src_tp,
            "fp": src_fp,
            "fn": src_fn,
            "tn": src_tn,
            "f1": round(src_f1, 5),
            "precision": round(src_prec, 5),
            "recall": round(src_recall, 5),
            "fpr": round(src_fpr, 5),
        }

    # Latency stats (exclude cold-start first sample)
    warm_latencies = latencies[1:]
    latency_stats = {
        "mean_ms": round(float(warm_latencies.mean()), 2),
        "median_ms": round(float(np.median(warm_latencies)), 2),
        "p95_ms": round(float(np.percentile(warm_latencies, 95)), 2),
        "p99_ms": round(float(np.percentile(warm_latencies, 99)), 2),
        "min_ms": round(float(warm_latencies.min()), 2),
        "max_ms": round(float(warm_latencies.max()), 2),
    }

    # False negative samples (missed injections)
    fn_indices = np.where((predictions == 0) & (labels == 1))[0]
    fn_samples = []
    for idx in fn_indices[:20]:
        fn_samples.append(
            {
                "index": int(idx),
                "source": sources[idx],
                "l3_confidence": round(float(confidences[idx]), 5),
                "text_preview": texts[idx][:150] + "..." if len(texts[idx]) > 150 else texts[idx],
            }
        )

    # False positive samples (wrongly flagged benign)
    fp_indices = np.where((predictions == 1) & (labels == 0))[0]
    fp_samples = []
    for idx in fp_indices[:20]:
        fp_samples.append(
            {
                "index": int(idx),
                "source": sources[idx],
                "detected_by_layer": int(detected_by_layer[idx]),
                "confidence": round(float(confidences[idx]), 5),
                "text_preview": texts[idx][:150] + "..." if len(texts[idx]) > 150 else texts[idx],
            }
        )

    return {
        "thresholds": {"l2_bge": L2_THRESHOLD, "l3_deberta": L3_THRESHOLD},
        "overall": {
            "total": n,
            "injection": n_inject,
            "benign": n_benign,
            "f1": round(f1, 5),
            "precision": round(precision, 5),
            "recall": round(recall, 5),
            "fpr": round(fpr, 5),
            "tp": int(tp),
            "fp": int(fp),
            "fn": int(fn),
            "tn": int(tn),
        },
        "layer_contribution": {
            "l1_true_positives": layer_tp.get(1, 0),
            "l2_true_positives": layer_tp.get(2, 0),
            "l3_true_positives": layer_tp.get(3, 0),
            "l1_false_positives": layer_fp.get(1, 0),
            "l2_false_positives": layer_fp.get(2, 0),
            "l3_false_positives": layer_fp.get(3, 0),
        },
        "per_source": source_metrics,
        "latency": latency_stats,
        "total_eval_seconds": round(total_time, 1),
        "false_negatives_sample": fn_samples,
        "false_positives_sample": fp_samples,
    }


def print_results(results: dict) -> None:
    """Pretty-print evaluation results."""
    o = results["overall"]
    lc = results["layer_contribution"]
    lat = results["latency"]

    print(f"\n{'=' * 70}")
    print("HOLDOUT EVALUATION RESULTS (ONE-SHOT)")
    print(f"{'=' * 70}")
    print(
        f"  Thresholds: L2={results['thresholds']['l2_bge']}, "
        f"L3={results['thresholds']['l3_deberta']}"
    )
    print(f"  Samples:    {o['total']} ({o['injection']} injection, {o['benign']} benign)")

    # Targets
    f1_pass = o["f1"] > 0.95
    fpr_pass = o["fpr"] < 0.015
    lat_pass = lat["median_ms"] < 100

    print(f"\n  {'METRIC':>12}  {'VALUE':>10}  {'TARGET':>15}  {'STATUS':>6}")
    print(f"  {'-' * 50}")
    print(f"  {'F1':>12}  {o['f1']:>10.5f}  {'> 0.95':>15}  {'PASS' if f1_pass else 'FAIL':>6}")
    print(f"  {'Precision':>12}  {o['precision']:>10.5f}  {'':>15}  {'':>6}")
    print(f"  {'Recall':>12}  {o['recall']:>10.5f}  {'':>15}  {'':>6}")
    print(f"  {'FPR':>12}  {o['fpr']:>10.5f}  {'< 0.015':>15}  {'PASS' if fpr_pass else 'FAIL':>6}")
    print(
        f"  {'Latency':>12}  {lat['median_ms']:>8.1f}ms  {'< 100ms':>15}  {'PASS' if lat_pass else 'FAIL':>6}"
    )

    print(f"\n  CONFUSION MATRIX:")
    print(f"    {'':>18} Pred Benign  Pred Injection")
    print(f"    {'Actual Benign':>18}  {o['tn']:>10}  {o['fp']:>10}")
    print(f"    {'Actual Injection':>18}  {o['fn']:>10}  {o['tp']:>10}")

    print(f"\n  LAYER CONTRIBUTION (true positives / false positives):")
    print(f"    L1 (rules):    {lc['l1_true_positives']:>5} TP / {lc['l1_false_positives']} FP")
    print(f"    L2 (BGE):      {lc['l2_true_positives']:>5} TP / {lc['l2_false_positives']} FP")
    print(f"    L3 (DeBERTa):  {lc['l3_true_positives']:>5} TP / {lc['l3_false_positives']} FP")

    print(f"\n  LATENCY (warm, excluding cold start):")
    print(
        f"    Mean:   {lat['mean_ms']:.1f}ms  |  P95: {lat['p95_ms']:.1f}ms  |  P99: {lat['p99_ms']:.1f}ms"
    )

    print(f"\n  PER-SOURCE BREAKDOWN:")
    print(f"    {'Source':>20} {'N':>6} {'F1':>8} {'Recall':>8} {'FPR':>8}")
    print(f"    {'-' * 55}")
    for src, m in results["per_source"].items():
        print(f"    {src:>20} {m['total']:>6} {m['f1']:>8.4f} {m['recall']:>8.4f} {m['fpr']:>8.4f}")

    if results["false_negatives_sample"]:
        print(f"\n  FALSE NEGATIVES (missed injections, showing first 10):")
        for fn in results["false_negatives_sample"][:10]:
            print(
                f"    [{fn['source']}] conf={fn['l3_confidence']:.4f}: "
                f"{fn['text_preview'][:90]}"
            )

    if results["false_positives_sample"]:
        print(f"\n  FALSE POSITIVES (wrongly flagged, showing first 10):")
        for fp_item in results["false_positives_sample"][:10]:
            print(
                f"    [{fp_item['source']}] L{fp_item['detected_by_layer']} "
                f"conf={fp_item['confidence']:.4f}: {fp_item['text_preview'][:90]}"
            )

    print(f"\n  Total wall time: {results['total_eval_seconds']:.0f}s")

    all_pass = f1_pass and fpr_pass and lat_pass
    print(f"\n  {'=' * 50}")
    print(f"  OVERALL: {'ALL TARGETS MET' if all_pass else 'SOME TARGETS MISSED'}")
    print(f"  {'=' * 50}")


def main():
    parser = argparse.ArgumentParser(description="One-shot holdout evaluation")
    parser.add_argument("--no_wandb", action="store_true", help="Skip WandB logging")
    args = parser.parse_args()

    print("=" * 70)
    print("Phase 8 Step 2: One-Shot Holdout Evaluation")
    print("=" * 70)
    print(f"  Thresholds: L2={L2_THRESHOLD}, L3={L3_THRESHOLD}")
    print("  WARNING: This should be run ONCE. Results are final.")

    # Load holdout
    print("\n[1/2] Loading holdout dataset...")
    holdout = pd.read_csv(HOLDOUT_PATH)
    texts = holdout["text"].tolist()
    labels = holdout["label"].values
    sources = holdout["source"].tolist()
    print(
        f"  {len(holdout)} samples "
        f"(injection: {(labels==1).sum()}, benign: {(labels==0).sum()})"
    )

    # Run evaluation
    print("\n[2/2] Running cascade evaluation...")
    results = run_cascade_evaluation(texts, labels, sources)

    # Print results
    print_results(results)

    # Save results
    output_path = Path(__file__).parent / "holdout_evaluation_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_path}")

    # WandB logging
    if not args.no_wandb:
        try:
            import wandb

            wandb.init(
                project="argus-slm-gauntlet",
                name="holdout-final",
                config={
                    "l2_threshold": L2_THRESHOLD,
                    "l3_threshold": L3_THRESHOLD,
                    "holdout_samples": len(holdout),
                },
            )
            wandb.log(
                {
                    "holdout_f1": results["overall"]["f1"],
                    "holdout_precision": results["overall"]["precision"],
                    "holdout_recall": results["overall"]["recall"],
                    "holdout_fpr": results["overall"]["fpr"],
                    "latency_median_ms": results["latency"]["median_ms"],
                    "latency_p95_ms": results["latency"]["p95_ms"],
                }
            )
            wandb.finish()
            print("WandB logging complete")
        except Exception as e:
            print(f"WandB logging failed: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

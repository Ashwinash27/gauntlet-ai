"""Phase 8 Step 3: Benchmark Gauntlet on standard public datasets.

Runs the Gauntlet cascade (SLM mode) on three public benchmark datasets
that are commonly used to evaluate prompt injection detectors:

1. NotInject (339 samples, all benign) — over-defense test
2. ProtectAI Validation (3,227 samples, mixed) — multi-source benchmark
3. Qualifire Benchmark (5,000 samples, mixed) — injection vs benign

Usage:
    python training/benchmark_gauntlet.py
    python training/benchmark_gauntlet.py --no_wandb
    python training/benchmark_gauntlet.py --dataset notinject  # run one only
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.metrics import (
    f1_score,
    precision_score,
    recall_score,
    confusion_matrix,
)

PROJECT_ROOT = Path(__file__).parent.parent

# Tuned thresholds
L2_THRESHOLD = 0.89
L3_THRESHOLD = 0.49


# ---------------------------------------------------------------------------
# Dataset loaders
# ---------------------------------------------------------------------------


def load_notinject() -> tuple[list[str], np.ndarray, str]:
    """Load NotInject dataset (339 benign samples with trigger words)."""
    from datasets import load_dataset

    ds = load_dataset("leolee99/NotInject")
    texts = []
    labels = []

    for split_name in ["NotInject_one", "NotInject_two", "NotInject_three"]:
        if split_name in ds:
            for row in ds[split_name]:
                texts.append(row["prompt"])
                labels.append(0)  # All benign

    return texts, np.array(labels, dtype=np.int32), "NotInject"


def load_protectai_validation() -> tuple[list[str], np.ndarray, str]:
    """Load ProtectAI prompt-injection-validation dataset (3,227 samples)."""
    from datasets import load_dataset

    ds = load_dataset("protectai/prompt-injection-validation")
    texts = []
    labels = []

    for split_name in ds:
        for row in ds[split_name]:
            texts.append(row["text"])
            # ProtectAI uses label: 1 = injection, 0 = safe
            labels.append(int(row["label"]))

    return texts, np.array(labels, dtype=np.int32), "ProtectAI-Validation"


def load_qualifire() -> tuple[list[str], np.ndarray, str]:
    """Load Qualifire prompt-injections-benchmark dataset."""
    from datasets import load_dataset

    ds = load_dataset("qualifire/prompt-injections-benchmark")
    texts = []
    labels = []

    # Determine split name
    split_name = "train" if "train" in ds else list(ds.keys())[0]
    columns = ds[split_name].column_names

    for row in ds[split_name]:
        # Try common column names
        text = row.get("text") or row.get("prompt") or row.get("input", "")
        label = row.get("label", 0)

        # Handle string labels
        if isinstance(label, str):
            label = 1 if label.lower() in ("injection", "malicious", "1", "jailbreak") else 0

        texts.append(str(text))
        labels.append(int(label))

    return texts, np.array(labels, dtype=np.int32), "Qualifire"


DATASET_LOADERS = {
    "notinject": load_notinject,
    "protectai": load_protectai_validation,
    "qualifire": load_qualifire,
}


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def evaluate_dataset(
    texts: list[str],
    labels: np.ndarray,
    dataset_name: str,
    l1,
    l2,
    l3,
) -> dict:
    """Run Gauntlet cascade on a dataset and compute metrics."""

    n = len(texts)
    n_inject = int((labels == 1).sum())
    n_benign = int((labels == 0).sum())

    print(f"\n  [{dataset_name}] {n} samples ({n_inject} injection, {n_benign} benign)")

    predictions = np.zeros(n, dtype=np.int32)
    detected_by_layer = np.zeros(n, dtype=np.int32)
    latencies = np.zeros(n, dtype=np.float64)

    t_start = time.perf_counter()

    for i, text in enumerate(texts):
        sample_start = time.perf_counter()

        # Layer 1
        r1 = l1.detect(text)
        if r1.is_injection:
            predictions[i] = 1
            detected_by_layer[i] = 1
            latencies[i] = (time.perf_counter() - sample_start) * 1000
            continue

        # Layer 2
        r2 = l2.detect(text)
        if r2.is_injection:
            predictions[i] = 1
            detected_by_layer[i] = 2
            latencies[i] = (time.perf_counter() - sample_start) * 1000
            continue

        # Layer 3
        r3 = l3.detect(text)
        if r3.is_injection:
            predictions[i] = 1
            detected_by_layer[i] = 3
            latencies[i] = (time.perf_counter() - sample_start) * 1000
            continue

        latencies[i] = (time.perf_counter() - sample_start) * 1000

        if (i + 1) % 500 == 0:
            elapsed = time.perf_counter() - t_start
            rate = (i + 1) / elapsed
            print(f"    {i+1}/{n} ({(i+1)/n*100:.0f}%) - {rate:.1f} samples/s")

    total_time = time.perf_counter() - t_start

    # Metrics
    if n_inject > 0 and n_benign > 0:
        tn, fp, fn, tp = confusion_matrix(labels, predictions, labels=[0, 1]).ravel()
    elif n_benign > 0:
        # All benign (NotInject case)
        tp, fn = 0, 0
        fp = int((predictions == 1).sum())
        tn = int((predictions == 0).sum())
    else:
        tp = int(((predictions == 1) & (labels == 1)).sum())
        fn = int(((predictions == 0) & (labels == 1)).sum())
        fp, tn = 0, 0

    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    f1 = f1_score(labels, predictions, pos_label=1, zero_division=0)
    precision = precision_score(labels, predictions, pos_label=1, zero_division=0)
    recall = recall_score(labels, predictions, pos_label=1, zero_division=0)

    # Over-defense accuracy (for NotInject: % of benign correctly classified)
    over_defense_acc = tn / n_benign if n_benign > 0 else None

    # Layer stats
    l1_det = int((detected_by_layer == 1).sum())
    l2_det = int((detected_by_layer == 2).sum())
    l3_det = int((detected_by_layer == 3).sum())

    # Latency (exclude first sample for warm stats)
    warm_lat = latencies[1:] if len(latencies) > 1 else latencies

    result = {
        "dataset": dataset_name,
        "total": n,
        "injection": n_inject,
        "benign": n_benign,
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "tn": int(tn),
        "f1": round(f1, 5),
        "precision": round(precision, 5),
        "recall": round(recall, 5),
        "fpr": round(fpr, 5),
        "over_defense_accuracy": (
            round(over_defense_acc, 5) if over_defense_acc is not None else None
        ),
        "layer_detections": {"l1": l1_det, "l2": l2_det, "l3": l3_det},
        "latency": {
            "mean_ms": round(float(warm_lat.mean()), 2),
            "median_ms": round(float(np.median(warm_lat)), 2),
            "p95_ms": round(float(np.percentile(warm_lat, 95)), 2),
        },
        "eval_seconds": round(total_time, 1),
    }

    # Print
    print(f"    F1={f1:.4f}  Prec={precision:.4f}  Recall={recall:.4f}  FPR={fpr:.4f}")
    if over_defense_acc is not None:
        print(
            f"    Over-defense accuracy: {over_defense_acc:.4f} "
            f"({tn}/{n_benign} benign correct)"
        )
    print(f"    TP={tp} FP={fp} FN={fn} TN={tn}")
    print(f"    Layers: L1={l1_det} L2={l2_det} L3={l3_det}")
    print(f"    Latency: mean={warm_lat.mean():.1f}ms  median={np.median(warm_lat):.1f}ms")
    print(f"    Time: {total_time:.1f}s")

    return result


def main():
    parser = argparse.ArgumentParser(description="Benchmark Gauntlet on public datasets")
    parser.add_argument("--no_wandb", action="store_true")
    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        choices=list(DATASET_LOADERS.keys()),
        help="Run single dataset only",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("Phase 8 Step 3: Gauntlet Benchmark on Public Datasets")
    print("=" * 70)
    print(f"  Thresholds: L2={L2_THRESHOLD}, L3={L3_THRESHOLD}")

    # Initialize layers once
    sys.path.insert(0, str(PROJECT_ROOT))
    from gauntlet.layers.rules import RulesDetector
    from gauntlet.layers.embeddings import EmbeddingsDetector
    from gauntlet.layers.slm_judge import SLMDetector

    print("\n[1] Initializing layers...")
    l1 = RulesDetector()
    l2 = EmbeddingsDetector(threshold=L2_THRESHOLD, mode="slm")
    l3 = SLMDetector(confidence_threshold=L3_THRESHOLD)

    print("  Warming up DeBERTa...")
    _ = l3.detect("warmup text")
    print("  All layers ready.")

    # Choose datasets
    if args.dataset:
        datasets_to_run = [args.dataset]
    else:
        datasets_to_run = list(DATASET_LOADERS.keys())

    # Load and evaluate
    print(f"\n[2] Loading and evaluating {len(datasets_to_run)} dataset(s)...")
    all_results = []

    for ds_key in datasets_to_run:
        print(f"\n  Loading {ds_key}...")
        try:
            texts, labels, name = DATASET_LOADERS[ds_key]()
            result = evaluate_dataset(texts, labels, name, l1, l2, l3)
            all_results.append(result)
        except Exception as e:
            print(f"  ERROR loading {ds_key}: {e}")
            import traceback

            traceback.print_exc()

    # Summary table
    print(f"\n{'=' * 70}")
    print("GAUNTLET v0.3.0 BENCHMARK RESULTS")
    print(f"{'=' * 70}")
    print(
        f"  {'Dataset':>25} {'N':>6} {'F1':>8} {'Prec':>8} {'Recall':>8} "
        f"{'FPR':>8} {'OD-Acc':>8}"
    )
    print(f"  {'-' * 75}")
    for r in all_results:
        od = (
            f"{r['over_defense_accuracy']:.4f}" if r["over_defense_accuracy"] is not None else "N/A"
        )
        print(
            f"  {r['dataset']:>25} {r['total']:>6} {r['f1']:>8.4f} "
            f"{r['precision']:>8.4f} {r['recall']:>8.4f} {r['fpr']:>8.4f} {od:>8}"
        )
    print(f"{'=' * 70}")

    # Save results
    output_path = Path(__file__).parent / "benchmark_results.json"
    output = {
        "model": "gauntlet-v0.3.0-slm",
        "thresholds": {"l2_bge": L2_THRESHOLD, "l3_deberta": L3_THRESHOLD},
        "results": all_results,
    }
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to: {output_path}")

    # WandB
    if not args.no_wandb:
        try:
            import wandb

            wandb.init(
                project="argus-slm-gauntlet",
                name="benchmark-public-datasets",
                config={"l2_threshold": L2_THRESHOLD, "l3_threshold": L3_THRESHOLD},
            )
            for r in all_results:
                prefix = r["dataset"].lower().replace("-", "_")
                wandb.log(
                    {
                        f"{prefix}_f1": r["f1"],
                        f"{prefix}_precision": r["precision"],
                        f"{prefix}_recall": r["recall"],
                        f"{prefix}_fpr": r["fpr"],
                    }
                )
            wandb.finish()
            print("WandB logging complete")
        except Exception as e:
            print(f"WandB logging failed: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

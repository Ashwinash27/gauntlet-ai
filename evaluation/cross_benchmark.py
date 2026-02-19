"""Cross-benchmark evaluation across internal known, holdout, and PINT datasets.

Runs Layer 1 only and Layer 1+2 on each dataset for generalization testing.

Run: python -m evaluation.cross_benchmark
"""

from __future__ import annotations

import json
import os
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).parent / "dataset"
RESULTS_PATH = Path(__file__).parent / "cross_benchmark_results.json"


@dataclass
class Metrics:
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0
    latencies_ms: list[float] = field(default_factory=list)

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def fpr(self) -> float:
        return self.fp / (self.fp + self.tn) if (self.fp + self.tn) else 0.0

    @property
    def accuracy(self) -> float:
        total = self.tp + self.fp + self.fn + self.tn
        return (self.tp + self.tn) / total if total else 0.0

    @property
    def avg_latency_ms(self) -> float:
        return statistics.mean(self.latencies_ms) if self.latencies_ms else 0.0

    @property
    def p95_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        sorted_l = sorted(self.latencies_ms)
        idx = int(len(sorted_l) * 0.95)
        return sorted_l[min(idx, len(sorted_l) - 1)]

    def to_dict(self) -> dict:
        return {
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
            "tn": self.tn,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "fpr": round(self.fpr, 4),
            "accuracy": round(self.accuracy, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
            "total_samples": self.tp + self.fp + self.fn + self.tn,
        }


def load_jsonl(path: Path) -> list[dict]:
    """Load a single JSONL file."""
    samples = []
    if not path.exists():
        print(f"  WARNING: {path} not found")
        return samples
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(json.loads(line))
    return samples


def run_benchmark(
    samples: list[dict], layers: list[int], label: str, threshold: float = 0.75
) -> Metrics:
    """Run benchmark on samples with given layer config."""
    from gauntlet import Gauntlet

    g = Gauntlet(embedding_threshold=threshold)
    metrics = Metrics()

    total = len(samples)
    for i, sample in enumerate(samples):
        text = sample["text"]
        expected = sample["is_injection"]

        start = time.perf_counter()
        try:
            result = g.detect(text, layers=layers)
            predicted = result.is_injection
        except Exception as e:
            print(f"  ERROR on sample {sample.get('id', i)}: {e}")
            predicted = False
        latency = (time.perf_counter() - start) * 1000

        metrics.latencies_ms.append(latency)

        if expected and predicted:
            metrics.tp += 1
        elif not expected and predicted:
            metrics.fp += 1
        elif expected and not predicted:
            metrics.fn += 1
        else:
            metrics.tn += 1

        if (i + 1) % 200 == 0 or (i + 1) == total:
            print(f"  [{label}] {i + 1}/{total}")

    return metrics


def main() -> None:
    print("=" * 60)
    print("Cross-Benchmark Evaluation")
    print("=" * 60)

    # Check OpenAI key for Layer 2
    has_openai = bool(os.environ.get("OPENAI_API_KEY"))
    print(f"OpenAI API key: {'found' if has_openai else 'NOT FOUND (Layer 2 will be skipped)'}")

    # Load datasets
    print("\nLoading datasets...")

    # 1. Internal known: 150 core malicious (in attack_phrases) + 1000 benign
    known_malicious = load_jsonl(DATA_DIR / "malicious_core.jsonl")
    benign = load_jsonl(DATA_DIR / "benign.jsonl")
    known_set = known_malicious + benign
    print(f"  Internal (known): {len(known_malicious)} malicious + {len(benign)} benign = {len(known_set)}")

    # 2. Internal holdout: 100 unseen malicious + 1000 benign
    holdout_malicious = load_jsonl(DATA_DIR / "malicious_holdout.jsonl")
    holdout_set = holdout_malicious + benign
    print(f"  Internal (holdout): {len(holdout_malicious)} malicious + {len(benign)} benign = {len(holdout_set)}")

    # 3. PINT external: all samples (mixed injection + benign)
    pint_samples = load_jsonl(DATA_DIR / "external" / "pint_samples.jsonl")
    pint_malicious = sum(1 for s in pint_samples if s["is_injection"])
    pint_benign = sum(1 for s in pint_samples if not s["is_injection"])
    print(f"  PINT external: {pint_malicious} malicious + {pint_benign} benign = {len(pint_samples)}")

    threshold = 0.75
    print(f"\nEmbedding threshold: {threshold}")

    datasets = [
        ("Internal (known)", known_set),
        ("Internal (holdout)", holdout_set),
        ("PINT external", pint_samples),
    ]

    layer_configs = [
        ("L1", [1]),
    ]
    if has_openai:
        layer_configs.append(("L1+2", [1, 2]))

    all_results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "embedding_threshold": threshold,
        "benchmarks": {},
    }

    results_table = []

    for ds_name, ds_samples in datasets:
        for config_name, layers in layer_configs:
            label = f"{ds_name} / {config_name}"
            print(f"\n{'—' * 40}")
            print(f"Running: {label} ({len(ds_samples)} samples, layers={layers})")
            print(f"{'—' * 40}")

            metrics = run_benchmark(ds_samples, layers, label, threshold=threshold)
            d = metrics.to_dict()

            all_results["benchmarks"][label] = d

            mal_count = metrics.tp + metrics.fn
            ben_count = metrics.fp + metrics.tn
            results_table.append({
                "benchmark": ds_name,
                "samples": f"{mal_count}m + {ben_count}b",
                "config": config_name,
                "precision": d["precision"],
                "recall": d["recall"],
                "f1": d["f1"],
                "fpr": d["fpr"],
                "avg_latency_ms": d["avg_latency_ms"],
            })

    # Print combined table
    print("\n" + "=" * 60)
    print("CROSS-BENCHMARK RESULTS")
    print("=" * 60)

    header = "| Benchmark | Samples | Config | Precision | Recall | F1 | FPR | Avg Latency |"
    sep =    "|-----------|---------|--------|-----------|--------|----|-----|-------------|"
    print(f"\n{header}")
    print(sep)
    for r in results_table:
        print(
            f"| {r['benchmark']} | {r['samples']} | {r['config']} | "
            f"{r['precision']:.2%} | {r['recall']:.2%} | {r['f1']:.2%} | "
            f"{r['fpr']:.2%} | {r['avg_latency_ms']:.1f}ms |"
        )

    # Save results
    with open(RESULTS_PATH, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to {RESULTS_PATH}")


if __name__ == "__main__":
    main()

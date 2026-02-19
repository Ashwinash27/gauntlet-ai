"""Run L1, L1+2, L1+2+3 benchmark on pint_test.jsonl (held-out test set).

Usage: PYTHONUNBUFFERED=1 python -m evaluation.run_pint_test_benchmark
"""
import json
import os
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

DATA_PATH = Path(__file__).parent / "dataset" / "external" / "pint_test.jsonl"
RESULTS_PATH = Path(__file__).parent / "pint_test_results.json"


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


def main():
    print("=" * 60)
    print("PINT Test Set Benchmark (post-regex-expansion)")
    print("=" * 60)

    # Check keys
    has_openai = bool(os.environ.get("OPENAI_API_KEY"))
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    print(f"OpenAI key: {'found' if has_openai else 'MISSING'}")
    print(f"Anthropic key: {'found' if has_anthropic else 'MISSING'}")

    if not has_openai or not has_anthropic:
        print("ERROR: Both OPENAI_API_KEY and ANTHROPIC_API_KEY required")
        sys.exit(1)

    # Load dataset
    samples = []
    with open(DATA_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(json.loads(line))

    mal = sum(1 for s in samples if s["is_injection"])
    ben = sum(1 for s in samples if not s["is_injection"])
    print(f"Dataset: {mal} malicious + {ben} benign = {len(samples)} total")

    from gauntlet import Gauntlet

    configs = [
        ("L1", [1]),
        ("L1+2", [1, 2]),
        ("L1+2+3", [1, 2, 3]),
    ]

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset": "pint_test.jsonl",
        "embedding_threshold": 0.75,
        "samples": {"malicious": mal, "benign": ben, "total": len(samples)},
    }

    for config_name, layers in configs:
        print(f"\n{'—' * 50}")
        print(f"Running {config_name} (layers={layers})")
        print(f"{'—' * 50}")

        g = Gauntlet(embedding_threshold=0.75, llm_timeout=30.0)
        metrics = Metrics()
        total = len(samples)
        false_negatives = []

        for i, sample in enumerate(samples):
            text = sample["text"]
            expected = sample["is_injection"]

            start = time.perf_counter()
            try:
                result = g.detect(text, layers=layers)
                predicted = result.is_injection
            except Exception as e:
                print(f"  ERROR on {sample.get('id', i)}: {e}")
                predicted = False
            latency = (time.perf_counter() - start) * 1000
            metrics.latencies_ms.append(latency)

            if expected and predicted:
                metrics.tp += 1
            elif not expected and predicted:
                metrics.fp += 1
            elif expected and not predicted:
                metrics.fn += 1
                false_negatives.append(sample.get("id", f"idx-{i}"))
            else:
                metrics.tn += 1

            step = 25 if 3 in layers else 100
            if (i + 1) % step == 0 or (i + 1) == total:
                print(
                    f"  [{config_name}] {i+1}/{total} "
                    f"TP={metrics.tp} FP={metrics.fp} FN={metrics.fn} TN={metrics.tn} "
                    f"(last: {latency:.0f}ms)"
                )

        d = metrics.to_dict()
        d["false_negative_ids"] = false_negatives
        results[config_name] = d

        print(f"\n  {config_name} Results:")
        print(f"    Precision: {d['precision']:.2%}")
        print(f"    Recall:    {d['recall']:.2%}")
        print(f"    F1:        {d['f1']:.2%}")
        print(f"    FPR:       {d['fpr']:.2%}")
        print(f"    Avg lat:   {d['avg_latency_ms']:.1f}ms")
        print(f"    P95 lat:   {d['p95_latency_ms']:.1f}ms")

    # Summary table
    print("\n" + "=" * 60)
    print("SUMMARY — PINT Test Set (held-out)")
    print("=" * 60)
    header = "| Config | Precision | Recall | F1     | FPR    | Avg Latency |"
    sep    = "|--------|-----------|--------|--------|--------|-------------|"
    print(header)
    print(sep)
    for config_name, _ in configs:
        d = results[config_name]
        print(
            f"| {config_name:<6} | {d['precision']:.2%}    | {d['recall']:.2%} | "
            f"{d['f1']:.2%} | {d['fpr']:.2%} | {d['avg_latency_ms']:.1f}ms        |"
        )

    # Save
    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {RESULTS_PATH}")


if __name__ == "__main__":
    main()

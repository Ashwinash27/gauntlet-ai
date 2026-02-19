"""Benchmark gauntlet detection across layer configurations.

Measures Precision, Recall, F1, FPR, Accuracy, and latency metrics
on both the core set (150 malicious + 1,000 benign) and the full set
(all ~4,500 samples).

Run: python -m evaluation.benchmark
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
RESULTS_PATH = Path(__file__).parent / "results.json"


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


def load_dataset(filenames: list[str]) -> list[dict]:
    """Load JSONL dataset files."""
    samples = []
    for filename in filenames:
        path = DATA_DIR / filename
        if not path.exists():
            print(f"  WARNING: {path.name} not found, skipping")
            continue
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                samples.append(json.loads(line))
    return samples


def detect_available_layers() -> list[int]:
    """Detect which layers can run based on available keys."""
    layers = [1]
    openai_key = os.environ.get("OPENAI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if openai_key:
        try:
            import numpy  # noqa: F401
            import openai  # noqa: F401
            layers.append(2)
        except ImportError:
            pass
    if anthropic_key:
        try:
            import anthropic  # noqa: F401
            layers.append(3)
        except ImportError:
            pass
    return layers


def run_benchmark(
    samples: list[dict], layers: list[int], label: str
) -> tuple[Metrics, dict[str, Metrics]]:
    """Run benchmark on samples with given layer config."""
    from gauntlet import Gauntlet

    g = Gauntlet()
    overall = Metrics()
    by_category: dict[str, Metrics] = {}

    total = len(samples)
    for i, sample in enumerate(samples):
        text = sample["text"]
        expected = sample["is_injection"]
        category = sample.get("category", "unknown")

        if category not in by_category:
            by_category[category] = Metrics()

        start = time.perf_counter()
        try:
            result = g.detect(text, layers=layers)
            predicted = result.is_injection
        except Exception as e:
            print(f"  ERROR on sample {sample.get('id', i)}: {e}")
            predicted = False
        latency = (time.perf_counter() - start) * 1000

        overall.latencies_ms.append(latency)
        by_category[category].latencies_ms.append(latency)

        if expected and predicted:
            overall.tp += 1
            by_category[category].tp += 1
        elif not expected and predicted:
            overall.fp += 1
            by_category[category].fp += 1
        elif expected and not predicted:
            overall.fn += 1
            by_category[category].fn += 1
        else:
            overall.tn += 1
            by_category[category].tn += 1

        if (i + 1) % 500 == 0 or (i + 1) == total:
            print(f"  [{label}] {i + 1}/{total} processed...")

    return overall, by_category


def format_markdown_table(
    configs: dict[str, tuple[Metrics, dict[str, Metrics]]]
) -> str:
    """Generate markdown results table."""
    lines = []

    # Overall metrics
    lines.append("## Overall Metrics\n")
    lines.append(
        "| Config | Samples | Precision | Recall | F1 | FPR | Accuracy | Avg Latency | P95 Latency |"
    )
    lines.append(
        "|--------|---------|-----------|--------|----|-----|----------|-------------|-------------|"
    )
    for config_name, (overall, _) in configs.items():
        d = overall.to_dict()
        lines.append(
            f"| {config_name} | {d['total_samples']} | "
            f"{d['precision']:.2%} | {d['recall']:.2%} | {d['f1']:.2%} | "
            f"{d['fpr']:.2%} | {d['accuracy']:.2%} | "
            f"{d['avg_latency_ms']:.1f}ms | {d['p95_latency_ms']:.1f}ms |"
        )
    lines.append("")

    # Per-category breakdown (from first config that has categories)
    for config_name, (_, by_cat) in configs.items():
        lines.append(f"## Per-Category Breakdown ({config_name})\n")
        lines.append("| Category | Samples | Precision | Recall | F1 |")
        lines.append("|----------|---------|-----------|--------|----|")
        for cat in sorted(by_cat):
            m = by_cat[cat]
            d = m.to_dict()
            lines.append(
                f"| {cat} | {d['total_samples']} | "
                f"{d['precision']:.2%} | {d['recall']:.2%} | {d['f1']:.2%} |"
            )
        lines.append("")
        break  # Only show breakdown for the first config

    return "\n".join(lines)


def main() -> None:
    print("=" * 60)
    print("Gauntlet Benchmark")
    print("=" * 60)

    # Detect available layers
    available = detect_available_layers()
    layer_names = {1: "Rules", 2: "Embeddings", 3: "LLM Judge"}
    print(f"\nAvailable layers: {[f'{l} ({layer_names[l]})' for l in available]}")

    # Build layer configs to test
    configs_to_run: list[tuple[str, list[int]]] = [("Layer 1 only", [1])]
    if 2 in available:
        configs_to_run.append(("Layers 1+2", [1, 2]))
    if 3 in available:
        configs_to_run.append(("Layers 1+2+3", [1, 2, 3]))

    # Load datasets
    print("\nLoading datasets...")
    core_malicious = load_dataset(["malicious_core.jsonl"])
    benign = load_dataset(["benign.jsonl"])
    public_malicious = load_dataset(["malicious_public.jsonl"])
    generated_malicious = load_dataset(["malicious_generated.jsonl"])

    core_set = core_malicious + benign
    full_set = core_malicious + public_malicious + generated_malicious + benign

    print(f"  Core set: {len(core_malicious)} malicious + {len(benign)} benign = {len(core_set)}")
    print(
        f"  Full set: {len(core_malicious) + len(public_malicious) + len(generated_malicious)} "
        f"malicious + {len(benign)} benign = {len(full_set)}"
    )

    all_results: dict = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "available_layers": available,
        "dataset_sizes": {
            "core_malicious": len(core_malicious),
            "public_malicious": len(public_malicious),
            "generated_malicious": len(generated_malicious),
            "benign": len(benign),
        },
        "configs": {},
    }

    # Run benchmarks
    for config_name, layers in configs_to_run:
        print(f"\n{'—' * 40}")
        print(f"Running: {config_name} (layers={layers})")
        print(f"{'—' * 40}")

        config_results: dict = {}

        # Core set
        print(f"\n  Core set ({len(core_set)} samples)...")
        core_overall, core_by_cat = run_benchmark(core_set, layers, f"{config_name}/core")
        config_results["core_set"] = {
            "overall": core_overall.to_dict(),
            "by_category": {k: v.to_dict() for k, v in core_by_cat.items()},
        }

        # Full set
        if len(full_set) > len(core_set):
            print(f"\n  Full set ({len(full_set)} samples)...")
            full_overall, full_by_cat = run_benchmark(
                full_set, layers, f"{config_name}/full"
            )
            config_results["full_set"] = {
                "overall": full_overall.to_dict(),
                "by_category": {k: v.to_dict() for k, v in full_by_cat.items()},
            }

        all_results["configs"][config_name] = config_results

    # Print markdown summary
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    # Build markdown from core set results
    core_configs = {}
    for config_name in all_results["configs"]:
        core_data = all_results["configs"][config_name]["core_set"]
        overall = Metrics(**{
            k: core_data["overall"][k]
            for k in ["tp", "fp", "fn", "tn"]
        })
        by_cat = {}
        for cat, cat_data in core_data["by_category"].items():
            by_cat[cat] = Metrics(**{k: cat_data[k] for k in ["tp", "fp", "fn", "tn"]})
        core_configs[config_name + " (core)"] = (overall, by_cat)

    full_configs = {}
    for config_name in all_results["configs"]:
        full_data = all_results["configs"][config_name].get("full_set")
        if full_data:
            overall = Metrics(**{
                k: full_data["overall"][k]
                for k in ["tp", "fp", "fn", "tn"]
            })
            by_cat = {}
            for cat, cat_data in full_data["by_category"].items():
                by_cat[cat] = Metrics(**{k: cat_data[k] for k in ["tp", "fp", "fn", "tn"]})
            full_configs[config_name + " (full)"] = (overall, by_cat)

    all_table_configs = {**core_configs, **full_configs}
    markdown = format_markdown_table(all_table_configs)
    print("\n" + markdown)

    # Save results
    with open(RESULTS_PATH, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to {RESULTS_PATH}")


if __name__ == "__main__":
    main()

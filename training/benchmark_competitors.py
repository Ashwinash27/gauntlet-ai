"""Phase 8: Benchmark competitor models on the same public datasets.

Runs ProtectAI DeBERTa-v3-base and Meta Prompt Guard 2 (86M) on:
1. NotInject (339 samples, all benign)
2. ProtectAI Validation (3,227 samples, mixed)

Usage:
    python training/benchmark_competitors.py
    python training/benchmark_competitors.py --model protectai
    python training/benchmark_competitors.py --model promptguard
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import (
    f1_score,
    precision_score,
    recall_score,
    confusion_matrix,
)
from transformers import AutoModelForSequenceClassification, AutoTokenizer


PROJECT_ROOT = Path(__file__).parent.parent
HF_CACHE = PROJECT_ROOT / ".hf_cache"


# ---------------------------------------------------------------------------
# Dataset loaders (same as benchmark_gauntlet.py)
# ---------------------------------------------------------------------------

def load_notinject() -> tuple[list[str], np.ndarray, str]:
    from datasets import load_dataset
    ds = load_dataset("leolee99/NotInject")
    texts, labels = [], []
    for split_name in ["NotInject_one", "NotInject_two", "NotInject_three"]:
        if split_name in ds:
            for row in ds[split_name]:
                texts.append(row["prompt"])
                labels.append(0)
    return texts, np.array(labels, dtype=np.int32), "NotInject"


def load_protectai_validation() -> tuple[list[str], np.ndarray, str]:
    from datasets import load_dataset
    ds = load_dataset("protectai/prompt-injection-validation")
    texts, labels = [], []
    for split_name in ds:
        for row in ds[split_name]:
            texts.append(row["text"])
            labels.append(int(row["label"]))
    return texts, np.array(labels, dtype=np.int32), "ProtectAI-Validation"


# ---------------------------------------------------------------------------
# Model runners
# ---------------------------------------------------------------------------

class CompetitorModel:
    def __init__(self, name: str, model_id: str, injection_label_id: int, max_length: int = 512):
        self.name = name
        self.model_id = model_id
        self.injection_label_id = injection_label_id
        self.max_length = max_length
        self.model = None
        self.tokenizer = None
        self.device = None

    def load(self):
        print(f"  Loading {self.name} from {self.model_id}...")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_id, cache_dir=str(HF_CACHE)
        )
        self.model = AutoModelForSequenceClassification.from_pretrained(
            self.model_id, cache_dir=str(HF_CACHE)
        )
        self.model.eval()
        self.model.to(self.device)

        param_count = sum(p.numel() for p in self.model.parameters())
        print(f"  Loaded: {param_count/1e6:.1f}M params on {self.device}")

    def predict_batch(self, texts: list[str]) -> tuple[np.ndarray, np.ndarray]:
        """Run inference on a batch. Returns (predictions, confidences)."""
        inputs = self.tokenizer(
            texts,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=self.max_length,
        )
        # Remove token_type_ids if present (DeBERTa-v3 doesn't need them)
        inputs.pop("token_type_ids", None)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.inference_mode():
            logits = self.model(**inputs).logits
            probs = torch.nn.functional.softmax(logits, dim=-1)
            injection_probs = probs[:, self.injection_label_id].cpu().numpy()
            preds = (injection_probs >= 0.5).astype(np.int32)

        return preds, injection_probs


def evaluate_model(
    model: CompetitorModel,
    texts: list[str],
    labels: np.ndarray,
    dataset_name: str,
    batch_size: int = 32,
) -> dict:
    """Evaluate a competitor model on a dataset."""

    n = len(texts)
    n_inject = int((labels == 1).sum())
    n_benign = int((labels == 0).sum())

    print(f"\n  [{model.name}] on [{dataset_name}] — {n} samples "
          f"({n_inject} inj, {n_benign} ben)")

    predictions = np.zeros(n, dtype=np.int32)
    confidences = np.zeros(n, dtype=np.float64)
    latencies = []

    t_start = time.perf_counter()

    for start in range(0, n, batch_size):
        end = min(start + batch_size, n)
        batch_texts = texts[start:end]

        batch_start = time.perf_counter()
        preds, confs = model.predict_batch(batch_texts)
        batch_time = (time.perf_counter() - batch_start) * 1000

        predictions[start:end] = preds
        confidences[start:end] = confs
        latencies.append(batch_time / len(batch_texts))  # per-sample avg

        if (end) % 500 < batch_size:
            elapsed = time.perf_counter() - t_start
            rate = end / elapsed
            print(f"    {end}/{n} ({end/n*100:.0f}%) - {rate:.1f} samples/s")

    total_time = time.perf_counter() - t_start

    # Metrics
    if n_inject > 0 and n_benign > 0:
        tn, fp, fn, tp = confusion_matrix(labels, predictions, labels=[0, 1]).ravel()
    elif n_benign > 0:
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
    over_defense_acc = tn / n_benign if n_benign > 0 else None

    lat_arr = np.array(latencies)

    result = {
        "model": model.name,
        "dataset": dataset_name,
        "total": n, "injection": n_inject, "benign": n_benign,
        "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
        "f1": round(f1, 5),
        "precision": round(precision, 5),
        "recall": round(recall, 5),
        "fpr": round(fpr, 5),
        "over_defense_accuracy": round(over_defense_acc, 5) if over_defense_acc is not None else None,
        "latency_mean_ms": round(float(lat_arr.mean()), 2),
        "eval_seconds": round(total_time, 1),
    }

    print(f"    F1={f1:.4f}  Prec={precision:.4f}  Recall={recall:.4f}  FPR={fpr:.4f}")
    if over_defense_acc is not None:
        print(f"    Over-defense accuracy: {over_defense_acc:.4f} ({tn}/{n_benign} correct)")
    print(f"    TP={tp} FP={fp} FN={fn} TN={tn}")
    print(f"    Latency: {lat_arr.mean():.1f}ms/sample | Total: {total_time:.1f}s")

    return result


def main():
    parser = argparse.ArgumentParser(description="Benchmark competitor models")
    parser.add_argument("--model", type=str, default=None,
                        choices=["protectai", "promptguard", "deepset"],
                        help="Run single model only")
    args = parser.parse_args()

    print("=" * 70)
    print("Phase 8: Competitor Model Benchmark")
    print("=" * 70)

    # Define models
    models_config = {
        "protectai": CompetitorModel(
            name="ProtectAI-v2",
            model_id="protectai/deberta-v3-base-prompt-injection-v2",
            injection_label_id=1,  # 0=SAFE, 1=INJECTION
            max_length=512,
        ),
        "promptguard": CompetitorModel(
            name="Meta-PromptGuard2-86M",
            model_id="meta-llama/Llama-Prompt-Guard-2-86M",
            injection_label_id=1,  # 0=BENIGN, 1=MALICIOUS
            max_length=512,
        ),
        "deepset": CompetitorModel(
            name="deepset-v3-base",
            model_id="deepset/deberta-v3-base-injection",
            injection_label_id=1,  # 0=SAFE, 1=INJECTION
            max_length=512,
        ),
    }

    if args.model:
        models_to_run = {args.model: models_config[args.model]}
    else:
        models_to_run = models_config

    # Load datasets once
    print("\n[1] Loading datasets...")
    datasets = {}
    for loader_name, loader_fn in [("NotInject", load_notinject),
                                     ("ProtectAI-Validation", load_protectai_validation)]:
        try:
            texts, labels, name = loader_fn()
            datasets[name] = (texts, labels)
            print(f"  {name}: {len(texts)} samples")
        except Exception as e:
            print(f"  ERROR loading {loader_name}: {e}")

    # Run benchmarks
    print("\n[2] Running benchmarks...")
    all_results = []

    for model_key, model in models_to_run.items():
        print(f"\n{'=' * 50}")
        print(f"  MODEL: {model.name}")
        print(f"{'=' * 50}")

        try:
            model.load()
        except Exception as e:
            print(f"  ERROR loading model {model.name}: {e}")
            import traceback
            traceback.print_exc()
            continue

        for ds_name, (texts, labels) in datasets.items():
            try:
                result = evaluate_model(model, texts, labels, ds_name)
                all_results.append(result)
            except Exception as e:
                print(f"  ERROR evaluating {model.name} on {ds_name}: {e}")
                import traceback
                traceback.print_exc()

        # Free GPU memory before loading next model
        model.model = None
        model.tokenizer = None
        torch.cuda.empty_cache()

    # Load Gauntlet results for comparison
    gauntlet_results_path = Path(__file__).parent / "benchmark_results.json"
    gauntlet_results = []
    if gauntlet_results_path.exists():
        with open(gauntlet_results_path) as f:
            data = json.load(f)
            for r in data.get("results", []):
                gauntlet_results.append({
                    "model": "Gauntlet-v0.3.0",
                    "dataset": r["dataset"],
                    "f1": r["f1"],
                    "precision": r["precision"],
                    "recall": r["recall"],
                    "fpr": r["fpr"],
                    "over_defense_accuracy": r.get("over_defense_accuracy"),
                })

    # Comparison table
    print(f"\n{'=' * 90}")
    print("COMPARISON TABLE")
    print(f"{'=' * 90}")
    print(f"  {'Model':>25} {'Dataset':>25} {'F1':>8} {'Prec':>8} "
          f"{'Recall':>8} {'FPR':>8} {'OD-Acc':>8}")
    print(f"  {'-' * 85}")

    combined = gauntlet_results + all_results
    # Sort by dataset then model
    combined.sort(key=lambda r: (r["dataset"], r["model"]))

    for r in combined:
        od = f"{r['over_defense_accuracy']:.4f}" if r.get('over_defense_accuracy') is not None else "N/A"
        print(f"  {r['model']:>25} {r['dataset']:>25} {r['f1']:>8.4f} "
              f"{r['precision']:>8.4f} {r['recall']:>8.4f} {r['fpr']:>8.4f} {od:>8}")

    print(f"{'=' * 90}")

    # Save
    output_path = Path(__file__).parent / "competitor_benchmark_results.json"
    with open(output_path, "w") as f:
        json.dump({"results": all_results, "gauntlet_results": gauntlet_results}, f, indent=2)
    print(f"\nResults saved to: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

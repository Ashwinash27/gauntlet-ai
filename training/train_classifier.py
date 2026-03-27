"""Fine-tune DeBERTa-v3-small for prompt injection detection.

Phase 2 of SLM Gauntlet v0.3.0.

Usage:
    python training/train_classifier.py
    python training/train_classifier.py --batch_size 8 --grad_accum 2   # if OOM on 6GB GPU
    python training/train_classifier.py --no_wandb                       # disable WandB logging
"""

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch
import wandb
from datasets import Dataset
from sklearn.metrics import f1_score, precision_score, recall_score
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    EarlyStoppingCallback,
    Trainer,
    TrainingArguments,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODEL_NAME = "microsoft/deberta-v3-small"
MAX_LENGTH = 256
SEED = 42

SPLITS_DIR = Path(__file__).parent / "splits"
CHECKPOINT_DIR = Path(__file__).parent / "checkpoints" / "deberta-v3-small-injection"
HF_CACHE_DIR = Path(__file__).parent.parent / ".hf_cache"

LABEL2ID = {"benign": 0, "injection": 1}
ID2LABEL = {0: "benign", 1: "injection"}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_jsonl(path: Path) -> list[dict]:
    """Load a JSONL file into a list of dicts."""
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_splits() -> tuple[Dataset, Dataset]:
    """Load train and validation splits as HuggingFace Datasets."""
    train_records = load_jsonl(SPLITS_DIR / "train.jsonl")
    val_records = load_jsonl(SPLITS_DIR / "val.jsonl")

    print(f"Loaded {len(train_records)} train, {len(val_records)} val samples")

    # Validate labels are binary 0/1
    for split_name, records in [("train", train_records), ("val", val_records)]:
        labels = {r["label"] for r in records}
        assert labels <= {0, 1}, f"{split_name} has unexpected labels: {labels}"

    train_ds = Dataset.from_list(train_records)
    val_ds = Dataset.from_list(val_records)

    return train_ds, val_ds


# ---------------------------------------------------------------------------
# Class weights
# ---------------------------------------------------------------------------


def compute_class_weights(train_ds: Dataset) -> torch.Tensor:
    """Compute inverse-frequency class weights from training labels.

    Formula: weight_c = N / (num_classes * count_c)
    This gives higher weight to the minority class (injection at 38%).
    """
    labels = np.array(train_ds["label"])
    num_samples = len(labels)
    num_classes = 2

    counts = np.bincount(labels, minlength=num_classes)
    weights = num_samples / (num_classes * counts)

    # Normalize so weights sum to num_classes (keeps loss scale stable)
    weights = weights / weights.sum() * num_classes

    print(
        f"Class distribution: benign={counts[0]} ({counts[0]/num_samples:.1%}), "
        f"injection={counts[1]} ({counts[1]/num_samples:.1%})"
    )
    print(f"Class weights: benign={weights[0]:.4f}, injection={weights[1]:.4f}")

    return torch.tensor(weights, dtype=torch.float32)


# ---------------------------------------------------------------------------
# Tokenization
# ---------------------------------------------------------------------------


def tokenize_dataset(dataset: Dataset, tokenizer: AutoTokenizer) -> Dataset:
    """Tokenize text field and keep labels."""

    def tokenize_fn(batch):
        return tokenizer(
            batch["text"],
            truncation=True,
            padding="max_length",
            max_length=MAX_LENGTH,
            # DeBERTa-v3 ONNX gotcha: token_type_ids can cause issues.
            # For binary classification, they're all zeros anyway.
            return_token_type_ids=False,
        )

    tokenized = dataset.map(
        tokenize_fn,
        batched=True,
        batch_size=1000,
        remove_columns=[c for c in dataset.column_names if c not in ("label",)],
        desc="Tokenizing",
    )

    # Rename label -> labels (HF Trainer convention)
    tokenized = tokenized.rename_column("label", "labels")
    tokenized.set_format("torch")

    return tokenized


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def make_compute_metrics():
    """Return a compute_metrics function for the Trainer."""

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        preds = np.argmax(logits, axis=-1)

        f1 = f1_score(labels, preds, average="binary", pos_label=1)
        precision = precision_score(labels, preds, average="binary", pos_label=1)
        recall = recall_score(labels, preds, average="binary", pos_label=1)

        # Also compute benign-class metrics for FPR monitoring
        # FPR = FP / (FP + TN) = 1 - specificity = 1 - recall(benign)
        recall_benign = recall_score(labels, preds, average="binary", pos_label=0)
        fpr = 1.0 - recall_benign

        return {
            "f1": f1,
            "precision": precision,
            "recall": recall,
            "fpr": fpr,
        }

    return compute_metrics


# ---------------------------------------------------------------------------
# Custom Trainer with class-weighted loss
# ---------------------------------------------------------------------------


class WeightedTrainer(Trainer):
    """Trainer subclass that uses class-weighted CrossEntropyLoss."""

    def __init__(self, class_weights: torch.Tensor, **kwargs):
        super().__init__(**kwargs)
        self.class_weights = class_weights

    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        labels = inputs.get("labels")
        # Pass inputs WITHOUT labels so model doesn't compute its own
        # unweighted loss (avoids double-backward with gradient checkpointing)
        forward_inputs = {k: v for k, v in inputs.items() if k != "labels"}
        outputs = model(**forward_inputs)
        logits = outputs.logits

        loss_fn = torch.nn.CrossEntropyLoss(weight=self.class_weights.to(logits.device))
        loss = loss_fn(logits, labels)

        return (loss, outputs) if return_outputs else loss


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fine-tune DeBERTa-v3-small for injection detection"
    )
    parser.add_argument("--batch_size", type=int, default=16, help="Per-device train batch size")
    parser.add_argument(
        "--eval_batch_size", type=int, default=32, help="Per-device eval batch size"
    )
    parser.add_argument("--grad_accum", type=int, default=1, help="Gradient accumulation steps")
    parser.add_argument("--epochs", type=int, default=4, help="Number of training epochs")
    parser.add_argument("--lr", type=float, default=2e-5, help="Learning rate")
    parser.add_argument("--warmup_ratio", type=float, default=0.1, help="Warmup ratio")
    parser.add_argument("--weight_decay", type=float, default=0.01, help="Weight decay")
    parser.add_argument("--no_wandb", action="store_true", help="Disable WandB logging")
    parser.add_argument(
        "--fp16", action="store_true", default=True, help="Use FP16 mixed precision"
    )
    parser.add_argument("--no_fp16", action="store_true", help="Disable FP16")
    parser.add_argument("--patience", type=int, default=2, help="Early stopping patience (epochs)")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.no_fp16:
        args.fp16 = False

    print("=" * 60)
    print("Phase 2: Fine-tune DeBERTa-v3-small")
    print("=" * 60)

    # -- Device info --
    if torch.cuda.is_available():
        gpu = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"GPU: {gpu} ({vram:.1f}GB)")
    else:
        print("WARNING: No GPU detected — training will be very slow")

    # -- Reproducibility --
    torch.manual_seed(SEED)
    np.random.seed(SEED)

    # -- Load data --
    print("\n[1/5] Loading data...")
    train_ds, val_ds = load_splits()

    # -- Class weights --
    print("\n[2/5] Computing class weights...")
    class_weights = compute_class_weights(train_ds)

    # -- Tokenizer + Model --
    print(f"\n[3/5] Loading model: {MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME,
        cache_dir=str(HF_CACHE_DIR),
        # DeBERTa-v3 fast tokenizer has a bug in transformers >=4.57
        # with convert_slow_tokenizer. Use slow tokenizer (SentencePiece).
        use_fast=False,
    )
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=2,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        cache_dir=str(HF_CACHE_DIR),
    )

    # NOTE: gradient_checkpointing conflicts with custom compute_loss
    # (double-backward error). Disabled — fp16 + batch 16 fits in 6GB.
    # If OOM, reduce batch_size to 8 with --batch_size 8 --grad_accum 2.

    param_count = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Parameters: {param_count / 1e6:.1f}M total, {trainable / 1e6:.1f}M trainable")

    # -- Tokenize --
    print("\n[4/5] Tokenizing datasets...")
    train_tokenized = tokenize_dataset(train_ds, tokenizer)
    val_tokenized = tokenize_dataset(val_ds, tokenizer)

    print(f"Train: {len(train_tokenized)} samples")
    print(f"Val:   {len(val_tokenized)} samples")

    # -- WandB --
    report_to = "none"
    if not args.no_wandb:
        report_to = "wandb"
        wandb.init(
            project="argus-slm-gauntlet",
            name=f"deberta-v3-small-injection-bs{args.batch_size}-lr{args.lr}",
            config={
                "model": MODEL_NAME,
                "max_length": MAX_LENGTH,
                "batch_size": args.batch_size,
                "grad_accum": args.grad_accum,
                "effective_batch_size": args.batch_size * args.grad_accum,
                "epochs": args.epochs,
                "lr": args.lr,
                "warmup_ratio": args.warmup_ratio,
                "weight_decay": args.weight_decay,
                "fp16": args.fp16,
                "class_weights": class_weights.tolist(),
                "train_samples": len(train_tokenized),
                "val_samples": len(val_tokenized),
                "seed": SEED,
            },
        )

    # -- Training args --
    output_dir = str(CHECKPOINT_DIR)

    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.eval_batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        warmup_ratio=args.warmup_ratio,
        weight_decay=args.weight_decay,
        fp16=args.fp16,
        # Evaluation & saving
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        save_total_limit=2,  # Keep only best + latest to save disk
        # Logging
        logging_strategy="steps",
        logging_steps=50,
        report_to=report_to,
        # Reproducibility
        seed=SEED,
        data_seed=SEED,
        # Performance
        dataloader_num_workers=2,
        dataloader_pin_memory=True,
        # Disable push to hub
        push_to_hub=False,
    )

    # -- Trainer --
    print("\n[5/5] Starting training...")
    print(
        f"  Batch size: {args.batch_size} (x{args.grad_accum} accum = {args.batch_size * args.grad_accum} effective)"
    )
    print(f"  Learning rate: {args.lr}")
    print(f"  Epochs: {args.epochs}")
    print(f"  FP16: {args.fp16}")
    print(f"  WandB: {report_to != 'none'}")

    trainer = WeightedTrainer(
        class_weights=class_weights,
        model=model,
        args=training_args,
        train_dataset=train_tokenized,
        eval_dataset=val_tokenized,
        processing_class=tokenizer,
        compute_metrics=make_compute_metrics(),
        callbacks=[EarlyStoppingCallback(early_stopping_patience=args.patience)],
    )

    # -- Train --
    train_result = trainer.train()

    # -- Save best model --
    best_dir = CHECKPOINT_DIR / "best"
    best_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(best_dir))
    tokenizer.save_pretrained(str(best_dir))
    print(f"\nBest model saved to: {best_dir}")

    # -- Final evaluation on val set --
    print("\n" + "=" * 60)
    print("Final Validation Results")
    print("=" * 60)

    eval_results = trainer.evaluate()

    for key, value in sorted(eval_results.items()):
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")

    # -- Save results to JSON --
    results_path = CHECKPOINT_DIR / "training_results.json"
    results = {
        "model": MODEL_NAME,
        "hyperparameters": {
            "batch_size": args.batch_size,
            "effective_batch_size": args.batch_size * args.grad_accum,
            "epochs": args.epochs,
            "lr": args.lr,
            "warmup_ratio": args.warmup_ratio,
            "weight_decay": args.weight_decay,
            "fp16": args.fp16,
            "max_length": MAX_LENGTH,
            "class_weights": class_weights.tolist(),
        },
        "train_metrics": {
            "train_loss": train_result.metrics.get("train_loss"),
            "train_runtime": train_result.metrics.get("train_runtime"),
            "train_samples_per_second": train_result.metrics.get("train_samples_per_second"),
        },
        "eval_metrics": {
            k: round(v, 6) if isinstance(v, float) else v for k, v in eval_results.items()
        },
        "data": {
            "train_samples": len(train_tokenized),
            "val_samples": len(val_tokenized),
        },
    }

    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {results_path}")

    # -- Check success criteria --
    val_f1 = eval_results.get("eval_f1", 0)
    val_fpr = eval_results.get("eval_fpr", 1)
    train_loss = train_result.metrics.get("train_loss", 0)

    print("\n" + "=" * 60)
    print("Success Criteria Check")
    print("=" * 60)

    passed = True
    if val_f1 >= 0.93:
        print(f"  ✓ Val F1 {val_f1:.4f} >= 0.93")
    else:
        print(f"  ✗ Val F1 {val_f1:.4f} < 0.93 — consider Optuna hyperparameter search")
        passed = False

    if val_fpr <= 0.015:
        print(f"  ✓ Val FPR {val_fpr:.4f} <= 1.5%")
    else:
        print(f"  ⚠ Val FPR {val_fpr:.4f} > 1.5% — may need threshold tuning in Phase 8")

    print(
        f"\n{'PASSED' if passed else 'NEEDS OPTIMIZATION'}: Phase 2 {'complete' if passed else 'may need Optuna tuning'}"
    )

    # -- Finish WandB --
    if not args.no_wandb and wandb.run is not None:
        wandb.log(
            {
                "final/val_f1": val_f1,
                "final/val_fpr": val_fpr,
                "final/val_precision": eval_results.get("eval_precision", 0),
                "final/val_recall": eval_results.get("eval_recall", 0),
                "phase2_passed": passed,
            }
        )
        wandb.finish()

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

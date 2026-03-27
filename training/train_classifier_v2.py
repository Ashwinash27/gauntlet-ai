"""Round 1: Fine-tune DeBERTa-v3-base on v2 data (with hard negatives).

Changes from v1 (train_classifier.py):
- Model: DeBERTa-v3-base (86M backbone, 184M total) instead of small (44M)
- Data: splits_v2/ with 5,500 hard negative benign samples added
- Hyperparams: PIGuard-aligned (3 epochs, batch 16)
- Monitors FPR alongside F1 during training

Usage:
    python training/train_classifier_v2.py
    python training/train_classifier_v2.py --batch_size 8 --grad_accum 2   # if OOM
    python training/train_classifier_v2.py --no_wandb
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
# Constants — changed from v1
# ---------------------------------------------------------------------------

MODEL_NAME = "microsoft/deberta-v3-base"  # was deberta-v3-small
MAX_LENGTH = 256
SEED = 42

SPLITS_DIR = Path(__file__).parent / "splits_v2"  # was splits/
CHECKPOINT_DIR = Path(__file__).parent / "checkpoints" / "deberta-v3-base-injection-v2"
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
    """Compute inverse-frequency class weights."""
    labels = np.array(train_ds["label"])
    num_samples = len(labels)
    num_classes = 2

    counts = np.bincount(labels, minlength=num_classes)
    weights = num_samples / (num_classes * counts)
    weights = weights / weights.sum() * num_classes

    print(f"Class distribution: benign={counts[0]} ({counts[0]/num_samples:.1%}), "
          f"injection={counts[1]} ({counts[1]/num_samples:.1%})")
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
            return_token_type_ids=False,
        )

    tokenized = dataset.map(
        tokenize_fn,
        batched=True,
        batch_size=1000,
        remove_columns=[c for c in dataset.column_names if c not in ("label",)],
        desc="Tokenizing",
    )

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
        forward_inputs = {k: v for k, v in inputs.items() if k != "labels"}
        outputs = model(**forward_inputs)
        logits = outputs.logits

        loss_fn = torch.nn.CrossEntropyLoss(
            weight=self.class_weights.to(logits.device)
        )
        loss = loss_fn(logits, labels)

        return (loss, outputs) if return_outputs else loss


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fine-tune DeBERTa-v3-base for injection detection (v2 data)"
    )
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--eval_batch_size", type=int, default=32)
    parser.add_argument("--grad_accum", type=int, default=1)
    parser.add_argument("--epochs", type=int, default=3,
                        help="PIGuard used 3 epochs")
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--warmup_ratio", type=float, default=0.1)
    parser.add_argument("--weight_decay", type=float, default=0.01)
    parser.add_argument("--no_wandb", action="store_true")
    parser.add_argument("--fp16", action="store_true", default=True)
    parser.add_argument("--no_fp16", action="store_true")
    parser.add_argument("--patience", type=int, default=2)
    return parser.parse_args()


def main():
    args = parse_args()

    if args.no_fp16:
        args.fp16 = False

    print("=" * 60)
    print("Round 1: Fine-tune DeBERTa-v3-base (v2 data)")
    print("=" * 60)
    print(f"Model: {MODEL_NAME}")
    print(f"Data:  {SPLITS_DIR}")

    if torch.cuda.is_available():
        gpu = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"GPU: {gpu} ({vram:.1f}GB)")
    else:
        print("WARNING: No GPU detected — training will be very slow")

    torch.manual_seed(SEED)
    np.random.seed(SEED)

    # -- Load data --
    print("\n[1/5] Loading v2 data...")
    train_ds, val_ds = load_splits()

    # -- Class weights --
    print("\n[2/5] Computing class weights...")
    class_weights = compute_class_weights(train_ds)

    # -- Tokenizer + Model --
    print(f"\n[3/5] Loading model: {MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME,
        cache_dir=str(HF_CACHE_DIR),
        use_fast=False,  # DeBERTa-v3 fast tokenizer bug
    )
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=2,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        cache_dir=str(HF_CACHE_DIR),
    )

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
            name=f"deberta-v3-base-v2-bs{args.batch_size}-lr{args.lr}",
            config={
                "model": MODEL_NAME,
                "version": "v0.3.1-round1",
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
                "hard_negatives": 5500,
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
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        save_total_limit=2,
        logging_strategy="steps",
        logging_steps=50,
        report_to=report_to,
        seed=SEED,
        data_seed=SEED,
        dataloader_num_workers=2,
        dataloader_pin_memory=True,
        push_to_hub=False,
    )

    # -- Trainer --
    print("\n[5/5] Starting training...")
    print(f"  Batch size: {args.batch_size} (x{args.grad_accum} accum = {args.batch_size * args.grad_accum} effective)")
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

    train_result = trainer.train()

    # -- Save best model --
    best_dir = CHECKPOINT_DIR / "best"
    best_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(best_dir))
    tokenizer.save_pretrained(str(best_dir))
    print(f"\nBest model saved to: {best_dir}")

    # -- Final evaluation --
    print("\n" + "=" * 60)
    print("Final Validation Results")
    print("=" * 60)

    eval_results = trainer.evaluate()

    for key, value in sorted(eval_results.items()):
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")

    # -- Save results --
    results_path = CHECKPOINT_DIR / "training_results_v2.json"
    results = {
        "model": MODEL_NAME,
        "version": "v0.3.1-round1",
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
            k: round(v, 6) if isinstance(v, float) else v
            for k, v in eval_results.items()
        },
        "data": {
            "train_samples": len(train_tokenized),
            "val_samples": len(val_tokenized),
            "hard_negatives_added": 5500,
            "splits_dir": str(SPLITS_DIR),
        },
    }

    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {results_path}")

    # -- Check success criteria --
    val_f1 = eval_results.get("eval_f1", 0)
    val_fpr = eval_results.get("eval_fpr", 1)

    print("\n" + "=" * 60)
    print("Success Criteria")
    print("=" * 60)

    if val_f1 >= 0.93:
        print(f"  ✓ Val F1 {val_f1:.4f} >= 0.93")
    else:
        print(f"  ✗ Val F1 {val_f1:.4f} < 0.93")

    if val_fpr <= 0.05:
        print(f"  ✓ Val FPR {val_fpr:.4f} <= 5%")
    else:
        print(f"  ⚠ Val FPR {val_fpr:.4f} > 5% — may need Round 2 (focal loss)")

    print(f"\nNext: Run benchmark to check NotInject FPR and ProtectAI F1")

    # -- Finish WandB --
    if not args.no_wandb and wandb.run is not None:
        wandb.log({
            "final/val_f1": val_f1,
            "final/val_fpr": val_fpr,
            "final/val_precision": eval_results.get("eval_precision", 0),
            "final/val_recall": eval_results.get("eval_recall", 0),
        })
        wandb.finish()

    return 0


if __name__ == "__main__":
    sys.exit(main())

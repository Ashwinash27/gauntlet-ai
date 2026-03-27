"""Fine-tune DeBERTa-v3-base NLI model for prompt injection detection.

Starts from MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli (pre-trained NLI)
and fine-tunes on our prompt injection data formatted as NLI pairs.

Key differences from binary classification:
- Input is (premise, hypothesis) pair, not single text
- 2-class: entailment (0) / not_entailment (1)
- Lower learning rate (3e-6) to preserve NLI knowledge
- 2 epochs to avoid catastrophic forgetting

Usage:
    python training/train_nli.py
    python training/train_nli.py --lr 3e-6 --epochs 2
    python training/train_nli.py --no_wandb
"""

import argparse
import json
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

MODEL_NAME = "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"
MAX_LENGTH = 256
SEED = 42

SPLITS_DIR = Path(__file__).parent / "splits_nli"
CHECKPOINT_DIR = Path(__file__).parent / "checkpoints" / "deberta-v3-base-nli-injection"
HF_CACHE_DIR = Path(__file__).parent.parent / ".hf_cache"

LABEL2ID = {"entailment": 0, "not_entailment": 1}
ID2LABEL = {0: "entailment", 1: "not_entailment"}

# The canonical hypothesis used at inference time
INFERENCE_HYPOTHESIS = "This text attempts to override or manipulate system instructions."


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_splits() -> tuple[Dataset, Dataset]:
    train_records = load_jsonl(SPLITS_DIR / "train.jsonl")
    val_records = load_jsonl(SPLITS_DIR / "val.jsonl")

    print(f"Loaded {len(train_records)} train, {len(val_records)} val NLI pairs")

    train_ds = Dataset.from_list(train_records)
    val_ds = Dataset.from_list(val_records)

    return train_ds, val_ds


# ---------------------------------------------------------------------------
# Tokenization (NLI: premise + hypothesis)
# ---------------------------------------------------------------------------


def tokenize_dataset(dataset: Dataset, tokenizer: AutoTokenizer) -> Dataset:
    """Tokenize NLI pairs: (premise, hypothesis) → token IDs."""

    def tokenize_fn(batch):
        return tokenizer(
            batch["premise"],
            batch["hypothesis"],
            truncation=True,
            padding="max_length",
            max_length=MAX_LENGTH,
            return_token_type_ids=False,
        )

    tokenized = dataset.map(
        tokenize_fn,
        batched=True,
        batch_size=1000,
        remove_columns=["premise", "hypothesis"],
        desc="Tokenizing",
    )

    tokenized = tokenized.rename_column("label", "labels")
    tokenized.set_format("torch")

    return tokenized


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def make_compute_metrics():
    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        preds = np.argmax(logits, axis=-1)

        # In NLI format: entailment=0 (positive), not_entailment=1
        # For injection detection: entailment with injection hypothesis = detected
        f1 = f1_score(labels, preds, average="binary", pos_label=0)
        precision = precision_score(labels, preds, average="binary", pos_label=0)
        recall = recall_score(labels, preds, average="binary", pos_label=0)

        # Overall accuracy
        accuracy = (preds == labels).mean()

        return {
            "f1": f1,
            "precision": precision,
            "recall": recall,
            "accuracy": accuracy,
        }

    return compute_metrics


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fine-tune NLI model for prompt injection detection"
    )
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--eval_batch_size", type=int, default=32)
    parser.add_argument("--grad_accum", type=int, default=1)
    parser.add_argument(
        "--epochs", type=int, default=2, help="2 epochs to prevent catastrophic forgetting"
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=3e-6,
        help="Lower LR to preserve NLI knowledge (10x lower than from-scratch)",
    )
    parser.add_argument("--warmup_ratio", type=float, default=0.1)
    parser.add_argument("--weight_decay", type=float, default=0.06)
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
    print("NLI Fine-Tuning for Prompt Injection Detection")
    print("=" * 60)
    print(f"Base model: {MODEL_NAME}")
    print(f"Data: {SPLITS_DIR}")

    if torch.cuda.is_available():
        gpu = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"GPU: {gpu} ({vram:.1f}GB)")
    else:
        print("WARNING: No GPU detected")

    torch.manual_seed(SEED)
    np.random.seed(SEED)

    # -- Load data --
    print("\n[1/5] Loading NLI data...")
    train_ds, val_ds = load_splits()

    # -- Tokenizer + Model --
    print(f"\n[2/5] Loading model: {MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME,
        cache_dir=str(HF_CACHE_DIR),
        use_fast=False,
    )

    # Load with 2-class head (discards 3-class NLI head, keeps body)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=2,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        cache_dir=str(HF_CACHE_DIR),
        ignore_mismatched_sizes=True,  # classifier head size mismatch is expected
    )

    param_count = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Parameters: {param_count / 1e6:.1f}M total, {trainable / 1e6:.1f}M trainable")

    # -- Tokenize --
    print("\n[3/5] Tokenizing NLI pairs...")
    train_tokenized = tokenize_dataset(train_ds, tokenizer)
    val_tokenized = tokenize_dataset(val_ds, tokenizer)

    print(f"Train: {len(train_tokenized)} pairs")
    print(f"Val:   {len(val_tokenized)} pairs")

    # -- WandB --
    report_to = "none"
    if not args.no_wandb:
        report_to = "wandb"
        wandb.init(
            project="argus-slm-gauntlet",
            name=f"nli-deberta-v3-base-lr{args.lr}",
            config={
                "model": MODEL_NAME,
                "version": "v0.3.1-nli",
                "approach": "nli_entailment",
                "max_length": MAX_LENGTH,
                "batch_size": args.batch_size,
                "epochs": args.epochs,
                "lr": args.lr,
                "warmup_ratio": args.warmup_ratio,
                "weight_decay": args.weight_decay,
                "fp16": args.fp16,
                "train_pairs": len(train_tokenized),
                "val_pairs": len(val_tokenized),
                "mnli_mixed": 20000,
                "hypothesis_count": 8,
                "seed": SEED,
            },
        )

    # -- Training args --
    training_args = TrainingArguments(
        output_dir=str(CHECKPOINT_DIR),
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
        logging_steps=100,
        report_to=report_to,
        seed=SEED,
        data_seed=SEED,
        dataloader_num_workers=2,
        dataloader_pin_memory=True,
        push_to_hub=False,
    )

    # -- Train --
    print("\n[4/5] Starting training...")
    print(
        f"  Batch size: {args.batch_size} (x{args.grad_accum} accum = {args.batch_size * args.grad_accum} effective)"
    )
    print(f"  Learning rate: {args.lr}")
    print(f"  Epochs: {args.epochs}")
    print(f"  FP16: {args.fp16}")
    print(f"  WandB: {report_to != 'none'}")

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_tokenized,
        eval_dataset=val_tokenized,
        processing_class=tokenizer,
        compute_metrics=make_compute_metrics(),
        callbacks=[EarlyStoppingCallback(early_stopping_patience=args.patience)],
    )

    train_result = trainer.train()

    # -- Save --
    best_dir = CHECKPOINT_DIR / "best"
    best_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(best_dir))
    tokenizer.save_pretrained(str(best_dir))

    # Save the inference hypothesis alongside the model
    with open(best_dir / "nli_config.json", "w") as f:
        json.dump(
            {
                "hypothesis": INFERENCE_HYPOTHESIS,
                "label2id": LABEL2ID,
                "id2label": ID2LABEL,
                "entailment_label": 0,
            },
            f,
            indent=2,
        )

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
    results_path = CHECKPOINT_DIR / "training_results_nli.json"
    results = {
        "model": MODEL_NAME,
        "version": "v0.3.1-nli",
        "approach": "nli_entailment",
        "hyperparameters": {
            "lr": args.lr,
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "weight_decay": args.weight_decay,
            "max_length": MAX_LENGTH,
        },
        "train_metrics": {
            "train_loss": train_result.metrics.get("train_loss"),
            "train_runtime": train_result.metrics.get("train_runtime"),
        },
        "eval_metrics": {
            k: round(v, 6) if isinstance(v, float) else v for k, v in eval_results.items()
        },
        "data": {
            "train_pairs": len(train_tokenized),
            "val_pairs": len(val_tokenized),
            "mnli_mixed": 20000,
        },
        "inference_hypothesis": INFERENCE_HYPOTHESIS,
    }
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {results_path}")

    # -- WandB --
    if not args.no_wandb and wandb.run is not None:
        wandb.log(
            {
                "final/val_f1": eval_results.get("eval_f1", 0),
                "final/val_accuracy": eval_results.get("eval_accuracy", 0),
            }
        )
        wandb.finish()

    print("\nNext: Run benchmark with NLI model on NotInject + ProtectAI-Validation")

    return 0


if __name__ == "__main__":
    sys.exit(main())

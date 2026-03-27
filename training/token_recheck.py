"""Round 2 Step 1a: PIGuard MOF Token-Wise Recheck.

Feed every token in the DeBERTa vocabulary individually through the trained
model. Tokens classified as "injection" by argmax are biased trigger tokens.

Uses the Round 1 base model (v2 checkpoint) for recheck.

Usage:
    python training/token_recheck.py
    python training/token_recheck.py --model_path training/checkpoints/deberta-v3-small-injection/best
"""

import argparse
import json
import sys
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_MODEL_PATH = (
    Path(__file__).parent / "checkpoints" / "deberta-v3-base-injection-v2" / "best"
)
OUTPUT_PATH = Path(__file__).parent / "biased_tokens.json"


def main():
    parser = argparse.ArgumentParser(description="MOF Token-Wise Recheck")
    parser.add_argument("--model_path", type=str, default=str(DEFAULT_MODEL_PATH))
    parser.add_argument("--batch_size", type=int, default=256)
    args = parser.parse_args()

    model_path = Path(args.model_path)
    print("=" * 60)
    print("MOF Token-Wise Recheck")
    print("=" * 60)
    print(f"Model: {model_path}")

    # Load model + tokenizer
    print("\nLoading model...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(str(model_path), use_fast=False)
    model = AutoModelForSequenceClassification.from_pretrained(str(model_path))
    model.eval()
    model.to(device)

    vocab_size = tokenizer.vocab_size
    print(f"Vocabulary size: {vocab_size}")
    print(f"Device: {device}")

    # Feed every token individually
    print(f"\nRunning recheck on {vocab_size} tokens (batch_size={args.batch_size})...")
    biased_tokens = []
    biased_ids = []

    for start in range(0, vocab_size, args.batch_size):
        end = min(start + args.batch_size, vocab_size)
        batch_ids = list(range(start, end))

        # Decode each token to text
        batch_texts = []
        for tid in batch_ids:
            try:
                text = tokenizer.decode([tid], skip_special_tokens=True).strip()
                if not text:
                    text = tokenizer.convert_ids_to_tokens(tid)
                batch_texts.append(text)
            except Exception:
                batch_texts.append("")

        # Tokenize the texts (each token as a full input)
        inputs = tokenizer(
            batch_texts,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=32,
            return_token_type_ids=False,
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.inference_mode():
            logits = model(**inputs).logits
            preds = logits.argmax(dim=-1).cpu().tolist()

        for i, (tid, text, pred) in enumerate(zip(batch_ids, batch_texts, preds)):
            if pred == 1:  # Predicted as injection
                conf = torch.softmax(logits[i], dim=-1)[1].item()
                biased_tokens.append({
                    "token_id": tid,
                    "token_text": text,
                    "confidence": round(conf, 4),
                })
                biased_ids.append(tid)

        if (end) % 10000 < args.batch_size:
            print(f"  {end}/{vocab_size} ({end/vocab_size*100:.0f}%) — {len(biased_tokens)} biased so far")

    # Sort by confidence
    biased_tokens.sort(key=lambda x: -x["confidence"])

    # Save
    output = {
        "model_path": str(model_path),
        "vocab_size": vocab_size,
        "total_biased": len(biased_tokens),
        "biased_ratio": round(len(biased_tokens) / vocab_size, 4),
        "tokens": biased_tokens,
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Summary
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"  Total biased tokens: {len(biased_tokens)} / {vocab_size} ({len(biased_tokens)/vocab_size*100:.1f}%)")
    print(f"  Saved to: {OUTPUT_PATH}")

    print("\n  Top 30 biased tokens (highest confidence):")
    for t in biased_tokens[:30]:
        print(f"    {t['confidence']:.4f}  {t['token_text']!r}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

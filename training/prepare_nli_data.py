"""Convert binary classification data to NLI format for prompt injection detection.

Each (text, label) pair becomes two NLI rows:
- text + correct hypothesis → entailment (0)
- text + incorrect hypothesis → not_entailment (1)

Hypotheses are rotated from a set of 5 paraphrases per class to prevent
the model from overfitting to a single template.

Also mixes in 20K MNLI samples to prevent catastrophic forgetting of
general NLI capability.

Usage:
    python training/prepare_nli_data.py
"""

import hashlib
import json
import random
import sys
from pathlib import Path

RANDOM_SEED = 42
SPLITS_DIR = Path(__file__).parent / "splits_v3"
NLI_DIR = Path(__file__).parent / "splits_nli"
MNLI_SAMPLE_SIZE = 20000

# Hypotheses for injection class (text IS an attack → entailment)
INJECTION_HYPOTHESES = [
    "This text attempts to override or manipulate system instructions.",
    "This text contains instructions meant to hijack the AI's behavior.",
    "This text tries to make the AI ignore its original directives.",
    "This text is an attempt to inject unauthorized instructions into the AI system.",
    "This text instructs the AI to disregard its safety guidelines or system prompt.",
]

# Hypotheses for benign class (text is NOT an attack → entailment)
BENIGN_HYPOTHESES = [
    "This text is a legitimate user request or question.",
    "This is a normal message with no attempt to manipulate the AI.",
    "This text is a genuine user query that respects the AI's intended purpose.",
]


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def convert_to_nli(records: list[dict], rng: random.Random) -> list[dict]:
    """Convert binary classification records to NLI pairs.

    Each record produces 2 NLI rows:
    1. text + matching hypothesis → entailment (0)
    2. text + non-matching hypothesis → not_entailment (1)
    """
    nli_pairs = []

    for r in records:
        text = r["text"]
        label = r["label"]

        if label == 1:  # injection
            # Correct: injection hypothesis → entailment
            hyp_correct = rng.choice(INJECTION_HYPOTHESES)
            nli_pairs.append({
                "premise": text,
                "hypothesis": hyp_correct,
                "label": 0,  # entailment
            })
            # Incorrect: benign hypothesis → not_entailment
            hyp_wrong = rng.choice(BENIGN_HYPOTHESES)
            nli_pairs.append({
                "premise": text,
                "hypothesis": hyp_wrong,
                "label": 1,  # not_entailment
            })
        else:  # benign
            # Correct: benign hypothesis → entailment
            hyp_correct = rng.choice(BENIGN_HYPOTHESES)
            nli_pairs.append({
                "premise": text,
                "hypothesis": hyp_correct,
                "label": 0,  # entailment
            })
            # Incorrect: injection hypothesis → not_entailment
            hyp_wrong = rng.choice(INJECTION_HYPOTHESES)
            nli_pairs.append({
                "premise": text,
                "hypothesis": hyp_wrong,
                "label": 1,  # not_entailment
            })

    return nli_pairs


def load_mnli_samples(n: int, rng: random.Random) -> list[dict]:
    """Load MNLI samples to mix in for catastrophic forgetting prevention."""
    from datasets import load_dataset

    print(f"  Loading MNLI ({n} samples)...")
    ds = load_dataset("nyu-mll/multi_nli", split="train")

    # Map 3-class to 2-class: entailment=0, neutral+contradiction=1
    label_map = {0: 0, 1: 1, 2: 1}  # entailment=0, neutral=1, contradiction=1

    all_samples = []
    for row in ds:
        all_samples.append({
            "premise": row["premise"],
            "hypothesis": row["hypothesis"],
            "label": label_map[row["label"]],
        })

    rng2 = random.Random(RANDOM_SEED + 100)
    rng2.shuffle(all_samples)
    sampled = all_samples[:n]
    print(f"  Sampled {len(sampled)} MNLI pairs")
    return sampled


def main():
    print("=" * 60)
    print("Convert Training Data to NLI Format")
    print("=" * 60)

    rng = random.Random(RANDOM_SEED)
    NLI_DIR.mkdir(exist_ok=True)

    # Load and convert each split
    for split_name in ["train", "val", "test"]:
        print(f"\n[{split_name}] Loading...")
        records = load_jsonl(SPLITS_DIR / f"{split_name}.jsonl")
        print(f"  Original: {len(records)} samples")

        nli_pairs = convert_to_nli(records, rng)
        print(f"  NLI pairs: {len(nli_pairs)} (2x original)")

        # Add MNLI samples to training set only
        if split_name == "train":
            mnli = load_mnli_samples(MNLI_SAMPLE_SIZE, rng)
            nli_pairs.extend(mnli)
            print(f"  After MNLI mix: {len(nli_pairs)}")

        # Shuffle
        rng.shuffle(nli_pairs)

        # Save
        path = NLI_DIR / f"{split_name}.jsonl"
        with open(path, "w") as f:
            for p in nli_pairs:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
        print(f"  Saved: {path}")

        # Stats
        ent = sum(1 for p in nli_pairs if p["label"] == 0)
        not_ent = sum(1 for p in nli_pairs if p["label"] == 1)
        print(f"  Entailment: {ent} ({ent/len(nli_pairs)*100:.1f}%)")
        print(f"  Not-entailment: {not_ent} ({not_ent/len(nli_pairs)*100:.1f}%)")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Output dir: {NLI_DIR}")
    print(f"  Injection hypotheses: {len(INJECTION_HYPOTHESES)}")
    print(f"  Benign hypotheses: {len(BENIGN_HYPOTHESES)}")
    print(f"  MNLI samples mixed into train: {MNLI_SAMPLE_SIZE}")

    # Show examples
    print("\n  Example NLI pairs:")
    train_data = load_jsonl(NLI_DIR / "train.jsonl")
    for p in train_data[:4]:
        label_str = "entailment" if p["label"] == 0 else "not_entailment"
        print(f"    [{label_str}]")
        print(f"      P: {p['premise'][:80]}...")
        print(f"      H: {p['hypothesis'][:80]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

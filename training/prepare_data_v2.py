"""Round 1: Rebuild training splits with hard negative data.

Merges original training data with downloaded hard negatives,
runs contamination check against holdout, and creates v2 splits.

Usage:
    python training/prepare_data_v2.py
"""

import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

RANDOM_SEED = 42
SPLITS_DIR = Path(__file__).parent / "splits"
HARD_NEG_PATH = Path(__file__).parent / "hard_negatives" / "all_hard_negatives.jsonl"
HOLDOUT_PATH = Path(__file__).parent / "holdout_composite.csv"

V2_DIR = Path(__file__).parent / "splits_v2"


def text_hash(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()


def load_original_splits() -> list[dict]:
    """Load all original v1 train/val/test samples."""
    samples = []
    for split_name in ["train", "val", "test"]:
        path = SPLITS_DIR / f"{split_name}.jsonl"
        with open(path) as f:
            for line in f:
                row = json.loads(line)
                row["_orig_split"] = split_name
                samples.append(row)
    return samples


def load_hard_negatives() -> list[dict]:
    """Load downloaded hard negatives."""
    samples = []
    with open(HARD_NEG_PATH) as f:
        for line in f:
            samples.append(json.loads(line))
    return samples


def load_holdout_hashes() -> set[str]:
    """Load holdout text hashes for contamination check."""
    hashes = set()
    if HOLDOUT_PATH.exists():
        df = pd.read_csv(HOLDOUT_PATH)
        for text in df["text"]:
            hashes.add(text_hash(str(text)))
    return hashes


def main():
    print("=" * 60)
    print("Round 1: Rebuild Training Splits (v2)")
    print("=" * 60)

    random.seed(RANDOM_SEED)
    V2_DIR.mkdir(exist_ok=True)

    # Load everything
    print("\n[1] Loading data...")
    original = load_original_splits()
    hard_neg = load_hard_negatives()
    holdout_hashes = load_holdout_hashes()

    print(f"  Original samples: {len(original)}")
    print(f"  Hard negatives:   {len(hard_neg)}")
    print(f"  Holdout hashes:   {len(holdout_hashes)}")

    # Contamination check against holdout
    print("\n[2] Contamination check against holdout...")
    clean_hard_neg = []
    contaminated = 0
    for s in hard_neg:
        h = text_hash(s["text"])
        if h in holdout_hashes:
            contaminated += 1
        else:
            clean_hard_neg.append(s)
    print(f"  Contaminated (removed): {contaminated}")
    print(f"  Clean hard negatives:   {len(clean_hard_neg)}")

    # Dedup hard negatives against original data
    print("\n[3] Dedup hard negatives against original data...")
    orig_hashes = {text_hash(s["text"]) for s in original}
    deduped_hard_neg = []
    dupes = 0
    for s in clean_hard_neg:
        h = text_hash(s["text"])
        if h in orig_hashes:
            dupes += 1
        else:
            deduped_hard_neg.append(s)
            orig_hashes.add(h)
    print(f"  Duplicates removed: {dupes}")
    print(f"  Unique hard negatives to add: {len(deduped_hard_neg)}")

    # Merge: keep original splits structure, add hard negatives proportionally
    print("\n[4] Merging and splitting...")

    # Shuffle hard negatives and split 80/10/10
    random.shuffle(deduped_hard_neg)
    n = len(deduped_hard_neg)
    n_train = int(n * 0.8)
    n_val = int(n * 0.1)

    hn_train = deduped_hard_neg[:n_train]
    hn_val = deduped_hard_neg[n_train:n_train + n_val]
    hn_test = deduped_hard_neg[n_train + n_val:]

    # Separate original by split
    orig_train = [s for s in original if s["_orig_split"] == "train"]
    orig_val = [s for s in original if s["_orig_split"] == "val"]
    orig_test = [s for s in original if s["_orig_split"] == "test"]

    # Merge
    train_v2 = orig_train + hn_train
    val_v2 = orig_val + hn_val
    test_v2 = orig_test + hn_test

    # Shuffle each split
    random.shuffle(train_v2)
    random.shuffle(val_v2)
    random.shuffle(test_v2)

    # Remove _orig_split key before saving
    for split_data in [train_v2, val_v2, test_v2]:
        for s in split_data:
            s.pop("_orig_split", None)

    # Save
    print("\n[5] Saving v2 splits...")
    for name, data in [("train", train_v2), ("val", val_v2), ("test", test_v2)]:
        path = V2_DIR / f"{name}.jsonl"
        with open(path, "w") as f:
            for s in data:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
        print(f"  {name}: {len(data)} samples → {path}")

    # Stats
    print("\n" + "=" * 60)
    print("DATASET STATISTICS")
    print("=" * 60)

    for name, data in [("train", train_v2), ("val", val_v2), ("test", test_v2)]:
        labels = Counter(s["label"] for s in data)
        sources = Counter(s["source"] for s in data)
        benign = labels.get(0, 0)
        inject = labels.get(1, 0)
        ratio = benign / inject if inject > 0 else float("inf")
        print(f"\n  {name} ({len(data)} samples):")
        print(f"    Benign: {benign} ({benign/len(data)*100:.1f}%)")
        print(f"    Injection: {inject} ({inject/len(data)*100:.1f}%)")
        print(f"    Ratio (benign:injection): {ratio:.2f}:1")
        print(f"    Sources: {dict(sources.most_common(10))}")

    # Overall
    all_v2 = train_v2 + val_v2 + test_v2
    total_benign = sum(1 for s in all_v2 if s["label"] == 0)
    total_inject = sum(1 for s in all_v2 if s["label"] == 1)
    total_new = sum(1 for s in all_v2 if s["source"] in
                    ("wildjailbreak_adv_benign", "orbench_hard", "xstest_v2_safe"))

    print(f"\n  TOTAL: {len(all_v2)} samples")
    print(f"    Benign: {total_benign}, Injection: {total_inject}")
    print(f"    Ratio: {total_benign/total_inject:.2f}:1")
    print(f"    New hard negatives: {total_new} ({total_new/len(all_v2)*100:.1f}% of total)")

    # Save stats
    stats = {
        "total": len(all_v2),
        "benign": total_benign,
        "injection": total_inject,
        "ratio": round(total_benign / total_inject, 2),
        "new_hard_negatives": total_new,
        "splits": {
            "train": len(train_v2),
            "val": len(val_v2),
            "test": len(test_v2),
        },
        "sources": dict(Counter(s["source"] for s in all_v2).most_common()),
    }
    stats_path = V2_DIR / "stats_v2.json"
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"\n  Stats saved to {stats_path}")

    print("\n" + "=" * 60)
    print("DONE — v2 splits ready for training")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())

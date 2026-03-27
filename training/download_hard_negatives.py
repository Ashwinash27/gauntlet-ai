"""Round 1: Download hard negative datasets for FPR reduction.

Downloads benign samples from three curated sources:
1. WildJailbreak adversarial_benign (4,000 sampled from 78K)
2. OR-Bench hard-1k (1,319 over-refusal benign)
3. XSTest v2 safe prompts (250 dual-meaning benign)

Usage:
    python training/download_hard_negatives.py
"""

import hashlib
import json
import random
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = Path(__file__).parent / "hard_negatives"
HOLDOUT_PATH = Path(__file__).parent / "holdout_composite.csv"
TRAIN_PATH = Path(__file__).parent / "splits" / "train.jsonl"

WILDJAILBREAK_SAMPLE_SIZE = 4000
RANDOM_SEED = 42


def text_hash(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()


def load_existing_hashes() -> set[str]:
    """Load hashes of existing training data + holdout to check for contamination."""
    hashes = set()

    # Training data
    if TRAIN_PATH.exists():
        with open(TRAIN_PATH) as f:
            for line in f:
                row = json.loads(line)
                hashes.add(text_hash(row["text"]))
        print(f"  Loaded {len(hashes)} training hashes")

    # Holdout
    if HOLDOUT_PATH.exists():
        df = pd.read_csv(HOLDOUT_PATH)
        for text in df["text"]:
            hashes.add(text_hash(str(text)))
        print(f"  Total hashes (train + holdout): {len(hashes)}")

    return hashes


def download_wildjailbreak(existing_hashes: set[str]) -> list[dict]:
    """Download WildJailbreak adversarial benign samples."""
    from datasets import load_dataset

    print("\n[1/3] Downloading WildJailbreak (allenai/wildjailbreak)...")
    print("  Using streaming mode (avoids schema cast errors)...")

    ds = load_dataset("allenai/wildjailbreak", "train", split="train", streaming=True)

    # Stream, filter, and collect
    samples = []
    seen = set()
    count = 0
    for row in ds:
        count += 1
        if count % 50000 == 0:
            print(f"  Processed {count} rows, collected {len(samples)} adversarial benign...")

        if row.get("data_type") != "adversarial_benign":
            continue

        text = row.get("adversarial")
        if text is None or not isinstance(text, str) or len(text.strip()) < 10:
            continue
        h = text_hash(text)
        if h in existing_hashes or h in seen:
            continue
        seen.add(h)
        samples.append({
            "text": text.strip(),
            "label": 0,
            "source": "wildjailbreak_adv_benign",
            "attack_category": "none",
        })

    print(f"  Total rows scanned: {count}")
    print(f"  After dedup: {len(samples)} unique adversarial benign samples")

    # Random sample
    random.seed(RANDOM_SEED)
    if len(samples) > WILDJAILBREAK_SAMPLE_SIZE:
        samples = random.sample(samples, WILDJAILBREAK_SAMPLE_SIZE)
    print(f"  Sampled: {len(samples)}")

    return samples


def download_orbench(existing_hashes: set[str]) -> list[dict]:
    """Download OR-Bench hard-1k benign samples."""
    from datasets import load_dataset

    print("\n[2/3] Downloading OR-Bench hard-1k (bench-llm/or-bench)...")

    ds = load_dataset("bench-llm/or-bench", "or-bench-hard-1k", split="train")
    print(f"  Total samples: {len(ds)}")

    samples = []
    seen = set()
    for row in ds:
        text = row["prompt"]
        if text is None or len(text.strip()) < 10:
            continue
        h = text_hash(text)
        if h in existing_hashes or h in seen:
            continue
        seen.add(h)
        samples.append({
            "text": text.strip(),
            "label": 0,
            "source": "orbench_hard",
            "attack_category": "none",
        })

    print(f"  After dedup: {len(samples)} unique samples")
    return samples


def download_xstest(existing_hashes: set[str]) -> list[dict]:
    """Download XSTest v2 safe prompts."""
    from datasets import load_dataset

    print("\n[3/3] Downloading XSTest v2 (natolambert/xstest-v2-copy)...")

    ds = load_dataset("natolambert/xstest-v2-copy", split="prompts")
    print(f"  Total prompts: {len(ds)}")

    # Filter for safe (non-contrast) types
    safe = ds.filter(lambda x: not x["type"].startswith("contrast_"))
    print(f"  Safe prompts: {len(safe)}")

    samples = []
    seen = set()
    for row in safe:
        text = row["prompt"]
        if text is None or len(text.strip()) < 10:
            continue
        h = text_hash(text)
        if h in existing_hashes or h in seen:
            continue
        seen.add(h)
        samples.append({
            "text": text.strip(),
            "label": 0,
            "source": "xstest_v2_safe",
            "attack_category": "none",
        })

    print(f"  After dedup: {len(samples)} unique samples")
    return samples


def main():
    print("=" * 60)
    print("Round 1: Download Hard Negative Datasets")
    print("=" * 60)

    OUTPUT_DIR.mkdir(exist_ok=True)

    # Load existing hashes for dedup
    print("\n[0] Loading existing data hashes for deduplication...")
    existing_hashes = load_existing_hashes()

    # Download all three
    wj_samples = download_wildjailbreak(existing_hashes)
    # Update hashes so subsequent datasets dedup against WJ too
    for s in wj_samples:
        existing_hashes.add(text_hash(s["text"]))

    orb_samples = download_orbench(existing_hashes)
    for s in orb_samples:
        existing_hashes.add(text_hash(s["text"]))

    xst_samples = download_xstest(existing_hashes)

    # Save each dataset
    all_samples = []

    for name, samples in [
        ("wildjailbreak", wj_samples),
        ("orbench", orb_samples),
        ("xstest", xst_samples),
    ]:
        path = OUTPUT_DIR / f"{name}.jsonl"
        with open(path, "w") as f:
            for s in samples:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
        print(f"\n  Saved {len(samples)} samples to {path}")
        all_samples.extend(samples)

    # Save combined
    combined_path = OUTPUT_DIR / "all_hard_negatives.jsonl"
    with open(combined_path, "w") as f:
        for s in all_samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  WildJailbreak:  {len(wj_samples)}")
    print(f"  OR-Bench:       {len(orb_samples)}")
    print(f"  XSTest v2:      {len(xst_samples)}")
    print(f"  Total:          {len(all_samples)}")
    print(f"  Combined file:  {combined_path}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())

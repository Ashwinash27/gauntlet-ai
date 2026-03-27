"""Download curated datasets from HuggingFace Hub for training.

v0.3.0: 5 research-backed datasets replacing original 8.
Dropped: WildJailbreak, HackAPrompt, Pliny, HarmBench, TensorTrust, Jasper.

Usage:
    HF_TOKEN=hf_xxx python training/download_datasets.py
"""

import os
from pathlib import Path

RAW_DIR = Path(__file__).parent / "raw"
HOLDOUT_PATH = Path(__file__).parent / "holdout_pint_test.csv"

OLD_FILES = [
    "wildjailbreak.parquet",
    "hackaprompt.parquet",
    "pliny.parquet",
    "harmbench.parquet",
    "tensortrust.parquet",
    "jasper.parquet",
]


def download_pint() -> None:
    """PINT — core injection/benign pairs. Test split locked as holdout."""
    from datasets import load_dataset

    print("[1/5] deepset/prompt-injections (PINT)...")
    ds = load_dataset("deepset/prompt-injections")

    train_path = RAW_DIR / "pint_train.csv"
    ds["train"].to_csv(str(train_path))
    print(f"  Train: {len(ds['train'])} rows -> {train_path}")

    if HOLDOUT_PATH.exists():
        print(f"  Holdout already locked ({HOLDOUT_PATH}) — skipping test split")
    else:
        ds["test"].to_csv(str(HOLDOUT_PATH))
        print(f"  Holdout LOCKED: {len(ds['test'])} rows -> {HOLDOUT_PATH}")


def download_neuralchemy() -> None:
    """Neuralchemy — 22K samples, 29 attack categories, explicit hard negatives."""
    from datasets import load_dataset

    print("[2/5] neuralchemy/Prompt-injection-dataset...")
    ds = load_dataset("neuralchemy/Prompt-injection-dataset", split="train")
    print(f"  Columns: {ds.column_names}")
    print(f"  First 3 rows:")
    for i, row in enumerate(ds.select(range(min(3, len(ds))))):
        print(f"    {i}: {dict(row)}")

    out = RAW_DIR / "neuralchemy.parquet"
    ds.to_pandas().to_parquet(str(out))
    print(f"  {len(ds)} rows -> {out}")


def download_safeguard() -> None:
    """SafeGuard — labeled injection/benign pairs."""
    from datasets import load_dataset

    print("[3/5] xTRam1/safe-guard-prompt-injection...")
    ds = load_dataset("xTRam1/safe-guard-prompt-injection", split="train")
    out = RAW_DIR / "safeguard.parquet"
    ds.to_pandas().to_parquet(str(out))
    print(f"  {len(ds)} rows -> {out}")


def download_slabs() -> None:
    """S-Labs — 15K samples, hard negatives designed for encoder models."""
    from datasets import load_dataset

    print("[4/5] S-Labs/prompt-injection-dataset...")
    ds = load_dataset("S-Labs/prompt-injection-dataset", split="train")
    print(f"  Columns: {ds.column_names}")
    print(f"  First 3 rows:")
    for i, row in enumerate(ds.select(range(min(3, len(ds))))):
        print(f"    {i}: {dict(row)}")

    out = RAW_DIR / "slabs.parquet"
    ds.to_pandas().to_parquet(str(out))
    print(f"  {len(ds)} rows -> {out}")


def download_shieldlm() -> None:
    """ShieldLM — 54K multilingual, 3 attack types, curated from 11 sources.
    WARNING: Contains SafeGuard verbatim — dedup handled in prepare step.
    """
    from datasets import load_dataset

    print("[5/5] dmilush/shieldlm-prompt-injection...")
    ds = load_dataset("dmilush/shieldlm-prompt-injection", split="train")
    print(f"  Columns: {ds.column_names}")
    print(f"  First 3 rows:")
    for i, row in enumerate(ds.select(range(min(3, len(ds))))):
        print(f"    {i}: {dict(row)}")

    out = RAW_DIR / "shieldlm.parquet"
    ds.to_pandas().to_parquet(str(out))
    print(f"  {len(ds)} rows -> {out}")


def warn_old_files() -> None:
    """Warn about leftover files from old dataset plan."""
    found = []
    for name in OLD_FILES:
        path = RAW_DIR / name
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            found.append(f"    {name}: {size_mb:.1f} MB")
    if found:
        print("\nWARNING: Old dataset files found in raw/ (safe to delete):")
        for line in found:
            print(line)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Gauntlet Training Data Download (v0.3.0)")
    print("=" * 60)

    for fn in [
        download_pint,
        download_neuralchemy,
        download_safeguard,
        download_slabs,
        download_shieldlm,
    ]:
        try:
            fn()
        except Exception as e:
            print(f"  FAILED: {e}")
            print("  Continuing...")

    warn_old_files()

    print()
    print("=" * 60)
    print("Download complete! Files:")
    for f in sorted(RAW_DIR.glob("*")):
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  {f.name}: {size_mb:.1f} MB")
    print("=" * 60)


if __name__ == "__main__":
    main()

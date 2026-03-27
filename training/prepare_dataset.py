"""Merge, deduplicate, audit, and split downloaded datasets into train/val/test.

v0.3.0 pipeline:
  1. Load & harmonize 5 datasets -> unified {text, label, source, attack_category}
  2. Source-aware exact dedup (priority: pint > neuralchemy > safeguard > slabs > shieldlm)
  3. Audit ShieldLM-SafeGuard overlap and log stats
  4. MinHash fuzzy dedup (Jaccard threshold=0.8)
  5. Contamination audit vs PINT holdout (exact hash + fuzzy Jaccard>0.9)
  6. Analyze class distribution (NO resampling — focal loss handles imbalance)
  7. Stratified 80/10/10 split by label+source
  8. Save splits + stats_report.json

Usage:
    python training/prepare_dataset.py
"""

import json
from pathlib import Path

import pandas as pd
import xxhash
from datasketch import MinHash, MinHashLSH
from sklearn.model_selection import train_test_split

RAW_DIR = Path(__file__).parent / "raw"
SPLITS_DIR = Path(__file__).parent / "splits"
HOLDOUT_PATH = Path(__file__).parent / "holdout_pint_test.csv"

SOURCE_PRIORITY = {
    "pint": 0,
    "neuralchemy": 1,
    "safeguard": 2,
    "slabs": 3,
    "shieldlm": 4,
}


# ---------------------------------------------------------------------------
# Label normalization
# ---------------------------------------------------------------------------

_INJECTION_LABELS = {
    "1", "injection", "unsafe", "malicious", "attack", "jailbreak",
    "prompt_injection", "prompt-injection", "true",
}
_BENIGN_LABELS = {
    "0", "benign", "safe", "legitimate", "legit", "normal", "false",
}


def normalize_label(value) -> int:
    """Map any label format to binary 0/1 (1=injection, 0=benign)."""
    if isinstance(value, (bool, int, float)):
        return int(bool(value))
    s = str(value).strip().lower()
    if s in _INJECTION_LABELS:
        return 1
    if s in _BENIGN_LABELS:
        return 0
    # Try numeric
    try:
        return int(bool(int(float(s))))
    except (ValueError, TypeError):
        pass
    raise ValueError(f"Cannot normalize label: {value!r}")


# ---------------------------------------------------------------------------
# Dataset loaders
# ---------------------------------------------------------------------------

def _find_text_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    # Case-insensitive fallback
    lower_map = {c.lower(): c for c in df.columns}
    for col in candidates:
        if col.lower() in lower_map:
            return lower_map[col.lower()]
    return None


def _find_label_col(df: pd.DataFrame) -> str | None:
    return _find_text_col(df, ["label", "label_binary", "is_injection", "class", "target", "Label"])


def load_pint_train() -> pd.DataFrame:
    """Load PINT train split."""
    path = RAW_DIR / "pint_train.csv"
    if not path.exists():
        print(f"  SKIP: {path} not found")
        return pd.DataFrame()

    df = pd.read_csv(path)
    return pd.DataFrame({
        "text": df["text"].astype(str),
        "label": df["label"].apply(normalize_label),
        "source": "pint",
        "attack_category": None,
    })


def load_neuralchemy() -> pd.DataFrame:
    """Load Neuralchemy prompt injection dataset."""
    path = RAW_DIR / "neuralchemy.parquet"
    if not path.exists():
        print(f"  SKIP: {path} not found")
        return pd.DataFrame()

    df = pd.read_parquet(path)
    text_col = _find_text_col(df, ["text", "prompt", "input", "content"])
    label_col = _find_label_col(df)
    # Neuralchemy uses "category" for attack type (e.g., "benign", "jailbreak", etc.)
    cat_col = _find_text_col(df, ["category", "attack_category", "type", "attack_type"])

    if text_col is None:
        print(f"  WARNING: No text column in neuralchemy. Columns: {list(df.columns)}")
        return pd.DataFrame()

    result = pd.DataFrame({
        "text": df[text_col].astype(str),
        "label": df[label_col].apply(normalize_label) if label_col else 1,
        "source": "neuralchemy",
        "attack_category": df[cat_col].astype(str) if cat_col else None,
    })
    return result


def load_safeguard() -> pd.DataFrame:
    """Load SafeGuard injection/benign pairs."""
    path = RAW_DIR / "safeguard.parquet"
    if not path.exists():
        print(f"  SKIP: {path} not found")
        return pd.DataFrame()

    df = pd.read_parquet(path)
    text_col = _find_text_col(df, ["text", "prompt", "input", "content"])
    label_col = _find_label_col(df)

    if text_col is None:
        print(f"  WARNING: No text column in safeguard. Columns: {list(df.columns)}")
        return pd.DataFrame()

    return pd.DataFrame({
        "text": df[text_col].astype(str),
        "label": df[label_col].apply(normalize_label) if label_col else 1,
        "source": "safeguard",
        "attack_category": None,
    })


def load_slabs() -> pd.DataFrame:
    """Load S-Labs prompt injection dataset."""
    path = RAW_DIR / "slabs.parquet"
    if not path.exists():
        print(f"  SKIP: {path} not found")
        return pd.DataFrame()

    df = pd.read_parquet(path)
    text_col = _find_text_col(df, ["text", "prompt", "input", "content"])
    label_col = _find_label_col(df)

    if text_col is None:
        print(f"  WARNING: No text column in slabs. Columns: {list(df.columns)}")
        return pd.DataFrame()

    return pd.DataFrame({
        "text": df[text_col].astype(str),
        "label": df[label_col].apply(normalize_label) if label_col else 1,
        "source": "slabs",
        "attack_category": None,
    })


def load_shieldlm() -> pd.DataFrame:
    """Load ShieldLM prompt injection dataset."""
    path = RAW_DIR / "shieldlm.parquet"
    if not path.exists():
        print(f"  SKIP: {path} not found")
        return pd.DataFrame()

    df = pd.read_parquet(path)
    text_col = _find_text_col(df, ["text", "prompt", "input", "content"])
    label_col = _find_label_col(df)
    cat_col = _find_text_col(df, ["label_category", "attack_category", "category", "type", "attack_type"])

    if text_col is None:
        print(f"  WARNING: No text column in shieldlm. Columns: {list(df.columns)}")
        return pd.DataFrame()

    return pd.DataFrame({
        "text": df[text_col].astype(str),
        "label": df[label_col].apply(normalize_label) if label_col else 1,
        "source": "shieldlm",
        "attack_category": df[cat_col].astype(str) if cat_col else None,
    })


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def dedup_exact_source_aware(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Exact-text dedup with source priority. Higher-priority sources kept."""
    before = len(df)
    df = df.copy()
    df["_priority"] = df["source"].map(SOURCE_PRIORITY).fillna(99)
    df = df.sort_values("_priority").drop_duplicates(subset=["text"], keep="first")
    df = df.drop(columns=["_priority"])
    removed = before - len(df)
    return df.reset_index(drop=True), removed


def audit_shieldlm_safeguard_overlap(df: pd.DataFrame) -> dict:
    """Count how many ShieldLM rows were exact duplicates of SafeGuard rows."""
    sg_texts = set(df[df["source"] == "safeguard"]["text"])
    sl_texts = set(df[df["source"] == "shieldlm"]["text"])
    # Overlap means texts that appear in both sources before dedup
    # After dedup, SafeGuard copies are kept. Count the ShieldLM-only texts
    # that were also in SafeGuard (i.e., what got dropped from ShieldLM).
    # We need to check original data for this.
    overlap = sg_texts & sl_texts
    sg_total = len(sg_texts)
    return {
        "count": len(overlap),
        "safeguard_total": sg_total,
        "pct": round(len(overlap) / sg_total * 100, 1) if sg_total else 0,
    }


def _make_shingles(text: str, k: int = 3) -> list[str]:
    """Word-level k-shingles."""
    words = text.lower().split()
    if len(words) < k:
        return words  # Return individual words for short texts
    return [" ".join(words[i:i + k]) for i in range(len(words) - k + 1)]


def dedup_minhash(df: pd.DataFrame, threshold: float = 0.8, num_perm: int = 128) -> tuple[pd.DataFrame, int]:
    """MinHash LSH fuzzy dedup. Texts < 3 words are always kept."""
    before = len(df)
    short_mask = df["text"].str.split().str.len() < 3
    short_df = df[short_mask]
    long_df = df[~short_mask].copy()

    if len(long_df) == 0:
        return df, 0

    # Build MinHash signatures
    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
    minhashes = {}
    for idx, text in long_df["text"].items():
        m = MinHash(num_perm=num_perm)
        for shingle in _make_shingles(str(text)):
            m.update(shingle.encode("utf-8"))
        minhashes[idx] = m
        try:
            lsh.insert(str(idx), m)
        except ValueError:
            # Duplicate MinHash signature — already in LSH
            pass

    # Find clusters, keep highest-priority member
    to_remove = set()
    seen = set()
    for idx in long_df.index:
        if idx in to_remove or idx in seen:
            continue
        seen.add(idx)
        candidates = lsh.query(minhashes[idx])
        cluster_indices = [int(c) for c in candidates if int(c) != idx and int(c) not in to_remove]
        if not cluster_indices:
            continue
        # Keep the one with highest source priority (lowest number)
        all_in_cluster = [idx] + cluster_indices
        priorities = [(i, SOURCE_PRIORITY.get(long_df.loc[i, "source"], 99)) for i in all_in_cluster]
        priorities.sort(key=lambda x: x[1])
        keeper = priorities[0][0]
        for i, _ in priorities[1:]:
            to_remove.add(i)
            seen.add(i)

    long_df = long_df.drop(index=list(to_remove))
    result = pd.concat([short_df, long_df], ignore_index=True)
    removed = before - len(result)
    return result, removed


# ---------------------------------------------------------------------------
# Contamination audit
# ---------------------------------------------------------------------------

def contamination_audit(
    df: pd.DataFrame,
    holdout_path: Path,
) -> tuple[pd.DataFrame, dict]:
    """Two-tier contamination check: exact hash + fuzzy MinHash (Jaccard>0.9)."""
    stats = {"exact_removed": 0, "fuzzy_removed": 0, "status": "CLEAN"}

    if not holdout_path.exists():
        print("  WARNING: holdout_pint_test.csv not found — cannot audit!")
        stats["status"] = "SKIPPED"
        return df, stats

    holdout = pd.read_csv(holdout_path)
    holdout_texts = holdout["text"].astype(str).str.strip().tolist()

    # Tier 1: exact hash match
    holdout_hashes = {xxhash.xxh64(t.encode("utf-8")).hexdigest() for t in holdout_texts}
    df = df.copy()
    df["_hash"] = df["text"].apply(lambda t: xxhash.xxh64(str(t).encode("utf-8")).hexdigest())
    exact_mask = df["_hash"].isin(holdout_hashes)
    stats["exact_removed"] = int(exact_mask.sum())
    df = df[~exact_mask].drop(columns=["_hash"])

    # Tier 2: fuzzy MinHash match (higher threshold than general dedup)
    holdout_minhashes = []
    for t in holdout_texts:
        m = MinHash(num_perm=128)
        for shingle in _make_shingles(t):
            m.update(shingle.encode("utf-8"))
        holdout_minhashes.append(m)

    fuzzy_remove = set()
    for idx, text in df["text"].items():
        m = MinHash(num_perm=128)
        for shingle in _make_shingles(str(text)):
            m.update(shingle.encode("utf-8"))
        for hm in holdout_minhashes:
            if m.jaccard(hm) > 0.9:
                fuzzy_remove.add(idx)
                break

    stats["fuzzy_removed"] = len(fuzzy_remove)
    df = df.drop(index=list(fuzzy_remove))

    if stats["exact_removed"] > 0 or stats["fuzzy_removed"] > 0:
        stats["status"] = "CONTAMINATION_REMOVED"
        print(f"  CONTAMINATION FOUND: {stats['exact_removed']} exact + {stats['fuzzy_removed']} fuzzy matches removed")
    else:
        print("  Contamination audit: CLEAN (0 overlap)")

    return df.reset_index(drop=True), stats


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main() -> None:
    SPLITS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Gauntlet Dataset Preparation (v0.3.0)")
    print("=" * 60)

    # Step 1: Load & harmonize
    print("\n[1/8] Loading datasets...")
    all_dfs = []
    raw_counts = {}

    for name, loader in [
        ("PINT train", load_pint_train),
        ("Neuralchemy", load_neuralchemy),
        ("SafeGuard", load_safeguard),
        ("S-Labs", load_slabs),
        ("ShieldLM", load_shieldlm),
    ]:
        print(f"\n  Loading {name}...")
        df = loader()
        if len(df) > 0:
            inj = (df["label"] == 1).sum()
            ben = (df["label"] == 0).sum()
            print(f"    {len(df)} rows (injection: {inj}, benign: {ben})")
            raw_counts[df["source"].iloc[0]] = len(df)
            all_dfs.append(df)
        else:
            print("    Empty or missing")

    if not all_dfs:
        print("\nERROR: No datasets loaded!")
        return

    merged = pd.concat(all_dfs, ignore_index=True)

    # Drop empty/NaN texts
    merged = merged[merged["text"].notna() & (merged["text"].str.strip() != "")]
    merged["text"] = merged["text"].str.strip()
    total_raw = len(merged)
    print(f"\n  Total raw: {total_raw}")

    # Step 2: Source-aware exact dedup
    print("\n[2/8] Exact dedup (source-priority)...")
    # Pre-audit: count overlap before dedup removes ShieldLM copies
    overlap_stats = audit_shieldlm_safeguard_overlap(merged)
    merged, exact_removed = dedup_exact_source_aware(merged)
    after_exact = len(merged)
    print(f"  Removed {exact_removed} exact duplicates -> {after_exact} remaining")

    # Step 3: Log ShieldLM-SafeGuard overlap
    print("\n[3/8] ShieldLM-SafeGuard overlap audit...")
    print(f"  Overlap: {overlap_stats['count']} texts ({overlap_stats['pct']}% of SafeGuard)")

    # Step 4: MinHash fuzzy dedup
    print("\n[4/8] MinHash fuzzy dedup (Jaccard>0.8)...")
    merged, minhash_removed = dedup_minhash(merged, threshold=0.8)
    after_minhash = len(merged)
    print(f"  Removed {minhash_removed} near-duplicates -> {after_minhash} remaining")

    # Step 5: Contamination audit vs PINT holdout
    print("\n[5/8] Contamination audit vs PINT holdout...")
    merged, contamination_stats = contamination_audit(merged, HOLDOUT_PATH)

    # Step 6: Class distribution
    print("\n[6/8] Class distribution (NO resampling — focal loss handles imbalance)...")
    inj_count = int((merged["label"] == 1).sum())
    ben_count = int((merged["label"] == 0).sum())
    ratio = round(inj_count / ben_count, 2) if ben_count > 0 else float("inf")
    print(f"  Injection: {inj_count}")
    print(f"  Benign:    {ben_count}")
    print(f"  Ratio:     {ratio}:1")

    # Step 7: Stratified split 80/10/10
    print("\n[7/8] Splitting 80/10/10 (stratified by label)...")
    # Create stratification key from label (source may have too few members for stratification)
    train_df, temp_df = train_test_split(
        merged, test_size=0.2, random_state=42, stratify=merged["label"],
    )
    val_df, test_df = train_test_split(
        temp_df, test_size=0.5, random_state=42, stratify=temp_df["label"],
    )
    print(f"  Train: {len(train_df)}")
    print(f"  Val:   {len(val_df)}")
    print(f"  Test:  {len(test_df)}")

    # Verify all sources in all splits
    for split_name, split_df in [("train", train_df), ("val", val_df), ("test", test_df)]:
        sources = sorted(split_df["source"].unique())
        print(f"  {split_name} sources: {sources}")

    # Step 8: Save
    print("\n[8/8] Saving splits + stats...")
    for name, df in [("train", train_df), ("val", val_df), ("test", test_df)]:
        path = SPLITS_DIR / f"{name}.jsonl"
        df.to_json(str(path), orient="records", lines=True)
        print(f"  Saved: {path}")

    # Per-source stats
    per_source = {}
    for src in merged["source"].unique():
        src_df = merged[merged["source"] == src]
        per_source[src] = {
            "total": int(len(src_df)),
            "injection": int((src_df["label"] == 1).sum()),
            "benign": int((src_df["label"] == 0).sum()),
        }

    stats = {
        "total_raw": total_raw,
        "after_exact_dedup": after_exact,
        "shieldlm_safeguard_overlap": overlap_stats,
        "after_minhash_dedup": after_minhash,
        "contamination": contamination_stats,
        "final_total": len(merged),
        "class_distribution": {
            "injection": inj_count,
            "benign": ben_count,
            "ratio": f"{ratio}:1",
        },
        "per_source": per_source,
        "splits": {
            "train": len(train_df),
            "val": len(val_df),
            "test": len(test_df),
        },
    }

    stats_path = SPLITS_DIR / "stats_report.json"
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"  Saved: {stats_path}")

    print("\n" + "=" * 60)
    print("Dataset preparation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()

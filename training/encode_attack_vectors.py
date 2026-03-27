"""Build expanded attack phrase library and encode with BGE-small-en-v1.5.

Phase 3 of SLM Gauntlet v0.3.0.

Sources (all holdout-safe):
  1. Existing 603 hand-curated phrases (gauntlet/data/attack_phrases.jsonl)
  2. JailbreakBench (HF: JailbreakBench/JBB-Behaviors)
  3. InjecAgent (HF: NirDiamant/InjecAgent or similar)
  4. BIPIA (HF: microsoft/BIPIA)
  5. Neuralchemy + ShieldLM train splits (cluster -> diverse sample)

Output:
  - gauntlet/data/attack_vectors_bge.npy  (N x 384 float32)
  - gauntlet/data/metadata_bge.json       (per-phrase metadata)
  - gauntlet/data/attack_phrases_expanded.jsonl (all phrases for reference)

Usage:
    python training/encode_attack_vectors.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xxhash
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent.parent / "gauntlet" / "data"
SPLITS_DIR = Path(__file__).parent / "splits"
HOLDOUT_PATH = Path(__file__).parent / "holdout_composite.csv"
HF_CACHE = Path(__file__).parent.parent / ".hf_cache"

EXISTING_PHRASES_PATH = DATA_DIR / "attack_phrases.jsonl"
OUTPUT_NPY = DATA_DIR / "attack_vectors_bge.npy"
OUTPUT_META = DATA_DIR / "metadata_bge.json"
OUTPUT_PHRASES = DATA_DIR / "attack_phrases_expanded.jsonl"

BGE_MODEL = "BAAI/bge-small-en-v1.5"
BGE_DIM = 384


# ---------------------------------------------------------------------------
# Load existing phrases
# ---------------------------------------------------------------------------


def load_existing_phrases() -> list[dict]:
    """Load the 603 hand-curated attack phrases."""
    phrases = []
    with open(EXISTING_PHRASES_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                record = json.loads(line)
                phrases.append(
                    {
                        "text": record["text"],
                        "category": record.get("category", "unknown"),
                        "source": "hand_curated",
                        "id": record.get("id", ""),
                    }
                )
    print(f"  Existing hand-curated: {len(phrases)} phrases")
    return phrases


# ---------------------------------------------------------------------------
# External HuggingFace sources
# ---------------------------------------------------------------------------


def load_jailbreakbench() -> list[dict]:
    """Load JailbreakBench attack behaviors from HuggingFace."""
    try:
        from datasets import load_dataset

        ds = load_dataset(
            "JailbreakBench/JBB-Behaviors", "behaviors", split="harmful", cache_dir=str(HF_CACHE)
        )
        phrases = []
        for row in ds:
            # JBB has 'Goal' and 'Behavior' fields
            text = row.get("Goal") or row.get("Behavior") or row.get("text", "")
            if text and len(text.strip()) > 10:
                phrases.append(
                    {
                        "text": text.strip(),
                        "category": "jailbreak",
                        "source": "jailbreakbench",
                        "id": "",
                    }
                )
        print(f"  JailbreakBench: {len(phrases)} phrases")
        return phrases
    except Exception as e:
        print(f"  JailbreakBench: SKIP ({e})")
        return []


def load_injecagent() -> list[dict]:
    """Load InjecAgent indirect injection prompts."""
    try:
        from datasets import load_dataset

        # Try multiple possible dataset names
        for name in ["NirDiamant/InjecAgent", "satml-submission/InjecAgent"]:
            try:
                ds = load_dataset(name, cache_dir=str(HF_CACHE), trust_remote_code=False)
                break
            except Exception:
                continue
        else:
            print("  InjecAgent: SKIP (dataset not found)")
            return []

        phrases = []
        split = list(ds.keys())[0]  # Use first available split
        for row in ds[split]:
            # Look for injection text in various fields
            text = (
                row.get("injected_prompt")
                or row.get("attack_prompt")
                or row.get("prompt")
                or row.get("text", "")
            )
            if text and len(text.strip()) > 10:
                cat = row.get("attack_type", "indirect_injection")
                phrases.append(
                    {
                        "text": text.strip(),
                        "category": f"indirect_injection_{cat}" if cat else "indirect_injection",
                        "source": "injecagent",
                        "id": "",
                    }
                )
        print(f"  InjecAgent: {len(phrases)} phrases")
        return phrases
    except Exception as e:
        print(f"  InjecAgent: SKIP ({e})")
        return []


def load_bipia() -> list[dict]:
    """Load BIPIA indirect injection benchmarks."""
    try:
        from datasets import load_dataset

        ds = load_dataset("microsoft/BIPIA", cache_dir=str(HF_CACHE), trust_remote_code=False)
        phrases = []
        split = list(ds.keys())[0]
        for row in ds[split]:
            text = (
                row.get("injected_prompt")
                or row.get("attack")
                or row.get("prompt")
                or row.get("text", "")
            )
            if text and len(text.strip()) > 10:
                cat = row.get("attack_type", "indirect_injection")
                phrases.append(
                    {
                        "text": text.strip(),
                        "category": f"bipia_{cat}" if cat else "indirect_injection",
                        "source": "bipia",
                        "id": "",
                    }
                )
        print(f"  BIPIA: {len(phrases)} phrases")
        return phrases
    except Exception as e:
        print(f"  BIPIA: SKIP ({e})")
        return []


# ---------------------------------------------------------------------------
# Mine training data for diverse injection phrases
# ---------------------------------------------------------------------------


def mine_training_injections(
    model: SentenceTransformer,
    existing_embeddings: np.ndarray,
    max_per_source: int = 200,
    min_similarity_to_add: float = 0.92,
) -> list[dict]:
    """Mine diverse injection phrases from training data.

    Strategy: For each injection in train split, compute similarity to
    existing library. Only add if max similarity < min_similarity_to_add
    (i.e., it's sufficiently different from what we already have).
    Prioritize underrepresented categories.
    """
    train = pd.read_json(SPLITS_DIR / "train.jsonl", lines=True)
    injections = train[train["label"] == 1].copy()

    print(f"  Training injections available: {len(injections)}")

    # Group by source, sample from each
    phrases = []
    for source in ["neuralchemy", "shieldlm", "safeguard", "slabs"]:
        src_df = injections[injections["source"] == source]
        if len(src_df) == 0:
            continue

        # Sample up to 2x what we need (we'll filter by diversity)
        sample = src_df.sample(n=min(max_per_source * 2, len(src_df)), random_state=42)

        # Encode candidates
        texts = sample["text"].tolist()
        candidate_embs = model.encode(
            texts, normalize_embeddings=True, batch_size=64, show_progress_bar=False
        )

        # Filter: keep only if sufficiently different from existing library
        added = 0
        for i, (text, emb) in enumerate(zip(texts, candidate_embs)):
            if added >= max_per_source:
                break
            if len(text.strip()) < 10:
                continue

            # Max similarity to existing library
            if existing_embeddings.shape[0] > 0:
                sims = existing_embeddings @ emb
                max_sim = float(np.max(sims))
                if max_sim >= min_similarity_to_add:
                    continue  # Too similar to something we already have

            cat = sample.iloc[i].get("attack_category", "unknown")
            if pd.isna(cat) or cat == "None":
                cat = "direct_injection"

            phrases.append(
                {
                    "text": text.strip(),
                    "category": str(cat),
                    "source": f"train_{source}",
                    "id": "",
                }
            )
            added += 1

            # Update existing embeddings for next comparison
            existing_embeddings = np.vstack([existing_embeddings, emb.reshape(1, -1)])

        print(f"    {source}: added {added} diverse phrases")

    print(f"  Training mining total: {len(phrases)} phrases")
    return phrases, existing_embeddings


# ---------------------------------------------------------------------------
# Deduplication & holdout contamination check
# ---------------------------------------------------------------------------


def dedup_phrases(phrases: list[dict]) -> list[dict]:
    """Exact text dedup."""
    seen = set()
    deduped = []
    for p in phrases:
        text_hash = xxhash.xxh64(p["text"].encode("utf-8")).hexdigest()
        if text_hash not in seen:
            seen.add(text_hash)
            deduped.append(p)
    removed = len(phrases) - len(deduped)
    if removed:
        print(f"  Exact dedup removed: {removed}")
    return deduped


def remove_holdout_contamination(phrases: list[dict]) -> list[dict]:
    """Remove any phrases that appear in the holdout set."""
    if not HOLDOUT_PATH.exists():
        print("  WARNING: holdout not found, skipping contamination check")
        return phrases

    holdout = pd.read_csv(HOLDOUT_PATH)
    holdout_hashes = {
        xxhash.xxh64(str(t).strip().encode("utf-8")).hexdigest() for t in holdout["text"]
    }

    clean = []
    removed = 0
    for p in phrases:
        h = xxhash.xxh64(p["text"].encode("utf-8")).hexdigest()
        if h in holdout_hashes:
            removed += 1
        else:
            clean.append(p)

    if removed:
        print(f"  Holdout contamination removed: {removed}")
    else:
        print("  Holdout contamination check: CLEAN")
    return clean


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    print("=" * 60)
    print("Phase 3: Build BGE-small Attack Phrase Library")
    print("=" * 60)

    # Step 1: Load BGE model
    print("\n[1/7] Loading BGE-small model...")
    model = SentenceTransformer(BGE_MODEL, cache_folder=str(HF_CACHE))
    print(f"  Model: {BGE_MODEL} ({BGE_DIM} dims)")

    # Step 2: Load existing phrases
    print("\n[2/7] Loading existing phrases...")
    all_phrases = load_existing_phrases()

    # Step 3: Load external sources
    print("\n[3/7] Loading external HuggingFace sources...")
    all_phrases.extend(load_jailbreakbench())
    all_phrases.extend(load_injecagent())
    all_phrases.extend(load_bipia())

    # Step 4: Dedup and holdout check before mining
    print("\n[4/7] Dedup + holdout check (pre-mining)...")
    all_phrases = dedup_phrases(all_phrases)
    all_phrases = remove_holdout_contamination(all_phrases)
    print(f"  Pre-mining library: {len(all_phrases)} phrases")

    # Encode current library for diversity filtering
    print("\n  Encoding current library for diversity filtering...")
    current_texts = [p["text"] for p in all_phrases]
    current_embeddings = model.encode(
        current_texts,
        normalize_embeddings=True,
        batch_size=64,
        show_progress_bar=True,
    )

    # Step 5: Mine training data for diverse phrases
    print("\n[5/7] Mining training data for diverse phrases...")
    mined_phrases, updated_embeddings = mine_training_injections(
        model, current_embeddings, max_per_source=200, min_similarity_to_add=0.92
    )
    all_phrases.extend(mined_phrases)

    # Final dedup pass
    all_phrases = dedup_phrases(all_phrases)
    all_phrases = remove_holdout_contamination(all_phrases)

    print(f"\n  Final library: {len(all_phrases)} phrases")

    # Category breakdown
    cats = {}
    for p in all_phrases:
        cat = p["category"]
        cats[cat] = cats.get(cat, 0) + 1
    print("\n  Categories:")
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"    {cat}: {count}")

    # Source breakdown
    sources = {}
    for p in all_phrases:
        src = p["source"]
        sources[src] = sources.get(src, 0) + 1
    print("\n  Sources:")
    for src, count in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"    {src}: {count}")

    # Step 6: Encode all phrases
    print("\n[6/7] Encoding all phrases with BGE-small...")
    all_texts = [p["text"] for p in all_phrases]
    all_embeddings = model.encode(
        all_texts,
        normalize_embeddings=True,
        batch_size=64,
        show_progress_bar=True,
    )
    assert all_embeddings.shape == (
        len(all_phrases),
        BGE_DIM,
    ), f"Unexpected shape: {all_embeddings.shape}"
    print(f"  Embeddings shape: {all_embeddings.shape}")

    # Step 7: Save outputs
    print("\n[7/7] Saving outputs...")

    # Save embeddings
    np.save(str(OUTPUT_NPY), all_embeddings.astype(np.float32))
    print(f"  Saved: {OUTPUT_NPY} ({OUTPUT_NPY.stat().st_size / 1024:.0f} KB)")

    # Save metadata
    metadata = {
        "model": BGE_MODEL,
        "dimensions": BGE_DIM,
        "total_phrases": len(all_phrases),
        "patterns": [
            {
                "category": p["category"],
                "subcategory": None,
                "label": p["text"][:80],  # Truncated for metadata, not full text
                "source": p["source"],
            }
            for p in all_phrases
        ],
    }
    with open(OUTPUT_META, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"  Saved: {OUTPUT_META}")

    # Save expanded phrases JSONL
    with open(OUTPUT_PHRASES, "w", encoding="utf-8") as f:
        for p in all_phrases:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"  Saved: {OUTPUT_PHRASES}")

    print("\n" + "=" * 60)
    print(f"Attack phrase library complete: {len(all_phrases)} phrases, {BGE_DIM} dims")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())

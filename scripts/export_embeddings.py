"""Generate real OpenAI embeddings from attack phrases.

Reads attack_phrases.jsonl, batches through OpenAI text-embedding-3-small,
and saves the result as gauntlet/data/embeddings.npz + metadata.json.

Requires: OPENAI_API_KEY environment variable.
Run: python scripts/export_embeddings.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

BATCH_SIZE = 100
MODEL = "text-embedding-3-small"
DATA_DIR = Path(__file__).resolve().parent.parent / "gauntlet" / "data"
PHRASES_PATH = DATA_DIR / "attack_phrases.jsonl"


def load_phrases() -> list[dict]:
    """Load attack phrases from JSONL."""
    phrases = []
    with open(PHRASES_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            phrases.append(json.loads(line))
    return phrases


def embed_batch(client, texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts using OpenAI API."""
    resp = client.embeddings.create(input=texts, model=MODEL)
    return [item.embedding for item in resp.data]


def main() -> None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: Set OPENAI_API_KEY environment variable")
        sys.exit(1)

    try:
        import numpy as np
        from openai import OpenAI
    except ImportError:
        print("ERROR: Install openai and numpy: pip install openai numpy")
        sys.exit(1)

    phrases = load_phrases()
    if not phrases:
        print(f"ERROR: No phrases found in {PHRASES_PATH}")
        sys.exit(1)

    print(f"Loaded {len(phrases)} attack phrases")
    print(f"Model: {MODEL}")
    print(f"Batch size: {BATCH_SIZE}")

    client = OpenAI(api_key=api_key)
    all_embeddings = []
    texts = [p["text"] for p in phrases]

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        print(f"  Embedding batch {i // BATCH_SIZE + 1}/{(len(texts) + BATCH_SIZE - 1) // BATCH_SIZE} ({len(batch)} texts)...")
        embeddings = embed_batch(client, batch)
        all_embeddings.extend(embeddings)

    embeddings_array = np.array(all_embeddings, dtype=np.float32)
    print(f"\nEmbeddings shape: {embeddings_array.shape}")

    # Save embeddings.npz
    npz_path = DATA_DIR / "embeddings.npz"
    np.savez_compressed(npz_path, embeddings=embeddings_array)
    print(f"Saved {npz_path}")

    # Build and save metadata.json
    categories = {}
    for p in phrases:
        cat = p.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    metadata = {
        "version": "0.2.0",
        "model": MODEL,
        "dimensions": embeddings_array.shape[1],
        "count": len(phrases),
        "categories": categories,
        "phrases": [
            {
                "id": p.get("id", f"atk-{i:04d}"),
                "text": p["text"],
                "category": p.get("category", "unknown"),
            }
            for i, p in enumerate(phrases)
        ],
    }

    metadata_path = DATA_DIR / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"Saved {metadata_path}")

    print(f"\nDone! {len(phrases)} attack phrases → {embeddings_array.shape} embeddings")


if __name__ == "__main__":
    main()

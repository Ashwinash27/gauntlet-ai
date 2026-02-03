"""Batch embedding and database insertion utilities for seeding attack embeddings.

This module provides utilities for embedding attack samples in batches
and inserting them into Supabase for Layer 2 detection.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Callable

from openai import AsyncOpenAI
from supabase import AsyncClient

from app.detection.seed_data import AttackSample

logger = logging.getLogger(__name__)

# OpenAI embedding API limits
MAX_BATCH_SIZE = 100  # Max texts per embedding request
MAX_TOKENS_PER_BATCH = 8191  # Approximate token limit


@dataclass
class EmbeddedAttack:
    """An attack sample with its embedding."""

    sample: AttackSample
    embedding: list[float]


async def embed_batch(
    client: AsyncOpenAI,
    texts: list[str],
    model: str = "text-embedding-3-small",
) -> list[list[float]]:
    """
    Generate embeddings for a batch of texts.

    Args:
        client: Async OpenAI client.
        texts: List of texts to embed.
        model: Embedding model to use.

    Returns:
        List of embedding vectors.
    """
    response = await client.embeddings.create(
        model=model,
        input=texts,
    )
    # Return embeddings in the same order as input
    return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]


async def embed_attacks(
    client: AsyncOpenAI,
    attacks: list[AttackSample],
    model: str = "text-embedding-3-small",
    batch_size: int = 50,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[EmbeddedAttack]:
    """
    Generate embeddings for a list of attack samples.

    Args:
        client: Async OpenAI client.
        attacks: List of AttackSample objects.
        model: Embedding model to use.
        batch_size: Number of texts per batch.
        progress_callback: Optional callback(completed, total) for progress updates.

    Returns:
        List of EmbeddedAttack objects.
    """
    embedded = []
    total = len(attacks)

    for i in range(0, total, batch_size):
        batch = attacks[i : i + batch_size]
        texts = [a.text for a in batch]

        embeddings = await embed_batch(client, texts, model)

        for attack, embedding in zip(batch, embeddings):
            embedded.append(EmbeddedAttack(sample=attack, embedding=embedding))

        if progress_callback:
            progress_callback(len(embedded), total)

        # Small delay to avoid rate limits
        if i + batch_size < total:
            await asyncio.sleep(0.1)

    return embedded


async def insert_embeddings(
    client: AsyncClient,
    embedded_attacks: list[EmbeddedAttack],
    batch_size: int = 100,
    progress_callback: Callable[[int, int], None] | None = None,
) -> int:
    """
    Insert embedded attacks into Supabase.

    Args:
        client: Async Supabase client.
        embedded_attacks: List of EmbeddedAttack objects.
        batch_size: Number of rows per insert batch.
        progress_callback: Optional callback(completed, total) for progress updates.

    Returns:
        Number of rows inserted.
    """
    total = len(embedded_attacks)
    inserted = 0

    for i in range(0, total, batch_size):
        batch = embedded_attacks[i : i + batch_size]

        rows = [
            {
                "attack_text": ea.sample.text,
                "embedding": ea.embedding,
                "category": ea.sample.category,
                "subcategory": ea.sample.subcategory,
                "severity": ea.sample.severity,
                "source": ea.sample.source,
                "is_active": True,
            }
            for ea in batch
        ]

        await client.table("attack_embeddings").insert(rows).execute()
        inserted += len(batch)

        if progress_callback:
            progress_callback(inserted, total)

    return inserted


async def clear_embeddings(client: AsyncClient) -> int:
    """
    Delete all attack embeddings from the database.

    Args:
        client: Async Supabase client.

    Returns:
        Number of rows deleted.
    """
    # Delete all rows (Supabase requires a filter, so we use is_active in (true, false))
    result = await client.table("attack_embeddings").delete().gte("severity", 0).execute()
    return len(result.data) if result.data else 0


async def get_embedding_count(client: AsyncClient) -> int:
    """
    Get the count of attack embeddings in the database.

    Args:
        client: Async Supabase client.

    Returns:
        Number of embeddings in the database.
    """
    result = await client.table("attack_embeddings").select("id", count="exact").execute()
    return result.count or 0


async def seed_database(
    openai_client: AsyncOpenAI,
    supabase_client: AsyncClient,
    attacks: list[AttackSample],
    model: str = "text-embedding-3-small",
    clear_existing: bool = False,
    progress_callback: Callable[[str, int, int], None] | None = None,
) -> dict[str, int]:
    """
    Full seeding pipeline: embed attacks and insert into database.

    Args:
        openai_client: Async OpenAI client.
        supabase_client: Async Supabase client.
        attacks: List of AttackSample objects.
        model: Embedding model to use.
        clear_existing: Whether to clear existing embeddings first.
        progress_callback: Optional callback(stage, completed, total) for progress.

    Returns:
        Dict with counts: {"cleared": int, "embedded": int, "inserted": int}
    """
    result = {"cleared": 0, "embedded": 0, "inserted": 0}

    # Clear existing embeddings if requested
    if clear_existing:
        if progress_callback:
            progress_callback("clearing", 0, 1)
        result["cleared"] = await clear_embeddings(supabase_client)
        if progress_callback:
            progress_callback("clearing", 1, 1)

    # Embed attacks
    def embed_progress(completed: int, total: int) -> None:
        if progress_callback:
            progress_callback("embedding", completed, total)

    embedded = await embed_attacks(
        openai_client,
        attacks,
        model=model,
        progress_callback=embed_progress,
    )
    result["embedded"] = len(embedded)

    # Insert into database
    def insert_progress(completed: int, total: int) -> None:
        if progress_callback:
            progress_callback("inserting", completed, total)

    result["inserted"] = await insert_embeddings(
        supabase_client,
        embedded,
        progress_callback=insert_progress,
    )

    return result


__all__ = [
    "EmbeddedAttack",
    "embed_batch",
    "embed_attacks",
    "insert_embeddings",
    "clear_embeddings",
    "get_embedding_count",
    "seed_database",
]

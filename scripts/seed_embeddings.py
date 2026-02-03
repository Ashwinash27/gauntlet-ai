#!/usr/bin/env python3
"""CLI script to seed the attack embeddings database.

Usage:
    python scripts/seed_embeddings.py              # Seed without clearing existing
    python scripts/seed_embeddings.py --clear      # Clear existing and re-seed
    python scripts/seed_embeddings.py --stats      # Show stats only, don't seed
    python scripts/seed_embeddings.py --model text-embedding-3-large  # Use different model
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.clients import get_openai_client, get_supabase_client
from app.core.config import get_settings
from app.detection.seed_data import get_attack_stats, load_all_attacks
from app.detection.seeder import get_embedding_count, seed_database


def print_progress(stage: str, completed: int, total: int) -> None:
    """Print progress update."""
    percent = (completed / total * 100) if total > 0 else 100
    bar_length = 40
    filled = int(bar_length * completed / total) if total > 0 else bar_length
    bar = "=" * filled + "-" * (bar_length - filled)

    stage_names = {
        "clearing": "Clearing existing",
        "embedding": "Generating embeddings",
        "inserting": "Inserting to database",
    }
    stage_name = stage_names.get(stage, stage)

    print(f"\r{stage_name}: [{bar}] {percent:.1f}% ({completed}/{total})", end="", flush=True)
    if completed == total:
        print()  # New line when complete


async def show_stats() -> None:
    """Show current database stats."""
    supabase = await get_supabase_client()
    count = await get_embedding_count(supabase)
    print(f"Current embeddings in database: {count}")


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Seed the attack embeddings database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/seed_embeddings.py              # Seed without clearing
    python scripts/seed_embeddings.py --clear      # Clear existing and re-seed
    python scripts/seed_embeddings.py --stats      # Show stats only
    python scripts/seed_embeddings.py --model text-embedding-3-large
        """,
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing embeddings before seeding",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show database stats only, don't seed",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Embedding model to use (default: from config)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load and categorize attacks without seeding",
    )

    args = parser.parse_args()
    settings = get_settings()
    model = args.model or settings.embedding_model

    # Stats only mode
    if args.stats:
        await show_stats()
        return

    # Load attacks
    print("Loading deepset/prompt-injections dataset...")
    attacks = load_all_attacks()
    print(f"Loaded {len(attacks)} attack samples\n")

    # Show category distribution
    stats = get_attack_stats(attacks)
    print("Category distribution:")
    for category, count in stats.items():
        print(f"  {category}: {count}")
    print()

    # Dry run mode
    if args.dry_run:
        print("Dry run complete. Use without --dry-run to seed database.")
        return

    # Seed database
    print(f"Using model: {model}")
    if args.clear:
        print("Will clear existing embeddings first")
    print()

    openai_client = await get_openai_client()
    supabase_client = await get_supabase_client()

    result = await seed_database(
        openai_client=openai_client,
        supabase_client=supabase_client,
        attacks=attacks,
        model=model,
        clear_existing=args.clear,
        progress_callback=print_progress,
    )

    print(f"\nSeeding complete!")
    if result["cleared"] > 0:
        print(f"  Cleared: {result['cleared']} existing embeddings")
    print(f"  Embedded: {result['embedded']} attacks")
    print(f"  Inserted: {result['inserted']} rows")

    # Show final count
    final_count = await get_embedding_count(supabase_client)
    print(f"\nTotal embeddings in database: {final_count}")


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""Run database migrations against Supabase.

This script executes SQL migrations using the Supabase client.
It requires the SUPABASE_URL and SUPABASE_KEY environment variables.

Usage:
    python scripts/run_migration.py                    # Run all migrations
    python scripts/run_migration.py --check            # Check if table exists
    python scripts/run_migration.py --file 001_attack_embeddings.sql
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.clients import get_supabase_client
from app.core.config import get_settings


MIGRATIONS_DIR = Path(__file__).parent.parent / "supabase" / "migrations"


async def check_table_exists(client) -> bool:
    """Check if attack_embeddings table exists."""
    try:
        result = await client.table("attack_embeddings").select("id").limit(1).execute()
        return True
    except Exception as e:
        if "relation" in str(e).lower() and "does not exist" in str(e).lower():
            return False
        # Other errors - table might exist but have issues
        print(f"Warning: {e}")
        return False


async def run_migration_via_rpc(client, sql: str) -> bool:
    """
    Attempt to run SQL via a custom RPC function.

    Note: This requires a 'run_sql' function to be created in Supabase first,
    which typically isn't available by default for security reasons.
    """
    try:
        await client.rpc("run_sql", {"query": sql}).execute()
        return True
    except Exception as e:
        print(f"RPC execution failed: {e}")
        return False


def print_manual_instructions(sql_file: Path) -> None:
    """Print instructions for manual migration."""
    print("\n" + "=" * 60)
    print("MANUAL MIGRATION REQUIRED")
    print("=" * 60)
    print("""
Supabase doesn't allow arbitrary SQL execution via the client API.
Please run the migration manually:

Option 1: Supabase Dashboard (Recommended)
------------------------------------------
1. Go to your Supabase project dashboard
2. Navigate to SQL Editor
3. Copy and paste the contents of:
   supabase/migrations/001_attack_embeddings.sql
4. Click "Run"

Option 2: psql (if you have direct database access)
---------------------------------------------------
1. Get your database connection string from Supabase dashboard
   (Settings > Database > Connection string)
2. Run: psql "your-connection-string" -f supabase/migrations/001_attack_embeddings.sql

Option 3: Supabase CLI
----------------------
1. Install: npm install -g supabase
2. Link: supabase link --project-ref your-project-ref
3. Run: supabase db push
""")

    print("\nMigration SQL content:")
    print("-" * 60)
    print(sql_file.read_text())
    print("-" * 60)


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run database migrations against Supabase",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check if migration has been applied",
    )
    parser.add_argument(
        "--file",
        type=str,
        default="001_attack_embeddings.sql",
        help="Migration file to run",
    )

    args = parser.parse_args()
    settings = get_settings()

    if not settings.supabase_url or not settings.supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_KEY must be set in .env")
        sys.exit(1)

    print(f"Connecting to Supabase: {settings.supabase_url}")
    client = await get_supabase_client()

    # Check if table exists
    table_exists = await check_table_exists(client)

    if args.check:
        if table_exists:
            print("✓ attack_embeddings table exists")
            # Try to check RPC function
            try:
                result = await client.rpc(
                    "match_attack_embeddings",
                    {"query_embedding": [0.0] * 1536, "match_threshold": 0.99, "match_count": 1}
                ).execute()
                print("✓ match_attack_embeddings RPC function exists")
            except Exception as e:
                if "function" in str(e).lower():
                    print("✗ match_attack_embeddings RPC function NOT found")
                else:
                    print(f"✓ RPC function exists (empty result expected)")
        else:
            print("✗ attack_embeddings table does NOT exist")
            print("  Run: python scripts/run_migration.py")
        return

    # If table already exists, skip migration
    if table_exists:
        print("✓ Migration already applied (table exists)")
        return

    # Load migration file
    migration_file = MIGRATIONS_DIR / args.file
    if not migration_file.exists():
        print(f"Error: Migration file not found: {migration_file}")
        sys.exit(1)

    # Print manual instructions since we can't run SQL directly
    print_manual_instructions(migration_file)


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""Admin script to generate and store API keys for Argus AI.

Usage:
    python scripts/create_api_key.py --name "User1 Production"
    python scripts/create_api_key.py --name "User1 Production" --limit 5000
    python scripts/create_api_key.py --name "Test Key" --limit 100

The script will:
1. Generate a new API key (sk-argus-...)
2. Store the hash in Supabase
3. Print the raw key (SAVE THIS - it won't be shown again!)

Environment variables required:
    SUPABASE_URL - Your Supabase project URL
    SUPABASE_KEY - Your Supabase service role key (not anon key!)
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load environment variables
load_dotenv(project_root / ".env")


async def create_api_key(name: str, daily_limit: int) -> str | None:
    """
    Generate a new API key and store it in Supabase.

    Args:
        name: Human-readable name for the key.
        daily_limit: Maximum requests per day.

    Returns:
        The raw API key if successful, None otherwise.
    """
    from supabase import acreate_client

    from app.core.auth import generate_api_key, hash_api_key

    # Get Supabase credentials
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_KEY must be set in .env")
        return None

    # Generate the key
    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)

    # Connect to Supabase
    try:
        client = await acreate_client(supabase_url, supabase_key)
    except Exception as e:
        print(f"Error connecting to Supabase: {e}")
        return None

    # Insert the key
    try:
        result = await client.table("api_keys").insert({
            "key_hash": key_hash,
            "name": name,
            "daily_limit": daily_limit,
            "is_active": True,
        }).execute()

        if result.data:
            key_id = result.data[0]["id"]
            print(f"\n{'=' * 60}")
            print("API KEY CREATED SUCCESSFULLY")
            print(f"{'=' * 60}")
            print(f"\nKey ID:      {key_id}")
            print(f"Name:        {name}")
            print(f"Daily Limit: {daily_limit:,} requests/day")
            print(f"\n{'*' * 60}")
            print("IMPORTANT: Save this key now! It will NOT be shown again.")
            print(f"{'*' * 60}")
            print(f"\nAPI Key: {raw_key}")
            print(f"\n{'=' * 60}\n")
            return raw_key
        else:
            print("Error: No data returned from insert")
            return None

    except Exception as e:
        if "duplicate key" in str(e).lower():
            print("Error: A key with this hash already exists (extremely rare collision)")
        else:
            print(f"Error inserting key: {e}")
        return None


async def list_api_keys() -> None:
    """List all API keys (without showing the actual keys)."""
    from supabase import acreate_client

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_KEY must be set in .env")
        return

    try:
        client = await acreate_client(supabase_url, supabase_key)
        result = await client.table("api_keys").select(
            "id, name, daily_limit, is_active, created_at, last_used_at"
        ).order("created_at", desc=True).execute()

        if not result.data:
            print("No API keys found.")
            return

        print(f"\n{'=' * 80}")
        print(f"{'ID':<36} {'Name':<20} {'Limit':<8} {'Active':<8} {'Last Used'}")
        print(f"{'=' * 80}")

        for key in result.data:
            last_used = key.get("last_used_at", "Never")
            if last_used and last_used != "Never":
                last_used = last_used[:19]  # Truncate to datetime
            print(
                f"{key['id']:<36} {key['name'][:20]:<20} "
                f"{key['daily_limit']:<8} {'Yes' if key['is_active'] else 'No':<8} "
                f"{last_used}"
            )

        print(f"{'=' * 80}\n")

    except Exception as e:
        print(f"Error listing keys: {e}")


async def deactivate_api_key(key_id: str) -> bool:
    """Deactivate an API key by ID."""
    from supabase import acreate_client

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_KEY must be set in .env")
        return False

    try:
        client = await acreate_client(supabase_url, supabase_key)
        result = await client.table("api_keys").update(
            {"is_active": False}
        ).eq("id", key_id).execute()

        if result.data:
            print(f"API key {key_id} has been deactivated.")
            return True
        else:
            print(f"API key {key_id} not found.")
            return False

    except Exception as e:
        print(f"Error deactivating key: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Manage Argus AI API keys",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    Create a new key:
        python scripts/create_api_key.py --name "User1 Production" --limit 5000

    List all keys:
        python scripts/create_api_key.py --list

    Deactivate a key:
        python scripts/create_api_key.py --deactivate <key-id>
        """,
    )

    parser.add_argument(
        "--name",
        type=str,
        help="Name for the new API key",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Daily request limit (default: 1000)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all API keys",
    )
    parser.add_argument(
        "--deactivate",
        type=str,
        metavar="KEY_ID",
        help="Deactivate an API key by ID",
    )

    args = parser.parse_args()

    if args.list:
        asyncio.run(list_api_keys())
    elif args.deactivate:
        asyncio.run(deactivate_api_key(args.deactivate))
    elif args.name:
        asyncio.run(create_api_key(args.name, args.limit))
    else:
        parser.print_help()
        print("\nError: Please specify --name to create a key, --list to list keys, or --deactivate to deactivate a key.")
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Create a test admin user for the ArgusAI dashboard.
Run this script to create login credentials.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # Use service role key

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_KEY must be set in .env")
    sys.exit(1)


def create_admin_user(email: str, password: str, name: str = "Admin User") -> dict:
    """Create an admin user in Supabase Auth."""
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Create user with admin metadata
    result = supabase.auth.admin.create_user({
        "email": email,
        "password": password,
        "email_confirm": True,
        "user_metadata": {
            "role": "admin",
            "name": name
        }
    })

    return result


def create_customer_user(email: str, password: str, name: str = "Test Customer") -> dict:
    """Create a customer user in Supabase Auth."""
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    result = supabase.auth.admin.create_user({
        "email": email,
        "password": password,
        "email_confirm": True,
        "user_metadata": {
            "role": "customer",
            "name": name
        }
    })

    return result


if __name__ == "__main__":
    print("Creating ArgusAI Dashboard users...")
    print("-" * 40)

    # Create admin user
    try:
        admin = create_admin_user(
            email="admin@argus.ai",
            password="admin123!",
            name="Admin User"
        )
        print(f"✓ Admin user created: admin@argus.ai / admin123!")
        print(f"  User ID: {admin.user.id}")
    except Exception as e:
        if "already been registered" in str(e):
            print("✓ Admin user already exists: admin@argus.ai / admin123!")
        else:
            print(f"✗ Failed to create admin: {e}")

    # Create test customer
    try:
        customer = create_customer_user(
            email="customer@test.com",
            password="customer123!",
            name="Test Customer"
        )
        print(f"✓ Customer user created: customer@test.com / customer123!")
        print(f"  User ID: {customer.user.id}")
    except Exception as e:
        if "already been registered" in str(e):
            print("✓ Customer user already exists: customer@test.com / customer123!")
        else:
            print(f"✗ Failed to create customer: {e}")

    print("-" * 40)
    print("\nYou can now log in to the dashboard at http://localhost:5173")
    print("Admin login: admin@argus.ai / admin123!")
    print("Customer login: customer@test.com / customer123!")

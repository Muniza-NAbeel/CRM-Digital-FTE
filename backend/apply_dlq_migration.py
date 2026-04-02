#!/usr/bin/env python3
"""
Apply Dead Letter Queue (DLQ) migration.

Usage:
    uv run python apply_dlq_migration.py
"""

import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()


async def apply_migration():
    """Apply the DLQ migration."""

    db_url = os.getenv("APP_DATABASE_URL")
    if not db_url:
        print("❌ APP_DATABASE_URL not configured")
        return False

    asyncpg_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    print("=" * 60)
    print("Dead Letter Queue (DLQ) Migration")
    print("=" * 60)
    print(f"\nConnecting to database...")

    try:
        conn = await asyncpg.connect(asyncpg_url)
        print("✓ Database connected")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

    # Check if table already exists
    print("\nChecking existing tables...")
    
    tables = await conn.fetch("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'dead_letter_queue'
    """)

    if tables:
        print("✓ Table 'dead_letter_queue' already exists")
        migration_applied = False
    else:
        print("Creating table 'dead_letter_queue'...")
        
        # Read migration SQL file
        migration_path = os.path.join(os.path.dirname(__file__), 
                                      "database", "migrations", "003_create_dead_letter_queue.sql")
        
        try:
            with open(migration_path, 'r') as f:
                migration_sql = f.read()
            
            await conn.execute(migration_sql)
            print("✓ Table 'dead_letter_queue' created successfully")
            print("✓ Indexes created")
            print("✓ Triggers created for auto-categorization")
            print("✓ Views created: v_dlq_pending_review, v_dlq_analytics")
            migration_applied = True
            
        except FileNotFoundError:
            print("❌ Migration SQL file not found")
            await conn.close()
            return False
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            await conn.close()
            return False

    await conn.close()
    print("\n" + "=" * 60)

    if migration_applied:
        print("✅ DLQ migration completed successfully!")
        print("\nThe dead_letter_queue table is now ready.")
        print("Failed messages after 3 retries will be automatically moved to DLQ.")
    else:
        print("✅ Database was already up-to-date.")

    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(apply_migration())
    if not success:
        exit(1)

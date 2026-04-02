#!/usr/bin/env python3
"""
Apply retry system migration to message_queue table.

Usage:
    uv run python apply_retry_migration.py
"""

import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()


async def apply_migration():
    """Apply the retry system migration."""
    
    db_url = os.getenv("APP_DATABASE_URL")
    if not db_url:
        print("❌ APP_DATABASE_URL not configured")
        return False
    
    asyncpg_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    print(f"Connecting to database...")
    
    try:
        conn = await asyncpg.connect(asyncpg_url)
        print("✓ Database connected")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    # Check if columns already exist
    print("Checking existing columns...")
    
    columns = await conn.fetch("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'message_queue' 
        ORDER BY column_name
    """)
    
    existing_cols = {row['column_name'] for row in columns}
    
    # Columns to add
    columns_to_add = [
        ("retry_count", "INTEGER DEFAULT 0"),
        ("last_retry_at", "TIMESTAMP WITH TIME ZONE"),
    ]
    
    migration_applied = False
    
    for col_name, col_type in columns_to_add:
        if col_name in existing_cols:
            print(f"✓ Column '{col_name}' already exists")
        else:
            print(f"Adding column '{col_name}' ({col_type})...")
            try:
                await conn.execute(f"ALTER TABLE message_queue ADD COLUMN {col_name} {col_type}")
                print(f"✓ Column '{col_name}' added successfully")
                migration_applied = True
            except Exception as e:
                print(f"❌ Failed to add '{col_name}': {e}")
    
    # Create index
    print("\nCreating index...")
    try:
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_message_queue_retry 
            ON message_queue (status, retry_count, created_at)
        """)
        print("✓ Index 'idx_message_queue_retry' created/exists")
        migration_applied = True
    except Exception as e:
        print(f"⚠ Index warning: {e}")
    
    # Add comments
    print("\nAdding column comments...")
    try:
        await conn.execute("COMMENT ON COLUMN message_queue.retry_count IS 'Number of retry attempts (max 3)'")
        await conn.execute("COMMENT ON COLUMN message_queue.last_retry_at IS 'Timestamp of last retry attempt'")
        print("✓ Comments added")
    except Exception as e:
        print(f"⚠ Comments warning: {e}")
    
    await conn.close()
    print("\n" + "=" * 50)
    
    if migration_applied:
        print("✅ Retry system migration completed!")
        print("The message_queue table now has retry tracking.")
    else:
        print("✅ Database was already up-to-date.")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(apply_migration())
    if not success:
        exit(1)

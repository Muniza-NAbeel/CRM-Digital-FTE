#!/usr/bin/env python3
"""
Apply database migration to add missing columns to message_queue table.

Usage:
    uv run python apply_migration.py
"""

import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()


async def apply_migration():
    """Apply the message_queue migration."""
    
    db_url = os.getenv("APP_DATABASE_URL")
    if not db_url:
        print("❌ APP_DATABASE_URL not configured")
        return False
    
    # Convert to asyncpg format
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
    print(f"Existing columns: {sorted(existing_cols)}")
    
    # Columns to add
    columns_to_add = [
        ("response", "TEXT"),
        ("sentiment", "VARCHAR(50)"),
        ("is_escalated", "BOOLEAN DEFAULT FALSE"),
        ("escalation_reason", "VARCHAR(100)"),
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
    
    # Create indexes if they don't exist
    print("\nCreating indexes...")
    
    indexes = [
        "idx_message_queue_sentiment",
        "idx_message_queue_escalated",
    ]
    
    for idx_name in indexes:
        try:
            await conn.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON message_queue (sentiment)")
            print(f"✓ Index '{idx_name}' created/exists")
        except Exception as e:
            print(f"⚠ Index '{idx_name}' warning: {e}")
    
    # Special index for is_escalated
    try:
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_message_queue_escalated 
            ON message_queue (is_escalated) WHERE is_escalated = TRUE
        """)
        print("✓ Index 'idx_message_queue_escalated' created/exists")
    except Exception as e:
        print(f"⚠ Index warning: {e}")
    
    # Add comments
    print("\nAdding column comments...")
    
    try:
        await conn.execute("COMMENT ON COLUMN message_queue.response IS 'AI-generated response sent to customer'")
        await conn.execute("COMMENT ON COLUMN message_queue.sentiment IS 'Detected sentiment: positive, negative, neutral'")
        await conn.execute("COMMENT ON COLUMN message_queue.is_escalated IS 'Whether the ticket requires human escalation'")
        await conn.execute("COMMENT ON COLUMN message_queue.escalation_reason IS 'Reason for escalation if applicable'")
        print("✓ Comments added")
    except Exception as e:
        print(f"⚠ Comments warning: {e}")
    
    await conn.close()
    print("\n" + "=" * 50)
    
    if migration_applied:
        print("✅ Migration completed successfully!")
        print("The message_queue table now has all required columns.")
    else:
        print("✅ Database was already up-to-date.")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(apply_migration())
    if not success:
        exit(1)

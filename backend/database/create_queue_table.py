"""Create message_queue table in database."""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    db_url = os.getenv("APP_DATABASE_URL")
    if not db_url:
        print("No database URL found")
        return
    
    # Convert to asyncpg format
    asyncpg_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    print(f"Connecting to database...")
    conn = await asyncpg.connect(asyncpg_url)
    
    sql_path = os.path.join(os.path.dirname(__file__), "add_message_queue.sql")
    with open(sql_path, "r") as f:
        sql = f.read()
    
    print("Creating message_queue table...")
    await conn.execute(sql)
    print("✓ Table created successfully!")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())

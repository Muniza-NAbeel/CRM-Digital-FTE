import asyncio
import asyncpg
import os
import json
from dotenv import load_dotenv

load_dotenv()

async def check():
    conn = await asyncpg.connect(
        os.getenv('APP_DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')
    )
    
    r = await conn.fetchrow(
        'SELECT customer_email, metadata, channel FROM message_queue WHERE request_id = $1',
        'f083b365-b34f-46a4-9cc2-fd4736e5c76c'
    )
    
    print("="*60)
    print("MESSAGE QUEUE RECORD:")
    print("="*60)
    print(f"customer_email: {r['customer_email']}")
    print(f"channel: {r['channel']}")
    print(f"metadata: {json.dumps(r['metadata'], indent=2)}")
    
    # Check for phone number in metadata
    metadata = r['metadata']
    if isinstance(metadata, str):
        metadata = json.loads(metadata)
    
    phone = metadata.get('customer_phone')
    print(f"\ncustomer_phone in metadata: {phone}")
    
    await conn.close()

if __name__ == '__main__':
    asyncio.run(check())

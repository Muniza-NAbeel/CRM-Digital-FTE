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
    
    # Check message queue
    r = await conn.fetchrow(
        'SELECT request_id, customer_email, channel, status, metadata FROM message_queue WHERE request_id = $1',
        '9d6382a4-655a-4e93-a5d3-453a61b50d6a'
    )
    
    print("="*60)
    print("MESSAGE QUEUE:")
    print("="*60)
    print(f"request_id: {r['request_id']}")
    print(f"customer_email: {r['customer_email']}")
    print(f"channel: {r['channel']}")
    print(f"status: {r['status']}")
    
    metadata = r['metadata']
    if isinstance(metadata, str):
        metadata = json.loads(metadata)
    
    print(f"customer_phone in metadata: {metadata.get('customer_phone')}")
    
    # Check messages
    print("\n" + "="*60)
    print("CONVERSATION MESSAGES:")
    print("="*60)
    
    # Get conversation ID from ticket
    ticket = await conn.fetchrow(
        'SELECT id FROM tickets WHERE ticket_number = $1', 'CS-2026-22179'
    )
    
    if ticket:
        msgs = await conn.fetch(
            'SELECT content, direction, channel FROM messages WHERE ticket_id = $1 ORDER BY created_at',
            ticket['id']
        )
        for m in msgs:
            direction = "OUTBOUND" if m['direction'] == 'outbound' else "INBOUND"
            print(f"{direction} | {m['channel']} | {m['content'][:80]}...")
    
    await conn.close()

if __name__ == '__main__':
    asyncio.run(check())

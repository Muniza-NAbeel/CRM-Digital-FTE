import asyncpg
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def check():
    db_url = os.getenv('APP_DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(db_url)
    
    print("="*70)
    print("LAST 5 MESSAGES IN QUEUE:")
    print("="*70)
    rows = await conn.fetch(
        'SELECT request_id, customer_email, subject, status, ticket_id, created_at '
        'FROM message_queue ORDER BY created_at DESC LIMIT 5'
    )
    for r in rows:
        print(f"  {r['request_id'][:8]}... | {r['customer_email']} | {r['subject'][:30]} | status={r['status']} | ticket_id={r['ticket_id']}")
    
    print("\n" + "="*70)
    print("LAST 5 TICKETS:")
    print("="*70)
    tickets = await conn.fetch(
        'SELECT id, ticket_number, subject, status, customer_id, created_at '
        'FROM tickets ORDER BY created_at DESC LIMIT 5'
    )
    for t in tickets:
        print(f"  ID={t['id']} | {t['ticket_number']} | {t['subject'][:30]} | status={t['status']}")
    
    print("\n" + "="*70)
    print("LAST 5 CONVERSATIONS:")
    print("="*70)
    convs = await conn.fetch(
        'SELECT id, ticket_id, status FROM conversations ORDER BY created_at DESC LIMIT 5'
    )
    for c in convs:
        print(f"  ID={c['id']} | ticket_id={c['ticket_id']} | status={c['status']}")
    
    print("\n" + "="*70)
    print("LAST 10 MESSAGES (conversation):")
    print("="*70)
    msgs = await conn.fetch(
        'SELECT id, conversation_id, content, direction, created_at '
        'FROM messages ORDER BY created_at DESC LIMIT 10'
    )
    for m in msgs:
        direction = "OUTBOUND" if m['direction'] == 'outbound' else "INBOUND"
        print(f"  {direction} | conv_id={m['conversation_id']} | {m['content'][:50]}...")
    
    await conn.close()

if __name__ == '__main__':
    asyncio.run(check())

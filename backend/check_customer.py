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
    
    # Check customer record
    customer = await conn.fetchrow(
        "SELECT * FROM customers WHERE phone = $1 OR email = $2",
        '+923128818931',
        'whatsapp_923128818931@channel.internal'
    )
    
    print("="*60)
    print("CUSTOMER RECORD:")
    print("="*60)
    if customer:
        print(f"id: {customer['id']}")
        print(f"email: {customer['email']}")
        print(f"phone: {customer['phone']}")
        print(f"full_name: {customer['full_name']}")
        print(f"preferred_channel: {customer['preferred_channel']}")
    else:
        print("Customer not found!")
    
    await conn.close()

if __name__ == '__main__':
    asyncio.run(check())

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def fix():
    conn = await asyncpg.connect(
        os.getenv('APP_DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')
    )
    
    # Update customer phone
    result = await conn.execute(
        "UPDATE customers SET phone = '+923128818931' WHERE email = 'whatsapp_923128818931@channel.internal'"
    )
    print(f'Customer phone updated! Rows affected: {result}')
    
    await conn.close()

if __name__ == '__main__':
    asyncio.run(fix())

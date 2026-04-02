import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test():
    from src.channels.whatsapp_handler import WhatsAppResponseSender
    
    sender = WhatsAppResponseSender(
        os.getenv('APP_TWILIO_ACCOUNT_SID'),
        os.getenv('APP_TWILIO_AUTH_TOKEN'),
        os.getenv('APP_TWILIO_WHATSAPP_NUMBER')
    )
    
    result = await sender.send_message(
        '+923128818931',
        '🧪 Direct test message from Customer Success FTE - Please ignore'
    )
    
    print('Result:', result)
    
    if isinstance(result, list) and len(result) > 0:
        first = result[0]
        if first.get('success'):
            print('\n✅ Message sent!')
            print(f"   SID: {first.get('message_sid')}")
            print(f"   Status: {first.get('status')}")
        else:
            print(f"\n❌ Send failed: {first.get('error')}")

if __name__ == '__main__':
    asyncio.run(test())

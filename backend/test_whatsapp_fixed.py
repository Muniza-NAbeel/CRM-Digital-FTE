"""
Test WhatsApp send - Fixed version
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_whatsapp_send():
    from src.channels.whatsapp_handler import WhatsAppResponseSender
    
    # Load credentials
    twilio_sid = os.getenv("APP_TWILIO_ACCOUNT_SID")
    twilio_token = os.getenv("APP_TWILIO_AUTH_TOKEN")
    twilio_number = os.getenv("APP_TWILIO_WHATSAPP_NUMBER")
    
    print("="*60)
    print("TWILIO CREDENTIALS CHECK")
    print("="*60)
    print(f"Account SID: {twilio_sid}")
    print(f"Auth Token: {twilio_token[:10]}...")
    print(f"WhatsApp Number: {twilio_number}")
    
    if not all([twilio_sid, twilio_token, twilio_number]):
        print("\n❌ Missing Twilio credentials!")
        return
    
    print("\n" + "="*60)
    print("TESTING WHATSAPP SEND")
    print("="*60)
    
    sender = WhatsAppResponseSender(
        account_sid=twilio_sid,
        auth_token=twilio_token,
        from_number=twilio_number,
    )
    
    # Send test message
    test_number = "+923128818931"
    test_message = "Test from Customer Success FTE"
    
    print(f"Sending to: {test_number}")
    print(f"From: {twilio_number}")
    print(f"Message: {test_message}")
    print()
    
    result = await sender.send_message(test_number, test_message)
    
    print("Result:")
    print(result)
    
    if isinstance(result, list) and len(result) > 0:
        first = result[0]
        if first.get('success'):
            print("\n✅ WhatsApp message sent successfully!")
            print(f"   Message SID: {first.get('message_sid')}")
            print(f"   Status: {first.get('status')}")
            print("\n⚠️  IMPORTANT: Check your WhatsApp!")
            print("   If you haven't joined the Twilio sandbox, you won't receive messages.")
            print(f"   Send 'join {twilio_number.split(':')[-1]}' to +14155238886 on WhatsApp")
        else:
            print(f"\n❌ WhatsApp send failed: {first.get('error')}")
    else:
        print("\n❌ Unexpected result format")

if __name__ == '__main__':
    asyncio.run(test_whatsapp_send())

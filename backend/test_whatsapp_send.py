"""
Test WhatsApp send directly
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
    print(f"Account SID: {twilio_sid[:10] if twilio_sid else 'NONE'}...")
    print(f"Auth Token: {twilio_token[:10] if twilio_token else 'NONE'}...")
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
    test_message = "🧪 Test message from Customer Success FTE - This is a test to verify WhatsApp integration."
    
    print(f"Sending to: {test_number}")
    print(f"Message: {test_message}")
    
    result = await sender.send_message(test_number, test_message)
    
    print(f"\nResult: {result}")
    
    if result.get('success'):
        print("\n✅ WhatsApp message sent successfully!")
        print(f"   SID: {result.get('sid')}")
        print(f"   Status: {result.get('status')}")
    else:
        print(f"\n❌ WhatsApp send failed: {result.get('error')}")

if __name__ == '__main__':
    asyncio.run(test_whatsapp_send())

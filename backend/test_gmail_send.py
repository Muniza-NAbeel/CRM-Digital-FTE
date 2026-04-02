"""
Test Gmail sending directly
"""
import asyncio
import os
import pickle
from dotenv import load_dotenv

load_dotenv()

async def test_gmail_send():
    from src.channels.gmail_handler import GmailResponseSender
    
    # Load credentials
    gmail_client_id = os.getenv("APP_GMAIL_CLIENT_ID")
    gmail_client_secret = os.getenv("APP_GMAIL_CLIENT_SECRET")
    gmail_refresh_token = os.getenv("APP_GMAIL_REFRESH_TOKEN")
    gmail_sender_email = os.getenv("APP_GMAIL_SENDER_EMAIL")
    
    print("="*60)
    print("GMAIL CREDENTIALS CHECK")
    print("="*60)
    print(f"Client ID: {gmail_client_id[:20]}...")
    print(f"Client Secret: {gmail_client_secret[:10]}...")
    print(f"Refresh Token: {gmail_refresh_token[:20] if gmail_refresh_token else 'NONE'}...")
    print(f"Sender Email: {gmail_sender_email}")
    
    if not all([gmail_client_id, gmail_client_secret, gmail_refresh_token, gmail_sender_email]):
        print("\n❌ Missing credentials!")
        return
    
    # Load token.json to verify refresh token
    token_path = os.path.join(os.path.dirname(__file__), 'token.json')
    if os.path.exists(token_path):
        with open(token_path, 'rb') as f:
            creds = pickle.load(f)
        print(f"\nToken.json refresh_token: {creds.refresh_token[:20] if creds.refresh_token else 'NONE'}...")
    
    print("\n" + "="*60)
    print("TESTING GMAIL SEND")
    print("="*60)
    
    sender = GmailResponseSender(
        client_id=gmail_client_id,
        client_secret=gmail_client_secret,
        refresh_token=gmail_refresh_token,
        sender_email=gmail_sender_email,
    )
    
    # Send test email
    result = await sender.send_reply(
        to_email=gmail_sender_email,  # Send to self for testing
        subject="Test Email from Customer Success FTE",
        content="This is a test email to verify Gmail API integration is working correctly.",
    )
    
    print(f"\nResult: {result}")
    
    if result.get("success"):
        print("\n✅ Email sent successfully!")
        print(f"   Message ID: {result.get('message_id')}")
    else:
        print(f"\n❌ Email send failed: {result.get('error')}")

if __name__ == '__main__':
    asyncio.run(test_gmail_send())

# WhatsApp & Gmail Integration Testing Guide

## Overview

This guide provides comprehensive testing instructions for the WhatsApp (Twilio) and Gmail integrations in the Customer Success Digital FTE system.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [WhatsApp Integration Testing](#whatsapp-integration-testing)
3. [Gmail Integration Testing](#gmail-integration-testing)
4. [API Testing](#api-testing)
5. [Webhook Testing](#webhook-testing)
6. [Multi-Channel Testing](#multi-channel-testing)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Environment Setup

Ensure your `.env` file contains the required credentials:

```bash
# WhatsApp (Twilio)
APP_TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
APP_TWILIO_AUTH_TOKEN="your_auth_token"
APP_TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Gmail
APP_GMAIL_CLIENT_ID="your_client_id.apps.googleusercontent.com"
APP_GMAIL_CLIENT_SECRET="your_client_secret"
APP_GMAIL_REFRESH_TOKEN="your_refresh_token"
APP_GMAIL_SENDER_EMAIL=support@yourdomain.com
APP_GMAIL_POLLING_ENABLED=false
APP_GMAIL_PUBSUB_ENABLED=false
```

### Backend Running

```bash
cd backend
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Running (for web form testing)

```bash
cd frontend/web-form
npm run dev
```

---

## WhatsApp Integration Testing

### 1. Twilio Sandbox Setup

#### Option A: Using Twilio Sandbox (Recommended for Testing)

1. **Connect to Sandbox**:
   - Go to Twilio Console → Messaging → Try it out → Send a WhatsApp message
   - Scan the QR code or send "join <keyword>" to the sandbox number
   - Note the sandbox WhatsApp number (e.g., `whatsapp:+14155238886`)

2. **Configure Webhook**:
   ```bash
   # In Twilio Console → Messaging → Settings → WhatsApp Sender Settings
   # Set webhook URL to:
   https://your-domain.com/webhooks/whatsapp
   ```

3. **For Local Testing with ngrok**:
   ```bash
   # Install ngrok
   ngrok http 8000
   
   # Use the ngrok URL in Twilio:
   https://abc123.ngrok.io/webhooks/whatsapp
   ```

### 2. Test Incoming WhatsApp Message

**Send a WhatsApp message to your Twilio number:**

```
Hello, I need help with my account!
```

**Expected Behavior:**

1. Twilio sends webhook to `/webhooks/whatsapp`
2. Backend validates signature
3. Message is normalized and published to Kafka
4. Message stored in `message_queue` table
5. Worker processes the message
6. Ticket is created
7. AI generates response
8. Response sent back via WhatsApp

**Verify in Database:**

```sql
-- Check message queue
SELECT request_id, channel, status, customer_email, metadata->>'customer_phone' as phone
FROM message_queue 
WHERE channel = 'whatsapp' 
ORDER BY created_at DESC 
LIMIT 5;

-- Check tickets
SELECT ticket_number, status, channel, subject
FROM tickets 
WHERE channel = 'whatsapp' 
ORDER BY created_at DESC 
LIMIT 5;

-- Check conversations
SELECT c.id, c.channel, c.external_thread_id, m.content, m.direction
FROM conversations c
JOIN messages m ON c.id = m.conversation_id
WHERE c.channel = 'whatsapp'
ORDER BY c.created_at DESC
LIMIT 10;
```

### 3. Test Webhook Signature Validation

```bash
# Test with valid signature (Twilio does this automatically)
# Send WhatsApp message via Twilio sandbox

# Test signature validation endpoint
curl -X POST http://localhost:8000/webhooks/whatsapp \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "X-Twilio-Signature: test_signature" \
  -d "From=whatsapp:+1234567890" \
  -d "Body=Test message" \
  -d "MessageSid=SM1234567890" \
  -d "ConversationSid=CH1234567890"
```

**Expected Response:**
```json
{
  "status": "received",
  "message_sid": "SM1234567890",
  "conversation_sid": "CH1234567890"
}
```

### 4. Test Long Message Splitting

Send a message longer than 1600 characters:

```bash
# The handler will automatically split messages > 1600 chars
# Test with a very long message
```

**Expected:** Message is split into multiple chunks with "..." continuation indicators.

---

## Gmail Integration Testing

### 1. Google Cloud Setup

#### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project or select existing
3. Enable Gmail API

#### Step 2: Create OAuth2 Credentials

1. Go to APIs & Services → Credentials
2. Create Credentials → OAuth client ID
3. Application type: Web application
4. Authorized redirect URIs: `http://localhost:8000/callback`
5. Note Client ID and Client Secret

#### Step 3: Get Refresh Token

```bash
# Construct OAuth URL:
https://accounts.google.com/o/oauth2/auth?
  client_id=YOUR_CLIENT_ID&
  redirect_uri=http://localhost:8000/callback&
  response_type=code&
  access_type=offline&
  scope=https://www.googleapis.com/auth/gmail.modify
```

### 2. Test Gmail Polling (Manual)

```python
# test_gmail_polling.py
import asyncio
from src.channels.gmail_handler import GmailHandler, GmailPollingService

async def test_polling():
    handler = GmailHandler()
    polling = GmailPollingService(handler)
    
    messages = await polling.fetch_new_messages(max_results=5)
    print(f"Fetched {len(messages)} messages")
    
    for msg in messages:
        print(f"  - From: {msg.customer_email}")
        print(f"  - Subject: {msg.metadata.get('subject')}")
        print(f"  - Content: {msg.content[:100]}...")

asyncio.run(test_polling())
```

### 3. Test Gmail Webhook (Pub/Sub)

**Setup Pub/Sub Push:**

```bash
# Create topic
gcloud pubsub topics create gmail-notifications

# Create subscription with push endpoint
gcloud pubsub subscriptions create gmail-sub \
  --topic=gmail-notifications \
  --push-endpoint=https://your-domain.com/webhooks/gmail
```

**Test Notification:**

```bash
# Publish test message
gcloud pubsub topics publish gmail-notifications \
  --message="test_notification"
```

### 4. Verify Email Processing

```sql
-- Check Gmail messages in queue
SELECT request_id, channel, status, customer_email, subject
FROM message_queue 
WHERE channel = 'gmail' 
ORDER BY created_at DESC 
LIMIT 5;

-- Check email threading
SELECT 
    c.external_thread_id as gmail_thread_id,
    COUNT(m.id) as message_count,
    array_agg(m.direction) as directions
FROM conversations c
JOIN messages m ON c.id = m.conversation_id
WHERE c.channel = 'gmail'
GROUP BY c.external_thread_id
ORDER BY c.created_at DESC
LIMIT 5;
```

---

## API Testing

### 1. Submit Message via API (Multi-Channel)

```bash
# Web Form
curl -X POST http://localhost:8000/api/v1/messages/submit \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-12345" \
  -d '{
    "customer_email": "test@example.com",
    "subject": "Test from web form",
    "message": "This is a test message",
    "channel": "web_form"
  }'

# WhatsApp (simulated)
curl -X POST http://localhost:8000/api/v1/messages/submit \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-12345" \
  -d '{
    "customer_phone": "+1234567890",
    "subject": "Test from WhatsApp",
    "message": "This is a WhatsApp test",
    "channel": "whatsapp"
  }'

# Gmail (simulated)
curl -X POST http://localhost:8000/api/v1/messages/submit \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-12345" \
  -d '{
    "customer_email": "test@gmail.com",
    "subject": "Test from Gmail",
    "message": "This is a Gmail test",
    "channel": "gmail"
  }'
```

### 2. Check Message Status

```bash
# Get status by request_id
curl http://localhost:8000/api/v1/messages/status/{request_id}
```

**Expected Response:**
```json
{
  "request_id": "uuid-here",
  "status": "completed",
  "ticket_number": "CS-2026-00001",
  "ticket_status": "resolved",
  "subject": "Test message",
  "channel": "whatsapp",
  "customer_email": null,
  "customer_phone": "+1234567890",
  "response": "Thank you for contacting us...",
  "sentiment": "neutral",
  "messages": [...]
}
```

### 3. Dashboard Metrics

```bash
# Get full dashboard
curl http://localhost:8000/api/v1/dashboard

# Get channel breakdown
curl http://localhost:8000/api/v1/dashboard | jq '.channels'

# Get real-time metrics
curl http://localhost:8000/api/v1/realtime
```

**Expected Channel Breakdown:**
```json
{
  "total_channels": 3,
  "breakdown": [
    {
      "channel": "web_form",
      "name": "Web Form",
      "count": 10,
      "percentage": 50.0,
      "unique_emails": 8,
      "unique_phones": 0
    },
    {
      "channel": "whatsapp",
      "name": "Whatsapp",
      "count": 7,
      "percentage": 35.0,
      "unique_emails": 0,
      "unique_phones": 5
    },
    {
      "channel": "gmail",
      "name": "Gmail",
      "count": 3,
      "percentage": 15.0,
      "unique_emails": 3,
      "unique_phones": 0
    }
  ]
}
```

---

## Webhook Testing

### 1. Local Webhook Testing with ngrok

```bash
# Start ngrok
ngrok http 8000

# Copy the HTTPS URL
# Update Twilio webhook URL:
curl -X POST https://api.twilio.com/2010-04-01/Accounts/ACxxx/Messaging/Services/MGxxx.json \
  -u ACxxx:your_auth_token \
  -d "WebhookUrl=https://abc123.ngrok.io/webhooks/whatsapp"
```

### 2. Webhook Signature Test (WhatsApp)

```python
# test_signature.py
import base64
import hmac
import hashlib

def generate_twilio_signature(auth_token, url, params):
    """Generate expected Twilio signature for testing"""
    sorted_params = sorted(params.items())
    signature_string = url
    for key, value in sorted_params:
        signature_string += key + value
    
    signature = base64.b64encode(
        hmac.new(
            auth_token.encode('utf-8'),
            signature_string.encode('utf-8'),
            hashlib.sha1
        ).digest()
    ).decode('utf-8')
    
    return signature

# Test
auth_token = "your_auth_token"
url = "http://localhost:8000/webhooks/whatsapp"
params = {
    "From": "whatsapp:+1234567890",
    "Body": "Test message",
    "MessageSid": "SM1234567890"
}

signature = generate_twilio_signature(auth_token, url, params)
print(f"Signature: {signature}")
```

---

## Multi-Channel Testing

### 1. Cross-Channel Conversation Test

**Scenario:** Customer starts on web form, continues on WhatsApp

```bash
# Step 1: Submit web form
curl -X POST http://localhost:8000/api/v1/messages/submit \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-12345" \
  -d '{
    "customer_email": "john@example.com",
    "subject": "Login issue",
    "message": "I cannot login to my account",
    "channel": "web_form"
  }'

# Step 2: Send WhatsApp from same customer (phone linked to email)
# Send WhatsApp message to Twilio number

# Step 3: Verify conversation continuity
SELECT 
    c.id as conversation_id,
    c.channel,
    c.is_cross_channel,
    array_agg(DISTINCT c2.channel) as all_channels
FROM conversations c
LEFT JOIN conversations c2 ON c.customer_id = c2.customer_id
WHERE c.customer_email = 'john@example.com'
GROUP BY c.id, c.channel, c.is_cross_channel;
```

### 2. Channel-Specific Response Formatting

**WhatsApp:** Short, casual responses (max 1600 chars, auto-split)
**Gmail:** Formal, detailed responses with proper threading
**Web Form:** Standard formatted responses

```sql
-- Check response lengths by channel
SELECT 
    channel,
    AVG(LENGTH(content)) as avg_response_length,
    COUNT(*) as count
FROM messages
WHERE direction = 'outbound'
GROUP BY channel
ORDER BY channel;
```

---

## Troubleshooting

### WhatsApp Issues

#### "Invalid Signature" Error

**Problem:** Twilio signature validation failing

**Solution:**
1. Verify `APP_TWILIO_AUTH_TOKEN` is correct
2. Check webhook URL matches exactly (including https/http)
3. Ensure ngrok URL is updated in Twilio console

#### Messages Not Received

**Problem:** WhatsApp messages not appearing in database

**Solution:**
```sql
-- Check webhook logs
SELECT * FROM message_queue WHERE channel = 'whatsapp' ORDER BY created_at DESC LIMIT 10;

-- Check for errors
SELECT request_id, error_message FROM message_queue 
WHERE status = 'failed' AND channel = 'whatsapp';
```

### Gmail Issues

#### OAuth2 Authentication Failed

**Problem:** Cannot authenticate with Gmail API

**Solution:**
1. Verify Client ID and Secret in `.env`
2. Refresh token may have expired - re-authorize
3. Check Gmail API is enabled in Google Cloud Console

#### Emails Not Fetched

**Problem:** Polling not retrieving emails

**Solution:**
```python
# Test Gmail handler directly
from src.channels.gmail_handler import GmailHandler

handler = GmailHandler()
# Check if handler initializes correctly
print(handler.channel_type)  # Should be "gmail"
```

### General Issues

#### Kafka Connection Issues

**Problem:** Messages not being processed

**Solution:**
```bash
# Check Kafka status
curl http://localhost:8000/api/v1/kafka/status

# Check worker status
curl http://localhost:8000/api/v1/worker/stats

# Check queue
curl http://localhost:8000/api/v1/messages/queue/debug
```

#### Database Issues

**Problem:** Messages not stored

**Solution:**
```sql
-- Check database connection
SELECT version();

-- Check message_queue table
\d message_queue

-- Check for locks
SELECT * FROM pg_stat_activity WHERE state = 'idle in transaction';
```

---

## Test Results Template

### WhatsApp Test Checklist

- [ ] Twilio sandbox connected
- [ ] Webhook URL configured
- [ ] Incoming message received
- [ ] Signature validation passed
- [ ] Message stored in database
- [ ] Ticket created
- [ ] AI response generated
- [ ] Response sent via WhatsApp
- [ ] Long message splitting works
- [ ] Media attachments handled

### Gmail Test Checklist

- [ ] OAuth2 credentials configured
- [ ] Gmail API enabled
- [ ] Polling fetches messages
- [ ] Email parsing works (HTML + plain text)
- [ ] Attachments handled
- [ ] Threading works (In-Reply-To, References)
- [ ] Response sent via Gmail
- [ ] Pub/Sub notifications work

### Multi-Channel Test Checklist

- [ ] Web form submissions work
- [ ] WhatsApp messages work
- [ ] Gmail messages work
- [ ] Channel metrics accurate
- [ ] Cross-channel conversation continuity
- [ ] Customer identification across channels
- [ ] Channel-specific response formatting

---

## Contact & Support

For issues or questions:
- Check backend logs: `docker logs backend`
- Review API documentation: `http://localhost:8000/docs`
- Check metrics dashboard: `http://localhost:8000/api/v1/dashboard`

# WhatsApp & Gmail Integration - Complete Implementation

## Overview

This document describes the complete implementation of WhatsApp (Twilio) and Gmail integrations for the Customer Success Digital FTE system.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Customer Success Digital FTE                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │   WhatsApp   │    │    Gmail     │    │   Web Form   │               │
│  │   (Twilio)   │    │  (Google)    │    │  (Next.js)   │               │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘               │
│         │                   │                   │                        │
│         ▼                   ▼                   ▼                        │
│  ┌─────────────────────────────────────────────────────────┐             │
│  │              Webhook Endpoints                          │             │
│  │  /webhooks/whatsapp    /webhooks/gmail                  │             │
│  └─────────────────────────────────────────────────────────┘             │
│         │                   │                   │                        │
│         ▼                   ▼                   ▼                        │
│  ┌─────────────────────────────────────────────────────────┐             │
│  │           Channel Intake Service (Unified)              │             │
│  │  - WhatsAppHandler                                      │             │
│  │  - GmailHandler                                         │             │
│  │  - WebFormHandler                                       │             │
│  └─────────────────────────────────────────────────────────┘             │
│         │                                                                  │
│         ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────┐             │
│  │              Kafka (inbound_messages)                   │             │
│  │              ↓ Fallback: In-Memory Queue                │             │
│  └─────────────────────────────────────────────────────────┘             │
│         │                                                                  │
│         ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────┐             │
│  │              Message Worker                             │             │
│  │  - Ticket Creation                                      │             │
│  │  - AI Processing (OpenAI Agents SDK)                    │             │
│  │  - Response Generation                                  │             │
│  └─────────────────────────────────────────────────────────┘             │
│         │                                                                  │
│         ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────┐             │
│  │           Multi-Channel Response Sender                 │             │
│  │  - WhatsAppResponseSender (Twilio API)                  │             │
│  │  - GmailResponseSender (Gmail API)                      │             │
│  └─────────────────────────────────────────────────────────┘             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Features Implemented

### WhatsApp (Twilio)

| Feature | Status | Description |
|---------|--------|-------------|
| Webhook Endpoint | ✅ | POST /webhooks/whatsapp |
| Signature Validation | ✅ | X-Twilio-Signature HMAC-SHA1 |
| Message Normalization | ✅ | Unified format for Kafka |
| Long Message Splitting | ✅ | Auto-split >1600 chars |
| Media Attachments | ✅ | URL + content type handling |
| Response Sender | ✅ | Twilio API integration |
| Phone Number Cleaning | ✅ | Remove 'whatsapp:' prefix |
| Conversation Threading | ✅ | Using ConversationSid |

### Gmail

| Feature | Status | Description |
|---------|--------|-------------|
| Webhook Endpoint | ✅ | POST /webhooks/gmail (Pub/Sub) |
| OAuth2 Support | ✅ | Client ID, Secret, Refresh Token |
| Message Parsing | ✅ | Multipart, HTML, plain text |
| Attachment Handling | ✅ | Base64 decoding |
| Polling Service | ✅ | Gmail API polling |
| Pub/Sub Support | ✅ | Google Cloud Pub/Sub |
| Response Sender | ✅ | Threading (In-Reply-To, References) |
| Email Threading | ✅ | Gmail thread_id tracking |

### Unified Features

| Feature | Status | Description |
|---------|--------|-------------|
| Multi-Channel API | ✅ | POST /api/v1/messages/submit |
| Channel Detection | ✅ | web_form, whatsapp, gmail |
| Customer Identification | ✅ | Email + phone support |
| Cross-Channel Continuity | ✅ | Unified customer view |
| Metrics Dashboard | ✅ | Channel breakdown in /api/v1/dashboard |
| Kafka Integration | ✅ | All channels publish to same topic |

---

## File Structure

```
backend/
├── src/
│   ├── channels/
│   │   ├── base.py                 # ChannelType, NormalizedMessage
│   │   ├── whatsapp_handler.py     # WhatsApp handler + response sender
│   │   ├── gmail_handler.py        # Gmail handler + response sender
│   │   ├── web_form_handler.py     # Web form handler
│   │   └── intake_service.py       # Unified intake + customer ID + router
│   ├── api/
│   │   └── routes/
│   │       ├── webhooks.py         # WhatsApp + Gmail webhooks
│   │       └── messages.py         # Multi-channel submit API
│   └── kafka/
│       └── integration.py          # Kafka publishing (updated for phone)
├── .env                            # Environment variables
├── CHANNEL_INTEGRATION_TESTING.md  # Testing guide
└── WHATSAPP_GMAIL_INTEGRATION.md   # This file
```

---

## API Reference

### Submit Message (Multi-Channel)

```http
POST /api/v1/messages/submit
Content-Type: application/json
X-API-Key: dev-api-key-12345

{
  // For Web Form / Gmail
  "customer_email": "user@example.com",
  
  // For WhatsApp
  "customer_phone": "+1234567890",
  
  "subject": "Issue description",
  "message": "Detailed message content...",
  "channel": "web_form|whatsapp|gmail"
}
```

**Response:**
```json
{
  "request_id": "uuid-here",
  "trace_id": "uuid-here",
  "status": "received",
  "message": "Message received and queued for processing",
  "rate_limit": {
    "remaining": 99,
    "limit": 100
  }
}
```

### Check Status

```http
GET /api/v1/messages/status/{request_id}
```

**Response:**
```json
{
  "request_id": "uuid-here",
  "status": "completed",
  "ticket_number": "CS-2026-00001",
  "ticket_status": "resolved",
  "subject": "Issue description",
  "channel": "whatsapp",
  "customer_email": null,
  "customer_phone": "+1234567890",
  "response": "Thank you for contacting us...",
  "sentiment": "neutral",
  "messages": [...],
  "created_at": "2024-01-16T12:00:00Z"
}
```

### Webhooks

#### WhatsApp Webhook

```http
POST /webhooks/whatsapp
Content-Type: application/x-www-form-urlencoded
X-Twilio-Signature: <HMAC-SHA1 signature>

From=whatsapp:+1234567890
To=whatsapp:+14155238886
Body=Hello
MessageSid=SM1234567890
ConversationSid=CH1234567890
```

**Response:**
```json
{
  "status": "received",
  "message_sid": "SM1234567890",
  "conversation_sid": "CH1234567890",
  "kafka_published": true
}
```

#### Gmail Webhook

```http
POST /webhooks/gmail
X-Goog-Channel-ID: <channel-id>
X-Goog-Resource-ID: <resource-id>
X-Goog-Resource-State: <state>
X-Goog-Message-Number: <msg-num>

{
  "message": {
    "data": "<base64-encoded-data>"
  }
}
```

**Response:**
```json
{
  "status": "received",
  "messages_found": 1,
  "channel_id": "<channel-id>"
}
```

### Dashboard Metrics

```http
GET /api/v1/dashboard
```

**Channel Breakdown:**
```json
{
  "channels": {
    "total_channels": 3,
    "breakdown": [
      {
        "channel": "web_form",
        "name": "Web Form",
        "count": 50,
        "percentage": 62.5,
        "completed": 48,
        "failed": 2,
        "avg_time_ms": 1250.5,
        "unique_emails": 45,
        "unique_phones": 0
      },
      {
        "channel": "whatsapp",
        "name": "Whatsapp",
        "count": 20,
        "percentage": 25.0,
        "completed": 19,
        "failed": 1,
        "avg_time_ms": 980.3,
        "unique_emails": 0,
        "unique_phones": 15
      },
      {
        "channel": "gmail",
        "name": "Gmail",
        "count": 10,
        "percentage": 12.5,
        "completed": 10,
        "failed": 0,
        "avg_time_ms": 1450.2,
        "unique_emails": 8,
        "unique_phones": 0
      }
    ]
  }
}
```

---

## Environment Variables

```bash
# WhatsApp (Twilio)
APP_TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
APP_TWILIO_AUTH_TOKEN="your_auth_token"
APP_TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Gmail
APP_GMAIL_CLIENT_ID="your_client_id.apps.googleusercontent.com"
APP_GMAIL_CLIENT_SECRET="your_client_secret"
APP_GMAIL_REDIRECT_URI=http://localhost:8000/callback
APP_GMAIL_REFRESH_TOKEN="your_refresh_token"
APP_GMAIL_SENDER_EMAIL=support@yourdomain.com
APP_GMAIL_POLLING_ENABLED=false
APP_GMAIL_POLLING_INTERVAL_SECONDS=60
APP_GMAIL_PUBSUB_ENABLED=false
```

---

## Testing Quick Start

### 1. WhatsApp Testing

```bash
# Start backend
cd backend
uvicorn src.api.main:app --reload

# Start ngrok for webhook testing
ngrok http 8000

# In Twilio Console, set webhook URL:
# https://abc123.ngrok.io/webhooks/whatsapp

# Send WhatsApp message to Twilio sandbox number
# Check logs for message processing
```

### 2. Gmail Testing

```bash
# Test Gmail handler directly
python -c "
from src.channels.gmail_handler import GmailHandler
handler = GmailHandler()
print('Gmail handler initialized:', handler.channel_type)
"

# Check metrics dashboard
curl http://localhost:8000/api/v1/dashboard | jq '.channels'
```

### 3. API Testing

```bash
# Submit test message
curl -X POST http://localhost:8000/api/v1/messages/submit \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-12345" \
  -d '{
    "customer_phone": "+1234567890",
    "subject": "Test",
    "message": "Test message",
    "channel": "whatsapp"
  }'

# Check status
curl http://localhost:8000/api/v1/messages/status/<request_id>
```

---

## Production Deployment

### Twilio Setup

1. **Purchase WhatsApp-enabled number** in Twilio Console
2. **Configure webhook URL** (production URL, not ngrok)
3. **Set up environment variables** in production
4. **Enable signature validation** for security

### Gmail Setup

1. **Create Google Cloud Project**
2. **Enable Gmail API**
3. **Create OAuth2 credentials**
4. **Set up Pub/Sub topic** (optional, for push notifications)
5. **Configure webhook URL** for Pub/Sub

### Security Considerations

- ✅ Webhook signature validation (WhatsApp)
- ✅ OAuth2 token handling (Gmail)
- ✅ API key authentication for submit endpoint
- ✅ Rate limiting per API key tier
- ✅ Input validation and sanitization

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Invalid Twilio signature | Check auth token, verify webhook URL |
| Gmail OAuth failed | Refresh token expired, re-authorize |
| Messages not processed | Check worker status, Kafka connection |
| Channel metrics wrong | Verify channel field in message_queue |

### Debug Commands

```bash
# Check queue
curl http://localhost:8000/api/v1/messages/queue/debug

# Check worker
curl http://localhost:8000/api/v1/worker/stats

# Check Kafka
curl http://localhost:8000/api/v1/kafka/status

# Check database
psql -c "SELECT channel, COUNT(*) FROM message_queue GROUP BY channel;"
```

---

## Next Steps

### Phase 1 (Completed)
- ✅ WhatsApp webhook integration
- ✅ Gmail webhook integration
- ✅ Multi-channel API
- ✅ Unified intake service
- ✅ Metrics dashboard

### Phase 2 (Future)
- [ ] Full Gmail polling implementation
- [ ] WhatsApp media sending
- [ ] Cross-channel conversation merging
- [ ] Channel-specific AI response formatting
- [ ] Advanced customer identification

---

## Support

For issues or questions:
- Testing Guide: `CHANNEL_INTEGRATION_TESTING.md`
- API Docs: `http://localhost:8000/docs`
- Metrics: `http://localhost:8000/api/v1/dashboard`

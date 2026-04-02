"""
FastAPI to Kafka Integration - Asynchronous Message Processing

## Architecture

### Before (Synchronous):
```
Request → API → AI Agent → Database → Response
         ↑
         └─ Blocks until complete (slow!)
```

### After (Asynchronous with Kafka):
```
Request → API → Kafka → Return immediately
                ↓
            Worker → AI Agent → Database
```

## Endpoints

### POST /api/v1/messages/submit
Submit a message for asynchronous processing.

**Request:**
```json
{
    "customer_email": "customer@example.com",
    "subject": "Help with my account",
    "message": "I need assistance...",
    "channel": "web_form"
}
```

**Response (Immediate - 202 Accepted):**
```json
{
    "request_id": "uuid-1234",
    "trace_id": "uuid-5678",
    "status": "received",
    "message": "Message received and queued for processing",
    "estimated_response_time": "24 hours"
}
```

### GET /api/v1/messages/status/{request_id}
Check processing status.

**Response:**
```json
{
    "request_id": "uuid-1234",
    "trace_id": "uuid-5678",
    "status": "completed",
    "message": "Processing complete",
    "ticket_number": "CS-2024-00001",
    "ticket_status": "resolved",
    "subject": "Help with my account",
    "channel": "web_form",
    "created_at": "2024-01-01T12:00:00Z",
    "customer_email": "customer@example.com",
    "message_count": 2,
    "messages": [...]
}
```

## Flow

1. **API receives request**
   - Validate input
   - Generate request_id and trace_id

2. **Publish to Kafka**
   - Send to `inbound_messages` topic
   - Does NOT wait for processing

3. **Return acknowledgment**
   - Return 202 Accepted immediately
   - Include request_id for tracking

4. **Background Worker processes**
   - Consumes from Kafka
   - Runs AI agent
   - Saves to database

5. **User checks status**
   - GET /status/{request_id}
   - Fetches from database

## Key Features

✅ **Non-blocking** - API returns immediately
✅ **Scalable** - Workers can scale independently
✅ **Resilient** - Kafka persists messages
✅ **Traceable** - request_id and trace_id for tracking
✅ **Fallback** - In-memory queue if Kafka unavailable
"""

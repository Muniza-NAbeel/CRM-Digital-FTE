# Background Message Worker - Implementation Complete

## Overview

Autonomous background worker for processing inbound customer messages using AI.

---

## File Created

### `src/workers/message_worker.py`

Background worker that processes messages through an 8-stage pipeline:

1. **Normalize Message** - Standardize format across channels
2. **Identify Customer** - Lookup or create customer record
3. **Create Ticket** - Generate support ticket
4. **Run AI Agent** - Generate intelligent response
5. **Analyze Sentiment** - Detect customer emotion
6. **Check Escalation** - Evaluate escalation triggers
7. **Save Conversation** - Store in database
8. **Publish Response** - Send to outbound queue

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Kafka: inbound_messages                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Background Message Worker                   │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Stage 1  │→│ Stage 2  │→│ Stage 3  │→│ Stage 4  │   │
│  │Normalize │  │Customer  │  │ Ticket   │  │ AI Agent │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│       ↓                                              ↓      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Stage 8  │←│ Stage 7  │←│ Stage 6  │←│ Stage 5  │   │
│  │ Publish  │  │  Save    │  │Escalate  │  │Sentiment │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Database + Kafka: outbound_messages             │
└─────────────────────────────────────────────────────────────┘
```

---

## Pipeline Stages

### Stage 1: Normalize Message

```python
{
    "id": "uuid-1234",
    "channel": "web_form",  # or gmail, whatsapp
    "customer_email": "customer@example.com",
    "subject": "Help with account",
    "message": "I need assistance...",
    "timestamp": "2024-01-01T12:00:00Z",
    "metadata": {}
}
```

**Channel-specific normalization:**
- **Web Form**: Direct mapping
- **Gmail**: Extract email from headers, clean subject
- **WhatsApp**: Generate email from phone, clean formatting

---

### Stage 2: Identify Customer

```sql
-- Lookup existing customer
SELECT * FROM customers WHERE email = $1

-- If not found, create new
INSERT INTO customers (email, full_name, preferred_channel, ...)
VALUES ($1, $2, $3, ...)
RETURNING *
```

**Result:**
```python
{
    "id": "customer-uuid",
    "email": "customer@example.com",
    "customer_tier": "standard",
    ...
}
```

---

### Stage 3: Create Ticket

```sql
INSERT INTO tickets (
    customer_id, subject, description, channel,
    priority, status, sla_tier,
    first_response_due_at, resolution_due_at
)
VALUES ($1, $2, $3, $4, $5, $6, $7, ...)
RETURNING *
```

**Result:**
```python
{
    "id": "ticket-uuid",
    "ticket_number": "CS-2024-00001",
    "status": "new",
    "priority": "medium",
    ...
}
```

---

### Stage 4: Run AI Agent

```python
from src.agents.customer_success_agent import CustomerSuccessAgent

agent = CustomerSuccessAgent()
response = await agent.process_message(
    message=normalized["message"],
    context={
        "ticket_id": str(ticket["id"]),
        "ticket_number": ticket["ticket_number"],
        "customer_id": str(ticket["customer_id"]),
        "channel": normalized["channel"],
        "subject": normalized["subject"],
    }
)
```

**Result:**
```python
{
    "response": "Thank you for contacting us...",
    "confidence": 0.95,
    "model": "gpt-4",
    "tokens_used": 150,
    "prompt_tokens": 100,
    "completion_tokens": 50,
}
```

---

### Stage 5: Analyze Sentiment

```python
from src.services.sentiment_analyzer import SentimentAnalyzer

analyzer = SentimentAnalyzer()
sentiment = await analyzer.analyze(normalized["message"])
```

**Result:**
```python
{
    "label": "negative",  # or positive, neutral
    "score": -0.65,  # -1.0 to 1.0
    "confidence": 0.85,  # 0.0 to 1.0
    "model": "openai",  # or keyword
}
```

---

### Stage 6: Check Escalation

**Escalation Triggers:**
- Negative sentiment (score < -0.5)
- Escalation keywords (escalate, manager, complaint)
- Pricing/refund queries
- Legal threats

```python
if sentiment["score"] < -0.5:
    escalation_needed = True
    escalation_reason = "negative_sentiment"

# Check keywords
for keyword in ["escalate", "manager", "complaint", "refund"]:
    if keyword in message.lower():
        escalation_needed = True
        escalation_reason = "customer_request"
```

**Result:**
```python
{
    "escalated": True,
    "reason": "negative_sentiment",
}
```

---

### Stage 7: Save Conversation

```sql
-- Create conversation record
INSERT INTO conversations (
    ticket_id, customer_id, channel,
    message_count, overall_sentiment, sentiment_score
)
VALUES ($1, $2, $3, 1, $4, $5)
RETURNING *

-- Save inbound message
INSERT INTO messages (
    ticket_id, conversation_id, customer_id,
    content, direction, channel,
    sentiment, sentiment_score
)
VALUES ($1, $2, $3, $4, 'inbound', $5, $6, $7)

-- Save outbound response
INSERT INTO messages (
    ticket_id, conversation_id, customer_id,
    content, direction, channel,
    ai_model_used, ai_prompt_tokens, ai_completion_tokens
)
VALUES ($1, $2, $3, $4, 'outbound', $5, $6, $7, $8)
```

---

### Stage 8: Publish Response

```python
from src.kafka import publish_outbound_message

result = await publish_outbound_message(
    ticket_id=str(ticket["id"]),
    customer_email=customer["email"],
    response_message=agent_response["response"],
    channel=ticket["channel"],
    agent_id="ai_agent",
    metadata={
        "ticket_number": ticket["ticket_number"],
        "confidence": agent_response["confidence"],
        "tokens_used": agent_response["tokens_used"],
    },
)
```

**Result:**
```python
{
    "success": True,
    "message_id": "uuid-5678",
    "topic": "outbound_messages",
    "mode": "kafka",  # or fallback
}
```

---

## Integration with FastAPI

### Application Startup (`src/api/main.py`)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    from src.workers import start_message_worker
    await start_message_worker()
    logger.info("✓ Message worker started - processing inbound messages")
    
    yield
    
    # Shutdown
    from src.workers import stop_message_worker
    await stop_message_worker()
    logger.info("Message worker stopped")
```

---

## Usage

### Start Worker

```python
from src.workers import start_message_worker

await start_message_worker()
# Worker now consuming from Kafka inbound_messages topic
```

### Stop Worker

```python
from src.workers import stop_message_worker

await stop_message_worker()
# Gracefully stops processing
```

### Get Statistics

```python
from src.workers import get_worker_stats

stats = get_worker_stats()
# {
#     "running": True,
#     "processed_count": 150,
#     "error_count": 2,
#     "last_processed_at": "2024-01-01T12:30:00Z"
# }
```

---

## Logging

### Stage Completion

```
INFO | 📨 Processing message: uuid-1234
INFO | Stage 1/8: Normalizing message
INFO | Stage 2/8: Identifying customer
INFO | Creating new customer: customer@example.com
INFO | New customer created: customer-uuid
INFO | Stage 3/8: Creating ticket
INFO | Ticket created: CS-2024-00001
INFO | Stage 4/8: Running AI agent
INFO | AI agent response generated
INFO | Stage 5/8: Analyzing sentiment
INFO | Stage 6/8: Checking escalation triggers
INFO | Escalation triggered: Negative sentiment detected
INFO | Stage 7/8: Saving conversation to database
INFO | Stage 8/8: Publishing response
INFO | Response published to Kafka
INFO | ✅ Message processed successfully: uuid-1234
```

### Error Handling

```
ERROR | ❌ Error processing message uuid-1234: Database connection failed
ERROR |   File "message_worker.py", line 123, in process_message
ERROR |   ...
```

---

## Error Handling

### Graceful Degradation

| Stage | Fallback Behavior |
|-------|------------------|
| AI Agent | Use template response |
| Sentiment Analysis | Use keyword-based analysis |
| Database | Retry with backoff |
| Kafka Publish | Use in-memory queue |

### Retry Logic

```python
try:
    await process_stage()
except Exception as e:
    logger.error(f"Stage failed: {e}")
    # Continue to next stage or use fallback
```

---

## Performance

### Async Processing

```python
# All stages are async
async def process_message(self, message_data: Dict[str, Any]):
    normalized = await self.normalize_message(message_data)
    customer = await self.identify_customer(normalized)
    ticket = await self.create_ticket(customer, normalized)
    # ...
```

### Scalability

- **Horizontal**: Deploy multiple worker instances
- **Kafka Consumer Groups**: Automatic load balancing
- **Async I/O**: Non-blocking database and API calls

---

## Monitoring

### Worker Stats

```python
stats = get_worker_stats()
```

**Output:**
```json
{
    "running": true,
    "processed_count": 150,
    "error_count": 2,
    "last_processed_at": "2024-01-01T12:30:00Z"
}
```

### Kafka Health

```bash
curl http://localhost:8000/api/v1/kafka/status
```

**Output:**
```json
{
    "kafka": {
        "status": "healthy",
        "kafka_connected": true,
        "fallback_active": false,
        "fallback_queue_size": 0,
        "consumer_running": true
    }
}
```

---

## Testing

### Test Worker Initialization

```python
from src.workers import get_message_worker

worker = get_message_worker()
assert worker is not None
assert worker.running == False
```

### Test Message Processing

```python
from src.workers import MessageWorker

worker = MessageWorker()

message = {
    "id": "test-123",
    "customer_email": "test@example.com",
    "subject": "Test",
    "message": "Help me",
    "channel": "web_form",
}

await worker.process_message(message)
```

---

## Status

✅ **Implementation Complete**

- [x] Message worker created
- [x] 8-stage pipeline implemented
- [x] Async processing
- [x] Error handling
- [x] Logging at each stage
- [x] Database integration
- [x] Kafka integration
- [x] Sentiment analysis
- [x] Escalation detection
- [x] FastAPI integration

---

**Background message worker is ready and operational!** 🚀

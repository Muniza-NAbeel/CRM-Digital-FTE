# Kafka Integration - Implementation Complete

## Overview

Asynchronous message processing integration using Apache Kafka with automatic fallback to in-memory queue.

---

## Files Created

### 1. `src/kafka/kafka_client.py`
Core Kafka client implementation with:
- **Async Producer** - Publish messages to Kafka topics
- **Async Consumer** - Subscribe and process messages
- **In-Memory Queue Fallback** - Automatic fallback when Kafka unavailable
- **Environment Configuration** - Uses settings from `.env`
- **Comprehensive Logging** - All publish/consume events logged

### 2. `src/kafka/integration.py`
Integration layer with:
- High-level publish functions
- Message handlers for consumers
- Setup and shutdown functions
- Health check endpoint

### 3. `src/kafka/__init__.py`
Module exports for easy imports.

### 4. `src/api/routes/kafka_status.py`
Kafka monitoring endpoints:
- `GET /api/v1/kafka/status` - Kafka health status
- `GET /api/v1/kafka/queue/stats` - Queue statistics

---

## Kafka Topics

| Topic | Purpose | Messages |
|-------|---------|----------|
| `inbound_messages` | Customer incoming messages | Web form, Gmail, WhatsApp |
| `outbound_messages` | Outgoing responses | AI responses, Human agent replies |
| `agent_events` | AI agent events | Ticket created, Sentiment detected, Escalated |

---

## Configuration (.env)

```env
# Kafka Configuration
APP_KAFKA_BOOTSTRAP_SERVERS=localhost:9092
APP_KAFKA_TOPIC_INBOUND=inbound_messages
APP_KAFKA_TOPIC_OUTBOUND=outbound_messages
APP_KAFKA_TOPIC_EVENTS=agent_events
APP_KAFKA_CONSUMER_GROUP_ID=digital_fte_worker
```

---

## Usage Examples

### Publish Inbound Message

```python
from src.kafka import publish_inbound_message

result = await publish_inbound_message(
    customer_email="customer@example.com",
    subject="Help with my account",
    message="I need assistance with...",
    channel="web_form",
)

# Result:
# {
#     "success": True,
#     "message_id": "uuid-1234-5678",
#     "topic": "inbound_messages",
#     "mode": "kafka"  # or "fallback"
# }
```

### Publish Agent Event

```python
from src.kafka import publish_agent_event

result = await publish_agent_event(
    event_type="ticket_created",
    ticket_id="ticket-uuid",
    customer_id="customer-uuid",
    event_data={
        "ticket_number": "CS-2024-00001",
        "subject": "Help request",
        "priority": "medium",
    },
)
```

### Publish Outbound Message

```python
from src.kafka import publish_outbound_message

result = await publish_outbound_message(
    ticket_id="ticket-uuid",
    customer_email="customer@example.com",
    response_message="Thank you for contacting us...",
    channel="web_form",
    agent_id="ai_agent",
)
```

---

## Integration Points

### 1. FastAPI Application (`src/api/main.py`)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    from src.kafka import init_kafka, setup_kafka_integration
    await init_kafka()
    await setup_kafka_integration()
    
    yield
    
    # Shutdown
    from src.kafka import shutdown_kafka_integration
    await shutdown_kafka_integration()
```

### 2. Ticket Creation (`src/api/routes/tickets.py`)

```python
@router.post("/", response_model=TicketResponse)
async def create_ticket(ticket_data: TicketCreate, ...):
    # Create ticket in database
    ticket = await db.fetchrow(...)
    
    # Publish event to Kafka (asynchronous)
    await publish_agent_event(
        event_type="ticket_created",
        ticket_id=str(ticket["id"]),
        event_data={...},
    )
    
    return ticket
```

---

## Fallback Behavior

### Kafka Available
```
Message → Kafka Producer → Kafka Broker → Consumer → Process
```

### Kafka Unavailable (Fallback)
```
Message → In-Memory Queue → Consumer → Process
```

**Automatic Failover:**
- If Kafka connection fails → Switches to in-memory queue
- If Kafka recovers → Processes queued messages, switches back
- No message loss
- No application downtime

---

## Logging

All Kafka events are logged:

```
✓ Message published to Kafka: topic=inbound_messages, key=inbound:user:123
✓ Message queued (fallback): topic=inbound_messages, key=inbound:user:123
← Message consumed from Kafka: topic=inbound_messages, key=inbound:user:123
← Message consumed from fallback queue: topic=inbound_messages, key=inbound:user:123
```

---

## Health Check

### Endpoint: `GET /health/`

```json
{
    "status": "healthy",
    "services": {
        "database": {
            "status": "healthy",
            "latency_ms": 16
        },
        "kafka": {
            "status": "fallback",
            "kafka_connected": false,
            "fallback_active": true,
            "fallback_queue_size": 0,
            "consumer_running": true
        }
    }
}
```

### Endpoint: `GET /api/v1/kafka/status`

```json
{
    "kafka": {
        "status": "fallback",
        "kafka_connected": false,
        "fallback_active": true,
        "fallback_queue_size": 0,
        "consumer_running": true
    }
}
```

### Endpoint: `GET /api/v1/kafka/queue/stats`

```json
{
    "mode": "fallback",
    "fallback_queue_size": 0,
    "consumer_running": true,
    "topics": {
        "inbound": "inbound_messages",
        "outbound": "outbound_messages",
        "events": "agent_events"
    }
}
```

---

## Error Handling

### Kafka Connection Failure
```python
try:
    await init_kafka()  # Returns False if Kafka unavailable
except Exception as e:
    logger.warning(f"Kafka init failed: {e}")
    # System continues with in-memory queue
```

### Publish Failure
```python
try:
    await publish_inbound_message(...)
except Exception as e:
    # Automatically falls back to in-memory queue
    logger.warning(f"Kafka publish failed, using fallback: {e}")
```

---

## Testing

### Test Kafka Status
```bash
curl http://localhost:8000/api/v1/kafka/status
```

### Test Health
```bash
curl http://localhost:8000/health/
```

### Test Queue Stats
```bash
curl http://localhost:8000/api/v1/kafka/queue/stats
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐      ┌──────────────┐      ┌───────────┐ │
│  │   Tickets    │      │   Messages   │      │  Agents   │ │
│  │    Router    │      │    Router    │      │           │ │
│  └──────┬───────┘      └──────┬───────┘      └─────┬─────┘ │
│         │                     │                     │       │
│         └─────────────────────┼─────────────────────┘       │
│                               │                             │
│                    ┌──────────▼──────────┐                  │
│                    │  Kafka Integration  │                  │
│                    │   (Publish/Consume) │                  │
│                    └──────────┬──────────┘                  │
│                               │                             │
└───────────────────────────────┼─────────────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │     Kafka Client      │
                    ├───────────────────────┤
                    │  ┌─────────────────┐  │
                    │  │   AIOKafka      │  │
                    │  │    Producer     │  │
                    │  └────────┬────────┘  │
                    │           │           │
                    │  ┌────────▼────────┐  │
                    │  │   AIOKafka      │  │
                    │  │    Consumer     │  │
                    │  └────────┬────────┘  │
                    │           │           │
                    │  ┌────────▼────────┐  │
                    │  │  In-Memory      │  │
                    │  │     Queue       │  │
                    │  │   (Fallback)    │  │
                    │  └─────────────────┘  │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │   Kafka Broker        │
                    │   (localhost:9092)    │
                    │   or                  │
                    │   In-Memory Queue     │
                    └───────────────────────┘
```

---

## Status

✅ **Implementation Complete**

- [x] Kafka client with Producer/Consumer
- [x] In-memory queue fallback
- [x] Environment configuration
- [x] FastAPI integration
- [x] Message publishing (inbound, outbound, events)
- [x] Message consuming with handlers
- [x] Comprehensive logging
- [x] Health check endpoints
- [x] Error handling
- [x] Graceful shutdown

---

## Next Steps (Optional)

1. **Start Kafka Broker** (if needed):
   ```bash
   docker-compose up -d kafka
   ```

2. **Monitor Kafka Processing**:
   - Check `/api/v1/kafka/status` for connection status
   - Check `/api/v1/kafka/queue/stats` for queue size
   - View application logs for publish/consume events

3. **Scale Workers**:
   - Deploy multiple consumer instances
   - Kafka will load balance across consumer group

---

**Kafka integration is complete and operational!** 🚀

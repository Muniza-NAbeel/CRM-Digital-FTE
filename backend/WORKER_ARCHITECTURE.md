# Worker Architecture - Hackathon Setup

## ⚠️ IMPORTANT: Avoid Double Processing

This system has **two ways** to run the message worker:

### Option A: FastAPI Embedded Worker ✅ (RECOMMENDED FOR HACKATHON)

**Run command:**
```bash
uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**What happens:**
- FastAPI starts on port 8000
- Worker automatically starts in background (via `lifespan` in `main.py`)
- Worker polls `message_queue` table every 2 seconds
- Messages are processed automatically

**Architecture:**
```
┌─────────────────────────────────────┐
│         FastAPI Application         │
│  ┌─────────────────────────────┐   │
│  │  API Routes (port 8000)     │   │
│  │  - POST /messages/submit    │   │
│  │  - GET  /messages/status    │   │
│  └─────────────────────────────┘   │
│  ┌─────────────────────────────┐   │
│  │  Background Worker          │   │
│  │  - Polls message_queue      │   │
│  │  - Creates tickets          │   │
│  │  - AI processing            │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│      PostgreSQL Database            │
│  - message_queue                    │
│  - tickets                          │
│  - customers                        │
│  - conversations                    │
│  - messages                         │
└─────────────────────────────────────┘
```

**Benefits:**
- ✅ Single process (simpler debugging)
- ✅ No double processing risk
- ✅ Shared database connection
- ✅ Easy to test locally
- ✅ Perfect for hackathons/demos

---

### Option B: Separate Worker Process ⚠️ (ADVANCED)

**Run commands (in separate terminals):**
```bash
# Terminal 1: Start API (without worker - requires code change)
uv run uvicorn src.api.main:app --reload

# Terminal 2: Start worker separately
uv run python -m src.workers.worker_runner
```

**⚠️ WARNING:**
- The standalone worker (`worker_runner.py`) is **DISABLED by default**
- It has a 5-second delay with warnings before starting
- Only use this if you modified `main.py` to NOT start embedded worker

**When to use:**
- Running worker as separate container/pod in production
- Need horizontal scaling (multiple worker instances)
- Kafka-based processing (not database polling)

---

## 🚫 DOUBLE PROCESSING RISK

If you run **BOTH** workers simultaneously:

```
FastAPI Embedded Worker  ─┐
                          ├──► Same message processed TWICE!
Separate Worker Process ──┘
```

**Consequences:**
- ❌ Duplicate tickets created
- ❌ Duplicate AI responses sent
- ❌ Race conditions in database
- ❌ Wasted resources
- ❌ Confusing logs

**How to avoid:**
1. **Always use Option A** (FastAPI embedded) for hackathon
2. If using Option B, disable embedded worker in `main.py`
3. Check running processes: `taskkill /F /IM python.exe`

---

## Current Setup (Hackathon Mode)

**File: `src/api/main.py`**
```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    # ... startup code ...
    
    # Start background message worker
    from src.workers import start_worker, run_worker
    await start_worker()
    
    # Run worker in background task
    asyncio.create_task(run_worker())
    logger.info("✓ Message worker started - processing inbound messages")
```

**File: `src/workers/worker_runner.py`**
```python
# ⚠️ WARNING: This standalone worker is DISABLED by default.
# Has 5-second delay with warnings before starting
```

---

## Testing the Pipeline

### 1. Start the Application
```bash
uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

Look for these logs:
```
✓ Database initialized: PostgreSQL
✓ Kafka integration complete
✓ Message worker started - processing inbound messages
Application startup complete
```

### 2. Submit a Message
```bash
curl -X POST http://localhost:8000/api/v1/messages/submit \
  -H "Content-Type: application/json" \
  -d '{
    "customer_email": "test@example.com",
    "subject": "Help needed",
    "message": "I am frustrated with your service"
  }'
```

### 3. Check Status (wait 3-5 seconds)
```bash
curl http://localhost:8000/api/v1/messages/status/<request_id>
```

**Expected response:**
```json
{
  "status": "completed",
  "ticket_number": "CS-2026-12345",
  "ticket_status": "resolved",
  "response": "Thank you for contacting us...",
  "sentiment": "negative",
  "is_escalated": true
}
```

---

## Production Deployment (Future)

For production, you would separate the worker:

**docker-compose.yml:**
```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://...
    # No worker in API container
  
  worker:
    build: .
    command: python -m src.workers.worker_runner
    environment:
      - DATABASE_URL=postgresql://...
    replicas: 3  # Scale workers horizontally
```

**Changes needed:**
1. Remove worker startup from `main.py` lifespan
2. Add health check endpoint for worker
3. Use Redis/Kafka for distributed task queue
4. Add worker metrics/monitoring

---

## Quick Reference

| Scenario | Command | Worker Location |
|----------|---------|-----------------|
| **Hackathon/Demo** | `uvicorn src.api.main:app` | Inside FastAPI ✅ |
| **Local Testing** | `uvicorn src.api.main:app` | Inside FastAPI ✅ |
| **Production** | Separate containers | Separate service |
| **Debugging** | `worker_runner.py` only | Standalone ⚠️ |

---

## Files Modified

1. **`src/workers/worker_runner.py`**
   - Added safety warnings
   - Added 5-second delay before starting
   - Added documentation about double processing risk

2. **`src/api/main.py`**
   - Worker starts automatically in `lifespan`
   - No changes needed (already configured correctly)

---

## TL;DR

**For hackathon, just run:**
```bash
uv run uvicorn src.api.main:app --reload
```

**Don't run:**
```bash
uv run python -m src.workers.worker_runner  # ❌ Don't use this!
```

**One process = No problems! ✅**

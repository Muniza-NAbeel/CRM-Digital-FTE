# Ticket Number Fix - Complete Working Solution

## Problem
The system was failing with:
```
ERROR: null value in column "ticket_number" of relation "tickets" violates not-null constraint
```

The database trigger `generate_ticket_number()` was not installed or not working, causing NULL values during INSERT.

## Solution

### 1. Added `generate_ticket_number()` Function

**Location:** `src/workers/message_worker.py` and `src/workers/message_processor.py`

```python
async def _generate_ticket_number(self) -> str:
    """
    Generate a unique ticket number.
    
    Format: CS-<YEAR>-<RANDOM_5_DIGIT>
    Example: CS-2026-48392
    """
    year = datetime.now().year
    random_digits = random.randint(10000, 99999)
    ticket_number = f"CS-{year}-{random_digits}"
    
    # Ensure uniqueness by checking database
    existing = await self.db.fetchval(
        "SELECT 1 FROM tickets WHERE ticket_number = $1",
        ticket_number,
    )
    
    # If collision (extremely rare), generate new one
    if existing:
        return await self._generate_ticket_number()
    
    return ticket_number
```

### 2. Updated Ticket Creation

**Before:**
```python
ticket = await self.db.fetchrow("""
    INSERT INTO tickets (
        customer_id, subject, description, channel,
        priority, status, sla_tier,
        first_response_due_at, resolution_due_at
    )
    VALUES ($1, $2, $3, $4, $5, $6, $7, ...)
    RETURNING *
""", customer_id, subject, message_text, channel, "medium", "new", "standard")
```

**After:**
```python
# Generate unique ticket number
ticket_number = await self._generate_ticket_number()
logger.info(f"   Generating ticket number: {ticket_number}")

ticket = await self.db.fetchrow("""
    INSERT INTO tickets (
        customer_id, subject, description, channel,
        priority, status, sla_tier, ticket_number,
        first_response_due_at, resolution_due_at
    )
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, ...)
    RETURNING *
""", customer_id, subject, message_text, channel, "medium", "new", "standard", ticket_number)
```

### 3. Added Error Handling

```python
try:
    ticket_number = await self._generate_ticket_number()
    ticket = await self.db.fetchrow(...)
    logger.info(f"   ✓ Ticket created with ticket_number: {ticket_number}")
except Exception as e:
    logger.error(f"   ✗ Ticket creation failed: {e}", exc_info=True)
    raise Exception(f"Failed to create ticket: {e}")
```

### 4. Enhanced Logging

```
📨 Picked message: <request_id>
📝 Processing started: <request_id>
   Email: <email>
   Subject: <subject>
👤 Step 1/6: Identifying customer
   ✓ Customer identified: <id>
🎫 Step 2/6: Creating ticket
   Generating ticket number: CS-2026-48392
   ✓ Ticket created with ticket_number: CS-2026-48392
🤖 Step 3/6: Running AI agent
   ✓ AI response generated: 245 chars
📊 Step 4/6: Analyzing sentiment
   ✓ Sentiment analyzed: negative (score: -0.5)
⚠️ Step 5/6: Checking escalation
   ✓ Escalation check: ESCALATED
   ⚠️ Escalation reason: negative_sentiment
💾 Step 6/6: Saving results
   ✓ Results saved: ticket=CS-2026-48392, conversation=<id>
✅ Processing completed: <request_id>
```

## Files Modified

1. **src/workers/message_worker.py**
   - Added `_generate_ticket_number()` method
   - Updated `_create_ticket()` to use generated ticket_number
   - Added error handling for ticket creation
   - Enhanced logging

2. **src/workers/message_processor.py**
   - Added `_generate_ticket_number()` method
   - Updated `_create_ticket()` to use generated ticket_number
   - Enhanced logging

## Expected API Response

### Submit Message
```bash
curl -X POST http://localhost:8000/api/v1/messages/submit \
  -H "Content-Type: application/json" \
  -d '{
    "customer_email": "test@example.com",
    "subject": "Help needed",
    "message": "I am frustrated with your service"
  }'
```

**Response:**
```json
{
  "request_id": "uuid-1234-5678",
  "trace_id": "uuid-9012-3456",
  "status": "received",
  "message": "Message received and queued for processing",
  "estimated_response_time": "24 hours"
}
```

### Check Status (after processing)
```bash
curl http://localhost:8000/api/v1/messages/status/<request_id>
```

**Response:**
```json
{
  "request_id": "uuid-1234-5678",
  "trace_id": "uuid-9012-3456",
  "status": "completed",
  "message": "Processing complete",
  "ticket_number": "CS-2026-48392",
  "ticket_status": "resolved",
  "subject": "Help needed",
  "channel": "web_form",
  "customer_email": "test@example.com",
  "created_at": "2026-03-28T10:30:00Z",
  "response": "Thank you for contacting us about 'Help needed'. Your ticket number is CS-2026-48392...",
  "sentiment": "negative",
  "is_escalated": true,
  "messages": [...],
  "error": null
}
```

## Testing

1. **Start the application:**
   ```bash
   uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Submit a test message:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/messages/submit \
     -H "Content-Type: application/json" \
     -d '{
       "customer_email": "angry@example.com",
       "subject": "Very frustrated",
       "message": "I am very angry and disappointed with your terrible service"
     }'
   ```

3. **Check status after 2-5 seconds:**
   ```bash
   curl http://localhost:8000/api/v1/messages/status/<request_id_from_step_2>
   ```

4. **Verify logs show:**
   - "Generating ticket number: CS-2026-XXXXX"
   - "Ticket created with ticket_number: CS-2026-XXXXX"
   - "Processing completed: <request_id>"

## Production Safety

- ✅ Ticket number is NEVER NULL
- ✅ Uniqueness is verified against database
- ✅ Recursive retry on collision (extremely rare)
- ✅ Proper error handling → status = "failed"
- ✅ Comprehensive logging at each step
- ✅ No duplicate processing (FOR UPDATE SKIP LOCKED)
- ✅ Failure handling with error_message stored

## Ticket Number Format

```
CS-<YEAR>-<RANDOM_5_DIGIT>

Examples:
  CS-2026-12345
  CS-2026-98765
  CS-2026-48392
```

The format ensures:
- Unique per year (90,000 possible numbers per year)
- Human-readable
- Easy to reference in customer communications
- Sorted chronologically by year

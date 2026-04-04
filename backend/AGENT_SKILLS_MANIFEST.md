# Agent Skills Manifest - Customer Success FTE

## Overview

This document defines the core skills/capabilities of the Customer Success Digital FTE. Each skill is a reusable capability that the agent can invoke based on context and need.

---

## Skill 1: Knowledge Retrieval

**Purpose:** Search and retrieve relevant product documentation to answer customer questions.

### When to Use
- Customer asks product-related questions
- Customer needs how-to guidance
- Customer reports a bug or issue
- Customer asks about features

### Input Schema
```python
class KnowledgeSearchInput(BaseModel):
    query: str              # Customer's question/issue
    max_results: int = 5    # Max results to return
    category: str = None    # Optional category filter
```

### Output Schema
```python
class KnowledgeSearchResult(BaseModel):
    query: str                    # Original query
    results: List[Dict]           # Search results
    relevance_scores: List[float] # Relevance scores
    search_time_ms: int           # Search duration
```

### Implementation
```python
@function_tool
async def search_knowledge_base(input: KnowledgeSearchInput) -> str:
    """Search product documentation for relevant information."""
    # Uses pgvector for semantic search
    # Returns formatted results with relevance scores
```

### Performance Metrics
- **Accuracy:** >90% relevant results
- **Latency:** <500ms
- **Coverage:** 100% of knowledge base

---

## Skill 2: Sentiment Analysis

**Purpose:** Analyze customer sentiment to gauge conversation tone and detect frustration.

### When to Use
- Every incoming customer message
- Before closing a ticket
- Before escalating to human
- For metrics/analytics

### Input Schema
```python
class SentimentInput(BaseModel):
    message_text: str       # Customer message
    conversation_id: str    # Context
```

### Output Schema
```python
class SentimentResult(BaseModel):
    label: str              # 'positive', 'neutral', 'negative'
    score: float            # 0.0 to 1.0
    confidence: float       # 0.0 to 1.0
    trend: str              # 'improving', 'stable', 'declining'
```

### Implementation
```python
@function_tool
async def analyze_sentiment(input: SentimentInput) -> SentimentResult:
    """Analyze customer sentiment from message text."""
    # Uses OpenAI or lightweight ML model
    # Tracks trend across conversation
```

### Thresholds
| Score Range | Label | Action |
|-------------|-------|--------|
| 0.7 - 1.0 | Positive | Can close ticket |
| 0.4 - 0.7 | Neutral | Continue conversation |
| 0.2 - 0.4 | Negative | Show empathy |
| 0.0 - 0.2 | Very Negative | Auto-escalate |

---

## Skill 3: Escalation Decision

**Purpose:** Determine when a conversation should be escalated to human support.

### When to Use
- After generating response
- When sentiment is negative
- When customer requests human
- When unable to help

### Input Schema
```python
class EscalationInput(BaseModel):
    conversation_context: Dict  # Full context
    sentiment_score: float      # Current sentiment
    customer_request: str       # Customer's last message
    search_attempts: int        # How many searches attempted
```

### Output Schema
```python
class EscalationResult(BaseModel):
    should_escalate: bool       # Decision
    reason: str                 # Escalation reason
    urgency: str                # 'normal', 'high', 'critical'
    suggested_agent: str        # Type of human agent needed
```

### Escalation Triggers

**Auto-Escalate (Always):**
- Customer mentions: "lawyer", "legal", "sue", "attorney"
- Pricing or refund requests
- Sentiment score < 0.2
- Customer explicitly requests human

**Should Escalate (Recommended):**
- Cannot find info after 2 search attempts
- Sentiment score < 0.3 and declining
- Customer follows up 3+ times on same issue
- Complex technical issue requiring code review

### Implementation
```python
@function_tool
async def escalate_to_human(input: EscalationInput) -> str:
    """Escalate conversation to human support."""
    # Creates escalation record
    # Notifies human agents via Kafka
    # Preserves full context
```

---

## Skill 4: Channel Adaptation

**Purpose:** Format responses appropriately for the communication channel.

### When to Use
- Before sending any response
- When customer switches channels
- When formatting multi-part messages

### Input Schema
```python
class ChannelAdaptationInput(BaseModel):
    response_text: str        # Raw response
    target_channel: str       # 'email', 'whatsapp', 'web_form'
    customer_name: str        # For personalization
    ticket_number: str        # For reference
```

### Output Schema
```python
class ChannelAdaptationResult(BaseModel):
    formatted_text: str       # Channel-appropriate response
    character_count: int      # Length
    split_required: bool      # If message needs splitting
    chunks: List[str]         # If split, list of chunks
```

### Channel Guidelines

#### Email
- **Style:** Formal, detailed
- **Greeting:** "Dear Customer,"
- **Signature:** "TechCorp AI Support Team"
- **Max Length:** 500 words
- **Features:** Ticket reference, full context

#### WhatsApp
- **Style:** Conversational, concise
- **Greeting:** "Hi!" + emoji
- **Signature:** "Reply for more help or type 'human'"
- **Max Length:** 1600 chars (optimal <300)
- **Features:** Emoji-friendly, split long messages

#### Web Form
- **Style:** Semi-formal, helpful
- **Greeting:** Optional
- **Signature:** "Need more help? Reply to this message"
- **Max Length:** 300 words
- **Features:** Ticket ID, link to portal

### Implementation
```python
@function_tool
async def format_for_channel(input: ChannelAdaptationInput) -> str:
    """Format response appropriately for the channel."""
    # Applies channel-specific templates
    # Splits long messages for WhatsApp
```

---

## Skill 5: Customer Identification

**Purpose:** Identify and unify customer profiles across all channels.

### When to Use
- Every incoming message
- When customer contacts via new channel
- When looking up conversation history

### Input Schema
```python
class CustomerIdentificationInput(BaseModel):
    email: str = None           # From email/web form
    phone: str = None           # From WhatsApp
    name: str = None            # From web form
    channel: str                # Source channel
```

### Output Schema
```python
class CustomerIdentificationResult(BaseModel):
    customer_id: str            # Unified customer ID
    is_new_customer: bool       # True if first contact
    matched_identifiers: List   # How customer was identified
    conversation_count: int     # Past conversations
    total_tickets: int          # Lifetime tickets
```

### Identification Strategy

**Priority Order:**
1. Check existing customers by email
2. Check existing customers by phone
3. Check customer_identifiers table
4. Create new customer if not found
5. Store all identifiers for future matching

### Cross-Channel Matching

```
Customer: john@example.com
├─ Email Channel (john@example.com)
├─ WhatsApp Channel (+923128818931)
└─ Web Form (john@example.com)

All channels unified under single customer_id
```

### Implementation
```python
@function_tool
async def identify_customer(input: CustomerIdentificationInput) -> str:
    """Identify or create customer profile."""
    # Searches by email, phone, identifiers
    # Creates new customer if needed
    # Returns unified customer_id
```

---

## Skill 6: Ticket Creation & Management

**Purpose:** Create and track support tickets for all customer interactions.

### When to Use
- **ALWAYS** at conversation start
- When customer follows up
- When issue category changes
- When escalation occurs

### Input Schema
```python
class TicketCreationInput(BaseModel):
    customer_id: str            # Customer ID
    subject: str                # Issue summary
    description: str            # Full description
    channel: str                # Source channel
    category: str               # Issue category
    priority: str               # 'low', 'medium', 'high'
```

### Output Schema
```python
class TicketCreationResult(BaseModel):
    ticket_id: str              # New ticket ID
    ticket_number: str          # Human-readable (CS-2026-XXXXX)
    status: str                 # 'open', 'processing', 'resolved'
    created_at: datetime        # Creation timestamp
    sla_due_at: datetime        # SLA deadline
```

### Ticket Lifecycle
```
open → processing → (escalated) → resolved → closed
```

### Implementation
```python
@function_tool
async def create_ticket(input: TicketCreationInput) -> str:
    """Create support ticket for tracking."""
    # Generates unique ticket number
    # Sets SLA deadlines
    # Stores in PostgreSQL
```

---

## Skill 7: Conversation History Retrieval

**Purpose:** Retrieve customer's complete interaction history across all channels.

### When to Use
- Before responding to customer
- When customer follows up
- When understanding context
- For metrics/analytics

### Input Schema
```python
class HistoryRetrievalInput(BaseModel):
    customer_id: str            # Customer ID
    limit: int = 20             # Max messages to return
    include_all_channels: bool  # Cross-channel history
```

### Output Schema
```python
class HistoryRetrievalResult(BaseModel):
    conversations: List[Dict]   # Past conversations
    messages: List[Dict]        # Individual messages
    total_count: int            # Total messages found
    channels_used: List[str]    # Channels customer has used
```

### Implementation
```python
@function_tool
async def get_customer_history(input: HistoryRetrievalInput) -> str:
    """Get customer's complete interaction history."""
    # Queries conversations and messages tables
    # Includes cross-channel context
    # Formats for agent consumption
```

---

## Skill 8: Response Delivery

**Purpose:** Send responses to customers via the appropriate channel.

### When to Use
- **ALWAYS** before ending agent turn
- When sending proactive updates
- When escalating to human
- When closing ticket

### Input Schema
```python
class ResponseDeliveryInput(BaseModel):
    ticket_id: str              # Ticket reference
    message: str                # Response content
    channel: str                # Target channel
    is_final: bool              # Is this the final response?
```

### Output Schema
```python
class ResponseDeliveryResult(BaseModel):
    success: bool               # Delivery status
    channel_message_id: str     # External ID (Gmail/Twilio)
    delivery_status: str        # 'sent', 'delivered', 'failed'
    latency_ms: int             # Delivery time
```

### Implementation
```python
@function_tool
async def send_response(input: ResponseDeliveryInput) -> str:
    """Send response to customer via channel."""
    # Routes to Gmail/WhatsApp/Web handler
    # Tracks delivery status
    # Logs to database
```

---

## Skill Manifest Summary

| # | Skill | Category | Criticality | Usage Frequency |
|---|-------|----------|-------------|-----------------|
| 1 | Knowledge Retrieval | Core | High | Every message |
| 2 | Sentiment Analysis | Core | High | Every message |
| 3 | Escalation Decision | Core | Critical | 15-20% messages |
| 4 | Channel Adaptation | Core | High | Every response |
| 5 | Customer Identification | Core | Critical | Every message |
| 6 | Ticket Creation | Core | Critical | Every conversation |
| 7 | History Retrieval | Core | Medium | 80% messages |
| 8 | Response Delivery | Core | Critical | Every response |

---

## Performance Requirements

### Overall Agent Performance
| Metric | Target | Measurement |
|--------|--------|-------------|
| Response time (processing) | <3 seconds | P95 latency |
| Response time (delivery) | <30 seconds | End-to-end |
| Accuracy on test set | >85% | E2E tests |
| Escalation rate | <20% | Of total tickets |
| Cross-channel ID | >95% | Customer matching |
| Customer satisfaction | >4.0/5.0 | Post-resolution survey |

### Per-Skill Performance
| Skill | Latency Target | Accuracy Target |
|-------|----------------|-----------------|
| Knowledge Retrieval | <500ms | >90% relevant |
| Sentiment Analysis | <200ms | >85% accurate |
| Escalation Decision | <100ms | >95% correct |
| Channel Adaptation | <50ms | 100% formatted |
| Customer Identification | <300ms | >98% accurate |
| Ticket Creation | <200ms | 100% success |
| History Retrieval | <400ms | 100% complete |
| Response Delivery | <5 seconds | >99% delivered |

---

## Skill Invocation Order (Typical Flow)

```
1. identify_customer()       ← On every incoming message
2. create_ticket()           ← First message only
3. get_customer_history()    ← Check for context
4. analyze_sentiment()       ← Understand tone
5. search_knowledge_base()   ← If product question
6. escalate_to_human()       ← If escalation needed
7. format_for_channel()      ← Before sending
8. send_response()           ← Deliver response
```

---

## Testing Strategy

### Unit Tests (Per Skill)
- Input validation
- Output formatting
- Error handling
- Edge cases

### Integration Tests (Skill Combinations)
- Full conversation flow
- Cross-skill interactions
- Database operations
- Channel integrations

### E2E Tests (Complete Flow)
- Multi-channel scenarios
- Cross-channel continuity
- Performance under load
- Error recovery

---

**Document Status:** ✅ Complete  
**Last Updated:** April 2, 2026  
**Version:** 1.0

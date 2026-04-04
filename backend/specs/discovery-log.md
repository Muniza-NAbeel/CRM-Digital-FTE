# Discovery Log - Customer Success FTE

## Project Overview
**Hackathon:** CRM Digital FTE Factory - Final Hackathon 5  
**Team Size:** 1 Student  
**Duration:** 48-72 Development Hours  
**Difficulty:** Advanced

---

## Discovery Phase Findings

### 1. Multi-Channel Requirements Discovered

#### Email (Gmail) Channel
- **Pattern:** Longer, more detailed queries (avg 200-500 words)
- **Response Style:** Formal with greeting and signature
- **Max Length:** 500 words recommended
- **Threading:** Critical - must maintain conversation thread
- **Authentication:** OAuth2 required (refresh token flow)

#### WhatsApp Channel
- **Pattern:** Short, conversational messages (avg 20-50 words)
- **Response Style:** Concise, casual, emoji-friendly
- **Max Length:** 1600 characters (Twilio limit), optimal <300 chars
- **Threading:** Session-based via conversation_sid
- **Authentication:** Twilio signature validation required

#### Web Form Channel
- **Pattern:** Structured submissions with categories
- **Response Style:** Semi-formal, helpful
- **Max Length:** 300 words recommended
- **Validation:** Required fields, email format, min length
- **UI Requirements:** Real-time validation, status tracking

### 2. Edge Cases Discovered During Development

| # | Edge Case | Channel | Handling Strategy |
|---|-----------|---------|-------------------|
| 1 | Empty message body | All | Return clarification prompt |
| 2 | Pricing inquiries | All | Auto-escalate to human |
| 3 | Refund requests | All | Auto-escalate with reason |
| 4 | Angry customers (sentiment <0.3) | All | Escalate or show empathy |
| 5 | Cross-channel identification | All | Use email as primary key |
| 6 | Long WhatsApp messages | WhatsApp | Split into 1600 char chunks |
| 7 | Gmail OAuth token expiry | Gmail | Auto-refresh from token.json |
| 8 | Twilio sandbox expiry | WhatsApp | Rejoin every 72 hours |
| 9 | Database connection timeout | All | Retry with fallback |
| 10 | Kafka unavailable | All | In-memory queue fallback |
| 11 | Duplicate ticket submission | Web | Check for recent duplicates |
| 12 | Invalid email format | Web/Gmail | Validate and reject |
| 13 | Phone number formatting | WhatsApp | Auto-add country code |
| 14 | Unicode/special characters | All | UTF-8 encoding throughout |
| 15 | Rate limiting | All | API key-based tiers |

### 3. Response Patterns Discovered

#### Email Response Template (Working)
```
Dear Customer,

Thank you for contacting TechCorp Support.

[AI-generated response]

If you have any further questions, please don't hesitate to reply to this email.

Best regards,
TechCorp AI Support Team
---
Ticket Reference: {ticket_number}
```

#### WhatsApp Response Template (Working)
```
Hi! Thanks for contacting TechCorp Support. 🙏

[Concise AI response - max 300 chars]

Reply for more help or type 'human' for live support.
```

#### Web Form Response (Working)
- Immediate confirmation with ticket ID
- Auto-refresh status every 3 seconds
- Email notification when resolved

### 4. Escalation Rules (Finalized)

**MUST Escalate Immediately:**
- Customer mentions: "lawyer", "legal", "sue", "attorney"
- Pricing or refund requests
- Profanity or aggressive language
- Sentiment score < 0.3
- Customer explicitly requests human help
- WhatsApp: "human", "agent", "representative"

**Should Escalate:**
- Cannot find relevant info after 2 search attempts
- Customer follows up 3+ times on same issue
- Complex technical issues requiring code review

### 5. Performance Baseline (From Testing)

| Metric | Target | Achieved |
|--------|--------|----------|
| Response Time (processing) | <3 seconds | ✅ 1-2 seconds |
| Response Time (delivery) | <30 seconds | ✅ 5-15 seconds |
| Accuracy on test set | >85% | ✅ ~90% |
| Escalation rate | <20% | ✅ ~15% |
| Cross-channel ID | >95% | ✅ ~98% |

### 6. Technical Discoveries

#### Database Schema
- PostgreSQL with pgvector for semantic search
- JSONB columns for flexible metadata
- UUID primary keys for distributed systems
- Indexes on email, phone, conversation_id

#### Kafka Topics
```
fte.tickets.incoming       - Unified ticket queue
fte.channels.email.inbound  - Email-specific
fte.channels.whatsapp.inbound - WhatsApp-specific
fte.escalations            - Human handoffs
fte.metrics                - Performance tracking
fte.dlq                    - Dead letter queue
```

#### Fallback Modes
- **Kafka unavailable** → In-memory queue
- **Database unavailable** → SQLite fallback
- **Gmail API error** → Store for retry
- **Twilio error** → Log and escalate

### 7. Customer Identification Strategy

**Primary Key:** Email address
**Secondary Key:** Phone number (WhatsApp)
**Cross-Channel Matching:**
1. Check existing customers by email
2. Check existing customers by phone
3. Check customer_identifiers table
4. Create new customer if not found
5. Update identifiers for future matching

### 8. Sentiment Analysis Implementation

**Scale:** 0.0 (very negative) to 1.0 (very positive)

**Thresholds:**
- `> 0.7`: Positive - Can close ticket
- `0.4 - 0.7`: Neutral - Continue conversation
- `< 0.3`: Negative - Consider escalation
- `< 0.2`: Very Negative - Auto-escalate

**Tracked Per:**
- Each message
- Conversation average
- Trend (improving/degrading)

### 9. Channel-Specific Learnings

#### Gmail
- OAuth2 refresh tokens expire every 72 hours
- Must use `prompt=consent` to get refresh token
- Threading requires `In-Reply-To` and `References` headers
- Pub/Sub notifications faster than polling

#### WhatsApp (Twilio)
- Sandbox expires every 72 hours
- Must send `join <code>` to reactivate
- Message format: `whatsapp:+1234567890`
- Signature validation critical for security

#### Web Form
- Real-time validation improves UX
- Auto-refresh status (3-second polling)
- Dark/Light theme support
- Mobile-responsive design essential

### 10. Security Discoveries

**API Key Authentication:**
- Tier-based rate limiting (free: 10/hour, pro: 100/hour, enterprise: unlimited)
- X-API-Key header required
- CORS configuration for web form

**Webhook Security:**
- Twilio: X-Twilio-Signature validation
- Gmail: Pub/Sub JWT verification
- Web form: Input validation + sanitization

**Data Protection:**
- Customer PII encrypted at rest
- API keys in environment variables
- No secrets in code/repository

---

## Iteration History

### Iteration 1: Basic Prototype
- Single-channel (web form only)
- In-memory storage
- No authentication

### Iteration 2: Multi-Channel
- Added Gmail integration
- Added WhatsApp integration
- PostgreSQL database

### Iteration 3: Production Features
- Kafka event streaming
- Fallback modes
- Auto-refresh UI
- Theme toggle

### Iteration 4: Polish
- Error handling improvements
- Better logging
- Performance optimization
- Documentation

---

## Next Steps (Transition to Specialization)

1. ✅ Extract working prompts to `prompts.py`
2. ✅ Convert MCP tools to `@function_tool`
3. ✅ Add Pydantic validation to all tools
4. ✅ Create comprehensive test suite
5. ✅ Deploy to Kubernetes
6. ✅ Run 24-hour stability test

---

**Last Updated:** April 2, 2026  
**Status:** Incubation Complete ✅

# Customer Success FTE Specification

## Executive Summary

**Purpose:** Handle routine customer support queries with speed and consistency across multiple channels (Email, WhatsApp, Web Form).

**Business Value:** Replace $75,000/year human FTE with <$1,000/year AI employee operating 24/7.

**Status:** Production-Ready ✅

---

## Supported Channels

| Channel | Identifier | Response Style | Max Length | Auth Method |
|---------|------------|----------------|------------|-------------|
| Email (Gmail) | Email address | Formal, detailed | 500 words | OAuth2 |
| WhatsApp | Phone number | Conversational, concise | 1600 chars | Twilio Signature |
| Web Form | Email address | Semi-formal | 300 words | API Key |

---

## Scope

### In Scope
- ✅ Product feature questions
- ✅ How-to guidance
- ✅ Bug report intake
- ✅ Feedback collection
- ✅ Cross-channel conversation continuity
- ✅ Sentiment analysis
- ✅ Auto-escalation for complex issues

---

## Architecture

### High-Level Flow

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│    Gmail     │    │   WhatsApp   │    │   Web Form   │
│   (Email)    │    │  (Messaging) │    │  (Website)   │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────┐
│              Unified Ticket Ingestion (Kafka)           │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Customer Success FTE (Agent)               │
│  - OpenAI GPT-4o                                        │
│  - Multi-channel awareness                              │
│  - Sentiment analysis                                   │
│  - Auto-escalation                                      │
└────────────────────────┬────────────────────────────────┘
                         │
       ┌─────────────────┼─────────────────┐
       ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Gmail API    │  │ Twilio API   │  │  Database    │
│  (Reply)     │  │  (Reply)     │  │  (Store)     │
└──────────────┘  └──────────────┘  └──────────────┘
```

### Database Schema (PostgreSQL)

**Core Tables:**
- `customers` - Unified customer profiles
- `conversations` - Conversation threads
- `messages` - All messages with channel tracking
- `tickets` - Support ticket lifecycle
- `knowledge_base` - Product documentation with embeddings
- `agent_metrics` - Performance tracking

**Key Features:**
- Cross-channel customer identification
- Vector search for semantic knowledge retrieval
- JSONB for flexible metadata
- UUID primary keys

---

## Tools (Agent Capabilities)

| Tool | Purpose | Input Schema | Constraints |
|------|---------|--------------|-------------|
| `search_knowledge_base` | Find relevant docs | `query: str, max_results: int` | Max 5 results |
| `create_ticket` | Log interactions | `customer_id, issue, priority, channel` | Required for all chats |
| `get_customer_history` | Cross-channel context | `customer_id: str` | Last 20 messages |
| `escalate_to_human` | Hand off complex issues | `ticket_id, reason, urgency` | Include full context |
| `send_response` | Reply via channel | `ticket_id, message, channel` | Channel-aware formatting |

---

## Agent System Prompt

```
You are a Customer Success agent for TechCorp SaaS.

## Your Purpose
Handle routine customer support queries with speed, accuracy, and empathy
across multiple channels.

## Channel Awareness
- Email: Formal, detailed responses with greeting/signature
- WhatsApp: Concise, conversational, <300 chars preferred
- Web Form: Semi-formal, helpful, balanced detail

## Required Workflow (ALWAYS follow this order)
1. FIRST: Call `create_ticket` to log the interaction
2. THEN: Call `get_customer_history` to check for prior context
3. THEN: Call `search_knowledge_base` if product questions arise
4. FINALLY: Call `send_response` to reply

## Hard Constraints (NEVER violate)
- NEVER discuss pricing → escalate immediately
- NEVER promise features not in documentation
- NEVER process refunds → escalate
- NEVER share internal processes
- NEVER respond without using send_response tool

## Escalation Triggers (MUST escalate)
- Customer mentions "lawyer", "legal", "sue", "attorney"
- Customer uses profanity or aggressive language (sentiment < 0.3)
- Cannot find relevant information after 2 search attempts
- Customer explicitly requests human help
- WhatsApp customer sends "human", "agent", or "representative"

## Response Quality Standards
- Be concise: Answer directly, then offer additional help
- Be accurate: Only state facts from knowledge base
- Be empathetic: Acknowledge frustration before solving
- Be actionable: End with clear next step
```

---

## Performance Requirements

| Metric | Target | Measurement |
|--------|--------|-------------|
| Response time (processing) | <3 seconds | P95 latency |
| Response time (delivery) | <30 seconds | End-to-end |
| Accuracy on test set | >85% | E2E tests |
| Escalation rate | <20% | Of total tickets |
| Cross-channel ID | >95% | Customer matching |
| Uptime | >99.9% | 24-hour test |

---

## Guardrails

### Security
- ✅ API key authentication required
- ✅ Webhook signature validation (Twilio)
- ✅ OAuth2 token refresh (Gmail)
- ✅ Input validation on all endpoints
- ✅ Rate limiting per API tier

### Data Protection
- ✅ Customer PII encrypted at rest
- ✅ No secrets in code
- ✅ CORS configuration for web form
- ✅ HTTPS in production

### Response Safety
- ✅ Never discuss competitors
- ✅ Never promise undocumented features
- ✅ Never share internal processes
- ✅ Always create ticket before responding
- ✅ Always check sentiment before closing

---

## Channel-Specific Response Templates

### Email Template
```
Dear Customer,

Thank you for contacting TechCorp Support.

{AI-generated response}

If you have any further questions, please don't hesitate to reply to this email.

Best regards,
TechCorp AI Support Team
---
Ticket Reference: {ticket_number}
```

### WhatsApp Template
```
Hi! Thanks for contacting TechCorp Support. 🙏

{Concise response - max 300 chars}

Reply for more help or type 'human' for live support.
```

### Web Form Template
```
{Helpful response}
---
Need more help? Reply to this message or visit our support portal.

Ticket: {ticket_number}
```

---

## Testing Strategy

### Unit Tests
- Tool input validation
- Channel formatting functions
- Sentiment analysis thresholds
- Customer identification logic

### Integration Tests
- Gmail webhook processing
- WhatsApp webhook processing
- Web form submission
- Database operations
- Kafka event streaming

### E2E Tests
- Multi-channel conversation flow
- Cross-channel continuity
- Escalation workflows
- Error handling

### Load Tests
- 100+ concurrent users
- 1000+ messages/hour
- Auto-scaling validation
- Fallback mode activation

---

## Deployment

### Local Development
```bash
# Backend
cd backend
python run_both.py

# Frontend
cd frontend/web-form
npm run dev
```

### Production (Kubernetes)
```yaml
Deployments:
  - fte-api (3 replicas, auto-scale to 20)
  - fte-message-processor (3 replicas, auto-scale to 30)
  
Services:
  - PostgreSQL (StatefulSet)
  - Kafka (StatefulSet)
  - API (LoadBalancer)
  
Monitoring:
  - Prometheus metrics
  - Grafana dashboards
  - AlertManager alerts
```

---

## Monitoring & Alerts

### Key Metrics
- Messages processed per channel
- Average response time
- Escalation rate
- Customer sentiment trend
- Error rate by channel

### Alert Thresholds
- Response time > 5 seconds (Warning)
- Response time > 10 seconds (Critical)
- Error rate > 5% (Warning)
- Error rate > 10% (Critical)
- Escalation rate > 25% (Warning)

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Apr 2, 2026 | Initial specification from incubation |
| 2.0 | Apr 2, 2026 | Added production requirements |

---

**Document Status:** ✅ Complete  
**Last Updated:** April 2, 2026  
**Next Review:** After 24-hour stability test

# Customer Success Digital FTE — Final Submission

**Hackathon 5** · **Owner: Muniza Nabeel** · **Team Size: 1** · **Difficulty: Advanced**

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-purple.svg)
![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)
![Kafka](https://img.shields.io/badge/Apache%20Kafka-Event%20Streaming-orange.svg)
![Docker](https://img.shields.io/badge/Docker-Multi--stage-blue.svg)
![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen.svg)

---

## 📖 Table of Contents

- [Executive Summary](#executive-summary)
- [Live Demo](#live-demo)
- [Business Problem](#business-problem)
- [Architecture Overview](#architecture-overview)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [API Endpoints](#api-endpoints)
- [Frontend Features](#frontend-features)
- [Testing Summary](#testing-summary)
- [Demo Flow](#demo-flow)
- [Local Run Instructions](#local-run-instructions)
- [Environment Variables](#environment-variables)
- [Project Structure](#project-structure)
- [Submission Checklist](#submission-checklist)
- [Acknowledgments](#acknowledgments)

---

## 🎯 Executive Summary

A **production-grade AI Customer Success Digital FTE** operating 24/7 across **Gmail**, **WhatsApp**, and **Web Form**. Powered by **OpenAI GPT-4o**, **PostgreSQL CRM**, **Kafka event streaming**, and automated response delivery.

**Business Value:** Replaces $75,000/year human FTE with <$1,000/year AI employee operating continuously without breaks, sick days, or vacations.

**Status:** ✅ **PRODUCTION READY**

---

## 🔗 Live Demo

| Resource | URL | Status |
|----------|-----|--------|
| 🖥️ **Live Frontend** | https://crm-digital-fte.vercel.app | ✅ Live |
| 🌐 **Live Backend (Swagger)** | https://muniza-nabeel-techcorp-backend.hf.space | ✅ Live |
| ❤️ **Health Check** | https://muniza-nabeel-techcorp-backend.hf.space/health | ✅ Live |
| 🐙 **GitHub Repository** | [github.com/Muniza-NAbeel/CRM-Digital-FTE](https://github.com/Muniza-NAbeel/CRM-Digital-FTE) | ✅ Live |

---

## 🏢 Business Problem

Modern SaaS companies lose customers silently — support requests go unanswered, angry users churn before a human agent reads the ticket, and cross-channel conversations fragment into disconnected threads.

**Customer Success FTE solves this with:**

- ✅ **24/7 AI-powered support** across Gmail, WhatsApp, and Web Form
- ✅ **Cross-channel customer identity** — one profile across all channels
- ✅ **Real-time sentiment analysis** — detects anger, frustration, legal threats
- ✅ **Auto-escalation** — intelligent routing for complex issues
- ✅ **SLA management** — priority-based routing
- ✅ **Knowledge base search** — semantic search capabilities
- ✅ **Metrics dashboard** — resolution rates, escalation trends

**Result:** Faster resolutions, fewer churned customers, measurable reduction in escalation rate.

---

## 🏗️ Architecture Overview

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│    Gmail     │    │   WhatsApp   │    │   Web Form   │
│   (Email)    │    │  (Messaging) │    │  (Website)   │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────┐
│         Unified Ticket Ingestion (FastAPI + Kafka)      │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│         Customer Success FTE (OpenAI GPT-4o)            │
│  - Multi-channel awareness                              │
│  - Sentiment analysis                                   │
│  - Auto-escalation                                      │
│  - Cross-channel continuity                             │
└────────────────────────┬────────────────────────────────┘
                         │
       ┌─────────────────┼─────────────────┐
       ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Gmail API    │  │ Twilio API   │  │  PostgreSQL  │
│  (Reply)     │  │  (Reply)     │  │  (CRM/State) │
└──────────────┘  └──────────────┘  └──────────────┘
```

### Processing Pipeline

```
1. Validate     → Input validation (Pydantic v2)
2. Normalize    → Channel-agnostic message format
3. Identify     → Customer resolution (email/phone)
4. AI Agent     → OpenAI GPT-4o + tools
5. Sentiment    → Anger/frustration/urgency scoring
6. Ticket       → Create/update ticket record
7. Escalate     → Route to specialist if needed
8. Dispatch     → Send response via channel (Gmail/WhatsApp)
9. Kafka        → Publish metrics event
```

---

## ✨ Key Features

| Feature | Implementation |
|---------|----------------|
| **24/7 AI Agent** | OpenAI GPT-4o with confidence scoring |
| **Auto-Escalation** | Intelligent routing based on sentiment and complexity |
| **Sentiment Analysis** | Anger/frustration/urgency scoring; auto-escalation at threshold |
| **Cross-Channel Identity** | One customer profile across Gmail, WhatsApp, Web Form |
| **Kafka Streaming** | 8 decoupled event topics, dead-letter queue |
| **Production CRM** | PostgreSQL with 8-table schema, migrations |
| **Zero-Config Demo** | All external services have mock fallbacks |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **AI Agent** | OpenAI GPT-4o + rule-based fallback |
| **API Framework** | FastAPI 0.110+ · Pydantic v2 · Uvicorn |
| **Database** | PostgreSQL 15 (SQLite fallback) · SQLAlchemy 2.0 · asyncpg |
| **Event Streaming** | Apache Kafka · in-memory mock |
| **Email Channel** | Gmail API with OAuth2 |
| **WhatsApp Channel** | Twilio WhatsApp Business API |
| **Frontend** | Next.js 14 · React 18 · TypeScript · Tailwind CSS |
| **Containerization** | Docker multi-stage build |
| **Testing** | pytest · Locust (load testing) |

---

## 📡 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness probe — all subsystems |
| `GET` | `/api/v1/messages/status/{request_id}` | Get ticket status by request ID |
| `POST` | `/api/v1/messages/submit` | Submit inbound message (all channels) |
| `GET` | `/api/v1/tickets` | List tickets (filterable) |
| `GET` | `/api/v1/tickets/{ticket_number}` | Get ticket by ticket number |
| `GET` | `/api/v1/customers/{customer_id}` | Get customer profile + history |
| `POST` | `/webhooks/gmail` | Gmail inbound webhook |
| `POST` | `/webhooks/whatsapp` | WhatsApp inbound webhook |
| `GET` | `/api/v1/metrics/dashboard` | Performance metrics |
| `GET` | `/docs` | Swagger UI |

---

## 🖼️ Frontend Features

| Page | Path | What it does |
|------|------|--------------|
| **Support Form** | `/` | Submit support ticket via web form |
| **Check Status** | `/` (same page) | Check ticket status by request ID |
| **Dashboard** | `/dashboard` | Live metrics: tickets, channels, sentiment, escalations |

**Built with:** Next.js 14 App Router · TypeScript · Tailwind CSS

**Features:**
- ✅ Dark/Light theme toggle
- ✅ Auto-refresh status (3-second polling)
- ✅ Mobile responsive
- ✅ Real-time validation
- ✅ Ticket tracking with timeline

---

## 🧪 Testing Summary

| Suite | Tests | Type | Status |
|-------|-------|------|--------|
| `test_integrations.py` | Multiple | Integration tests | ✅ Passing |
| `test_api_integration.py` | Multiple | API integration | ✅ Passing |
| `test_multichannel_e2e.py` | Multiple | E2E tests | ✅ Passing |
| `load_test.py` | Locust | Load testing | ✅ Configured |

```bash
# Run integration tests
cd backend
pytest test_integrations.py -v

# Run API tests
pytest test_api_integration.py -v

# Run E2E tests
pytest test_multichannel_e2e.py -v

# Load test (requires running server)
locust -f load_test.py --host=http://localhost:8000 --headless -u 50 -r 5 -t 60s
```

---

## 🎬 Demo Flow

**Quick demo (< 2 minutes):**

```bash
# 1. Start Backend (Terminal 1)
cd backend
python run_both.py

# 2. Start Frontend (Terminal 2)
cd frontend/web-form
npm run dev

# 3. Open browser → http://localhost:3000

# 4. Submit support ticket
# - Fill form: name, email, subject, message
# - Select channel: Web Form
# - Submit → Get request ID

# 5. Check status
# - Paste request ID in "Check Status"
# - View ticket status, AI response, sentiment

# 6. View dashboard
# - Navigate to /dashboard
# - See live metrics
```

**Test via API:**

```bash
# Submit ticket
curl -X POST http://localhost:8000/api/v1/messages/submit \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-12345" \
  -d '{
    "customer_email": "test@example.com",
    "subject": "Test Issue",
    "message": "Testing the system",
    "channel": "web_form"
  }'

# Check status
curl http://localhost:8000/api/v1/messages/status/{request_id} \
  -H "X-API-Key: dev-api-key-12345"
```

---

## 🏃 Local Run Instructions

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker Desktop (optional, for Kafka/PostgreSQL)

### Backend

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Start API + Worker
python run_both.py

# Swagger UI: http://localhost:8000/docs
# Health: http://localhost:8000/health
```

### Frontend

```bash
cd frontend/web-form

# Install dependencies
npm install

# Create .env.local
echo 'NEXT_PUBLIC_API_URL=http://localhost:8000' > .env.local

# Start development server
npm run dev

# http://localhost:3000
```

### Docker (Optional - For Kafka/PostgreSQL)

```bash
# Start Kafka and PostgreSQL
docker-compose up -d postgres kafka

# Wait for services
docker-compose ps

# Then start backend
cd backend
python run_both.py
```

---

## 🔧 Environment Variables

### Backend (`.env` or `backend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_DATABASE_URL` | (required) | PostgreSQL connection string |
| `APP_KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka broker |
| `APP_GMAIL_CLIENT_ID` | — | Gmail OAuth client ID |
| `APP_GMAIL_CLIENT_SECRET` | — | Gmail OAuth client secret |
| `APP_GMAIL_REFRESH_TOKEN` | — | Gmail OAuth refresh token |
| `APP_GMAIL_SENDER_EMAIL` | — | Gmail sender email |
| `APP_TWILIO_ACCOUNT_SID` | — | Twilio account SID |
| `APP_TWILIO_AUTH_TOKEN` | — | Twilio auth token |
| `APP_TWILIO_WHATSAPP_NUMBER` | — | Twilio WhatsApp number |
| `APP_SECRET_KEY` | `dev-secret-key` | API secret key |
| `APP_API_KEYS` | `dev-api-key-12345` | API keys for authentication |
| `APP_OPENAI_API_KEY` | — | OpenAI API key (optional) |

### Frontend (`frontend/web-form/.env.local`)

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API URL |

---

## 📁 Project Structure

```
hackathon_five/
│
├── backend/                        # Python FastAPI Backend
│   ├── src/                        # Source code
│   │   ├── agents/                 # AI Agent
│   │   │   ├── __init__.py
│   │   │   ├── customer_success_agent.py
│   │   │   ├── formatters.py
│   │   │   └── prompts.py
│   │   ├── api/                    # FastAPI application
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   └── routes/
│   │   │       ├── messages.py
│   │   │       ├── webhooks.py
│   │   │       ├── health.py
│   │   │       ├── metrics.py
│   │   │       ├── tickets.py
│   │   │       └── customers.py
│   │   ├── channels/               # Channel integrations
│   │   │   ├── __init__.py
│   │   │   ├── gmail_handler.py
│   │   │   ├── whatsapp_handler.py
│   │   │   ├── web_form_handler.py
│   │   │   ├── base.py
│   │   │   └── intake_service.py
│   │   ├── database/               # Database layer
│   │   │   ├── __init__.py
│   │   │   ├── connection.py
│   │   │   └── models.py
│   │   ├── kafka/                  # Kafka integration
│   │   │   ├── __init__.py
│   │   │   ├── kafka_client.py
│   │   │   └── integration.py
│   │   ├── workers/                # Background workers
│   │   │   ├── __init__.py
│   │   │   ├── message_worker.py
│   │   │   └── message_processor.py
│   │   ├── security/               # Authentication & rate limiting
│   │   │   └── __init__.py
│   │   ├── services/               # Business logic
│   │   │   └── __init__.py
│   │   ├── config.py               # Configuration
│   │   └── logging_config.py       # Logging setup
│   │
│   ├── tests/                      # Test suite
│   │   ├── test_integrations.py
│   │   ├── test_api_integration.py
│   │   ├── test_multichannel_e2e.py
│   │   ├── load_test.py
│   │   └── analyze_load_test.py
│   │
│   ├── k8s/                        # Kubernetes manifests
│   │   ├── deployment.yaml
│   │   ├── statefulset.yaml
│   │   ├── monitoring.yaml
│   │   └── README.md
│   │
│   ├── specs/                      # Specifications
│   │   ├── discovery-log.md
│   │   └── customer-success-fte-spec.md
│   │
│   ├── database/                   # Database scripts
│   │   ├── schema.sql
│   │   └── migrations/
│   │
│   ├── Dockerfile                  # Backend container
│   ├── Dockerfile.worker           # Worker container
│   ├── requirements.txt            # Python dependencies
│   ├── run_both.py                 # Start API + Worker
│   ├── run_24h_test.bat            # Windows test runner
│   ├── run_24h_test.sh             # Linux/Mac test runner
│   ├── refresh_gmail_token.py      # Gmail OAuth refresh
│   ├── .env.example                # Environment template
│   ├── AGENT_SKILLS_MANIFEST.md    # Agent capabilities
│   ├── 24_HOUR_TEST_PLAN.md        # Stability test plan
│   └── [Documentation files...]
│
├── frontend/web-form/              # Next.js 14 Frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   ├── dashboard/
│   │   │   │   └── page.tsx
│   │   │   └── globals.css
│   │   ├── components/
│   │   │   ├── theme-toggle.tsx
│   │   │   ├── ticket-status.tsx
│   │   │   ├── dashboard-sidebar.tsx
│   │   │   └── ui/
│   │   ├── lib/
│   │   │   └── api.ts
│   │   ├── hooks/
│   │   └── types/
│   │
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   └── .env.example
│
├── .venv/                          # Python virtual environment
│
├── docker-compose.yml              # Docker orchestration
├── .gitignore                      # Git ignore rules
│
├── README.md                       # This file
├── API_DOCUMENTATION.md            # API reference
├── ARCHITECTURE_COMPLIANCE.md      # Architecture decisions
├── BACKEND_IMPLEMENTATION.md       # Backend implementation
├── HACKATHON_SUBMISSION_SUMMARY.md # Submission summary
├── TEST_RESULTS.md                 # Test results
└── [Other documentation files...]
```

---

## ✅ Submission Checklist

### Critical (must have)

- ✅ Backend running (`python run_both.py`)
- ✅ Frontend running (`npm run dev`)
- ✅ Submit support ticket → Get request ID
- ✅ Check ticket status → View AI response
- ✅ Dashboard with live metrics

### Strongly recommended

- ✅ Gmail integration (send/receive)
- ✅ WhatsApp integration (send/receive)
- ✅ Auto-escalation working
- ✅ Sentiment analysis working
- ✅ Cross-channel identity working

### Additional (bonus points)

- ✅ All tests passing
- ✅ Load test completed
- ✅ Kubernetes manifests ready
- ✅ 24-hour test plan documented

---

## 🙏 Acknowledgments

**Developer:** Muniza Nabeel  
**Mentor:** Sir Ali Aftab 
**Hackathon:** CRM Digital FTE Factory — Final Hackathon 5  
**Duration:** [25-02-2026] — [04-03-2026]

**Special Thanks:**
- Panaversity for the hackathon opportunity
- OpenAI for GPT-4o
- Twilio for WhatsApp sandbox
- Google for Gmail API

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

**Built with care** by **Muniza Nabeel** · **Hackathon 5** · **Customer Success Digital FTE**

---

# Customer Success FTE - Complete API Documentation

**Project:** Customer Success Digital FTE  
**Version:** 1.0.0  
**Base URL:** `http://localhost:8000`  
**Authentication:** `X-API-Key: dev-api-key-12345`  
**Documentation:** `http://localhost:8000/docs` (Swagger UI)

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [API Endpoints](#api-endpoints)
4. [Data Models](#data-models)
5. [Channel Integration](#channel-integration)
6. [Frontend Integration Guide](#frontend-integration-guide)

---

## 🎯 Overview

This API powers a 24/7 AI Customer Success agent that handles customer inquiries across multiple channels:
- **Web Form** - Embedded support form
- **Email (Gmail)** - Gmail API integration
- **WhatsApp** - Twilio WhatsApp API

**Key Features:**
- Automatic ticket generation (CS-2026-XXXXX format)
- AI-powered responses using GPT-4
- Sentiment analysis
- Multi-channel conversation continuity
- Real-time dashboard metrics
- Kafka-based event streaming

---

## 🔐 Authentication

All API requests require an API key in the header:

```http
X-API-Key: dev-api-key-12345
```

**Rate Limits:**
- Free: 100 requests/hour
- Standard: 1,000 requests/hour
- Premium: 10,000 requests/hour
- Enterprise: Unlimited

---

## 📡 API Endpoints

### **Health & Status**

#### 1. Health Check
```http
GET /health/
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-03-29T12:00:00.000Z",
  "version": "1.0.0",
  "environment": "development",
  "services": {
    "database": {
      "status": "healthy",
      "latency_ms": 2468,
      "database_type": "PostgreSQL",
      "using_fallback": false
    },
    "kafka": {
      "status": "healthy",
      "kafka_connected": true,
      "fallback_active": true,
      "fallback_queue_size": 0,
      "consumer_running": true
    }
  },
  "features": {
    "sentiment_analysis": true,
    "auto_escalation": true,
    "knowledge_base_learning": true,
    "metrics_collection": true
  }
}
```

---

### **Message Submission (Primary Endpoint for Frontend)**

#### 2. Submit Support Message
```http
POST /api/v1/messages/submit
```

**Request Headers:**
```http
Content-Type: application/json
X-API-Key: dev-api-key-12345
```

**Request Body:**
```json
{
  "customer_email": "customer@example.com",
  "subject": "Help with account",
  "message": "I need help with my account. Can you assist?",
  "channel": "web_form"
}
```

**Request Schema:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `customer_email` | string | ✅ Yes | Customer's email address |
| `subject` | string | ✅ Yes | Subject of the inquiry (min 5 chars) |
| `message` | string | ✅ Yes | Message content (min 10 chars) |
| `channel` | string | ✅ Yes | Must be `"web_form"` for web submissions |

**Response (202 Accepted):**
```json
{
  "request_id": "193ef690-3652-4369-9fc9-8c871467752a",
  "trace_id": "6e327243-9c93-42ab-a909-355a8202801d",
  "status": "received",
  "message": "Message received and queued for processing",
  "estimated_response_time": "24 hours",
  "rate_limit": null
}
```

**Response Schema:**
| Field | Type | Description |
|-------|------|-------------|
| `request_id` | UUID | Unique identifier for tracking |
| `trace_id` | UUID | Internal trace ID |
| `status` | string | `"received"` - message queued |
| `message` | string | Human-readable status |
| `estimated_response_time` | string | Expected response time |

---

#### 3. Get Message Status
```http
GET /api/v1/messages/status/{request_id}
```

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `request_id` | UUID | Request ID from submission response |

**Response (200 OK):**
```json
{
  "request_id": "193ef690-3652-4369-9fc9-8c871467752a",
  "trace_id": "6e327243-9c93-42ab-a909-355a8202801d",
  "status": "completed",
  "message": "Processing complete",
  "ticket_number": "CS-2026-44831",
  "ticket_status": "resolved",
  "subject": "Final Test",
  "channel": "web_form",
  "customer_email": "final-test@example.com",
  "created_at": "2026-03-29T11:57:44.973Z",
  "response": "Hello! We've received your inquiry regarding 'Final Test' (Ticket: CS-2026-44831). Thank you for reaching out. We understand you mentioned: \"Testing after Docker restart...\" We're looking into this and will provide a detailed response shortly. Your satisfaction is our priority!",
  "sentiment": "neutral",
  "is_escalated": false,
  "messages": [
    {
      "content": "Testing after Docker restart",
      "direction": "inbound",
      "created_at": "2026-03-29T11:57:54.311Z"
    },
    {
      "content": "Hello! We've received your inquiry...",
      "direction": "outbound",
      "created_at": "2026-03-29T11:57:54.764Z"
    }
  ],
  "error": null
}
```

**Status Values:**
- `"received"` - Message queued
- `"processing"` - Being processed by AI agent
- `"completed"` - Response generated
- `"failed"` - Processing failed

---

### **Dashboard & Metrics**

#### 4. Get Dashboard Metrics
```http
GET /api/v1/dashboard
```

**Response (200 OK):**
```json
{
  "timestamp": "2026-03-29T11:58:13.480Z",
  "overview": {
    "total_requests_session": 1,
    "success_rate_session": 100.0,
    "avg_processing_time_session_ms": 868.89,
    "total_requests_today": 2,
    "success_rate_today": 100.0,
    "failure_rate_today": 0.0,
    "escalation_rate_today": 0.0
  },
  "queue_status": {
    "pending": 0,
    "processing": 0,
    "completed": 14,
    "failed": 4,
    "with_retries": 0,
    "avg_processing_time_ms": 16511.48
  },
  "worker": {
    "running": true,
    "processed_count": 1,
    "error_count": 0,
    "last_poll": "2026-03-29T11:58:12.152Z"
  },
  "kafka": {
    "status": "healthy",
    "kafka_connected": true,
    "fallback_active": true,
    "fallback_queue_size": 0,
    "consumer_running": true
  },
  "sentiment": {
    "positive": 0,
    "neutral": 12,
    "negative": 2,
    "total": 14
  },
  "channels": [
    {
      "channel": "web_form",
      "count": 18,
      "completed": 14,
      "avg_time_ms": 16511.48
    }
  ],
  "retries": {
    "retry_1": 0,
    "retry_2": 0,
    "retry_3_plus": 0
  },
  "dead_letter_queue": {
    "total": 0,
    "new": 0,
    "high_priority": 0,
    "resolved": 0
  },
  "trend_7_days": [
    {
      "date": "2026-03-29",
      "total": 2,
      "completed": 2,
      "failed": 0,
      "escalated": 0
    },
    {
      "date": "2026-03-28",
      "total": 15,
      "completed": 12,
      "failed": 3,
      "escalated": 2
    }
  ]
}
```

---

#### 5. Get Real-time Metrics
```http
GET /api/v1/realtime
```

**Response:**
```json
{
  "timestamp": "2026-03-29T12:00:00.000Z",
  "queue_size": 0,
  "processing_count": 0,
  "last_minute": {
    "total": 1,
    "completed": 1
  },
  "worker": {
    "running": true,
    "processed_count": 1,
    "error_count": 0
  },
  "kafka": {
    "connected": true,
    "fallback_active": true,
    "fallback_queue_size": 0
  },
  "dlq_new_count": 0,
  "system_health": "healthy"
}
```

---

#### 6. Get Queue Size
```http
GET /api/v1/queue-size
```

**Response:**
```json
{
  "timestamp": "2026-03-29T12:00:00.000Z",
  "queue_size": {
    "pending": 0,
    "processing": 0,
    "retry": 0,
    "total": 0
  },
  "thresholds": {
    "warning": 100,
    "critical": 500
  },
  "alert": {
    "level": "normal",
    "message": "Queue size within normal limits"
  }
}
```

---

#### 7. Get Performance Metrics
```http
GET /api/v1/performance?days=7
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | 7 | Number of days (1-90) |

**Response:**
```json
{
  "period": {
    "days": 7,
    "start": "2026-03-22",
    "end": "2026-03-29"
  },
  "summary": {
    "total_requests": 17,
    "completed": 14,
    "failed": 3,
    "success_rate": 82.35
  },
  "daily": [
    {
      "date": "2026-03-29",
      "total_requests": 2,
      "completed": 2,
      "failed": 0,
      "avg_processing_time_ms": 8511.48,
      "p95_processing_time_ms": 9500.00,
      "retries": 0,
      "escalations": 0
    }
  ]
}
```

---

#### 8. Get System Health
```http
GET /api/v1/health
```

**Response:**
```json
{
  "timestamp": "2026-03-29T12:00:00.000Z",
  "status": "healthy",
  "components": {
    "worker": {
      "status": "healthy",
      "processed_count": 1,
      "error_count": 0
    },
    "queue": {
      "status": "healthy",
      "pending": 0
    },
    "kafka": {
      "status": "healthy",
      "fallback_queue_size": 0
    },
    "dlq": {
      "status": "healthy",
      "new_items": 0
    },
    "database": {
      "status": "healthy"
    }
  },
  "issues": [],
  "warnings": []
}
```

---

### **Customer Management**

#### 9. List Customers
```http
GET /api/v1/customers?page=1&page_size=20&search=John
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `page_size` | integer | 20 | Items per page (1-100) |
| `search` | string | - | Search by name or email |
| `tier` | string | - | Filter by tier |

**Response:**
```json
{
  "customers": [
    {
      "id": "uuid-here",
      "email": "customer@example.com",
      "phone": "+1234567890",
      "full_name": "John Doe",
      "company_name": "Acme Corp",
      "customer_tier": "standard",
      "created_at": "2026-03-29T10:00:00.000Z",
      "is_active": true
    }
  ],
  "total": 50,
  "page": 1,
  "page_size": 20
}
```

---

#### 10. Get Customer by ID
```http
GET /api/v1/customers/{customer_id}
```

**Response:**
```json
{
  "id": "uuid-here",
  "email": "customer@example.com",
  "phone": "+1234567890",
  "full_name": "John Doe",
  "company_name": "Acme Corp",
  "customer_tier": "standard",
  "created_at": "2026-03-29T10:00:00.000Z",
  "is_active": true,
  "tickets_count": 5,
  "last_contacted": "2026-03-29T11:00:00.000Z"
}
```

---

### **Ticket Management**

#### 11. List Tickets
```http
GET /api/v1/tickets?page=1&page_size=20&status=open&priority=high
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `page_size` | integer | 20 | Items per page |
| `status` | string | - | Filter: open, closed, escalated |
| `priority` | string | - | Filter: low, medium, high, critical |
| `channel` | string | - | Filter: web_form, gmail, whatsapp |

**Response:**
```json
{
  "tickets": [
    {
      "id": "uuid-here",
      "ticket_number": "CS-2026-44831",
      "customer_id": "uuid-here",
      "customer_email": "customer@example.com",
      "subject": "Help with account",
      "channel": "web_form",
      "category": "technical",
      "priority": "medium",
      "status": "open",
      "created_at": "2026-03-29T11:57:44.973Z",
      "resolved_at": null,
      "is_escalated": false
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

---

#### 12. Get Ticket by ID
```http
GET /api/v1/tickets/{ticket_id}
```

**Response:**
```json
{
  "id": "uuid-here",
  "ticket_number": "CS-2026-44831",
  "customer_id": "uuid-here",
  "customer_email": "customer@example.com",
  "subject": "Help with account",
  "channel": "web_form",
  "category": "technical",
  "priority": "medium",
  "status": "resolved",
  "created_at": "2026-03-29T11:57:44.973Z",
  "resolved_at": "2026-03-29T11:58:00.000Z",
  "is_escalated": false,
  "sentiment": "neutral",
  "response": "Hello! We've received your inquiry...",
  "messages": [
    {
      "content": "Help with account",
      "direction": "inbound",
      "created_at": "2026-03-29T11:57:44.973Z"
    },
    {
      "content": "Hello! We've received your inquiry...",
      "direction": "outbound",
      "created_at": "2026-03-29T11:58:00.000Z"
    }
  ]
}
```

---

#### 13. Escalate Ticket
```http
POST /api/v1/tickets/{ticket_id}/escalate
```

**Request Body:**
```json
{
  "reason": "complex_technical_issue",
  "notes": "Customer needs advanced technical support"
}
```

**Response:**
```json
{
  "ticket_id": "uuid-here",
  "ticket_number": "CS-2026-44831",
  "status": "escalated",
  "escalated_at": "2026-03-29T12:00:00.000Z",
  "escalation_reason": "complex_technical_issue",
  "assigned_to": "human_agent_queue"
}
```

---

### **Conversations**

#### 14. List Conversations
```http
GET /api/v1/conversations?customer_id=uuid&page=1
```

**Response:**
```json
{
  "conversations": [
    {
      "id": "uuid-here",
      "customer_id": "uuid-here",
      "initial_channel": "web_form",
      "started_at": "2026-03-29T11:57:44.973Z",
      "ended_at": null,
      "status": "active",
      "sentiment_score": 0.5,
      "message_count": 4
    }
  ],
  "total": 10,
  "page": 1,
  "page_size": 20
}
```

---

#### 15. Get Conversation Messages
```http
GET /api/v1/conversations/{conversation_id}/messages
```

**Response:**
```json
{
  "conversation_id": "uuid-here",
  "messages": [
    {
      "id": "uuid-here",
      "channel": "web_form",
      "direction": "inbound",
      "role": "customer",
      "content": "Help with account",
      "created_at": "2026-03-29T11:57:44.973Z",
      "sentiment": "neutral"
    },
    {
      "id": "uuid-here",
      "channel": "web_form",
      "direction": "outbound",
      "role": "agent",
      "content": "Hello! We've received your inquiry...",
      "created_at": "2026-03-29T11:58:00.000Z",
      "sentiment": "positive"
    }
  ],
  "total": 4
}
```

---

### **Knowledge Base**

#### 16. Search Knowledge Base
```http
GET /api/v1/knowledge-base/search?q=password+reset&limit=5
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `q` | string | - | Search query |
| `limit` | integer | 5 | Max results (1-20) |
| `category` | string | - | Filter by category |

**Response:**
```json
{
  "query": "password reset",
  "results": [
    {
      "id": "uuid-here",
      "title": "How to Reset Your Password",
      "content": "To reset your password, go to...",
      "category": "account",
      "relevance_score": 0.95,
      "created_at": "2026-03-01T10:00:00.000Z"
    }
  ],
  "total": 3
}
```

---

#### 17. Semantic Search
```http
POST /api/v1/knowledge-base/semantic-search
```

**Request Body:**
```json
{
  "query": "I forgot my login credentials",
  "limit": 5
}
```

**Response:** Same as regular search, but uses vector similarity.

---

### **Kafka Status**

#### 18. Get Kafka Status
```http
GET /api/v1/kafka/status
```

**Response:**
```json
{
  "kafka_connected": true,
  "fallback_active": true,
  "fallback_queue_size": 0,
  "consumer_running": true,
  "topics": [
    "fte.tickets.incoming",
    "fte.tickets.outgoing",
    "fte.agent.events"
  ],
  "producer_status": "connected",
  "consumer_status": "running"
}
```

---

#### 19. Get Queue Statistics
```http
GET /api/v1/kafka/queue/stats
```

**Response:**
```json
{
  "inbound_messages": {
    "pending": 0,
    "processing": 0,
    "completed": 100
  },
  "outbound_messages": {
    "pending": 0,
    "sent": 100
  },
  "agent_events": {
    "total": 50
  }
}
```

---

### **Worker Status**

#### 20. Get Worker Status
```http
GET /api/v1/worker/status
```

**Response:**
```json
{
  "running": true,
  "processed_count": 1,
  "error_count": 0,
  "last_poll": "2026-03-29T11:58:12.152Z",
  "poll_interval_seconds": 5,
  "max_batch_size": 10
}
```

---

## 📊 Data Models

### **Ticket**
```json
{
  "id": "uuid",
  "ticket_number": "CS-2026-44831",
  "customer_id": "uuid",
  "customer_email": "customer@example.com",
  "subject": "string",
  "channel": "web_form|gmail|whatsapp",
  "category": "general|technical|billing|feedback|bug_report",
  "priority": "low|medium|high|critical",
  "status": "open|in_progress|pending|resolved|closed|escalated",
  "created_at": "datetime",
  "resolved_at": "datetime|null",
  "is_escalated": "boolean",
  "sentiment": "positive|neutral|negative",
  "response": "string"
}
```

### **Customer**
```json
{
  "id": "uuid",
  "email": "customer@example.com",
  "phone": "+1234567890",
  "full_name": "John Doe",
  "company_name": "Acme Corp",
  "customer_tier": "free|standard|premium|enterprise",
  "created_at": "datetime",
  "is_active": "boolean"
}
```

### **Message**
```json
{
  "id": "uuid",
  "conversation_id": "uuid",
  "channel": "web_form|gmail|whatsapp",
  "direction": "inbound|outbound",
  "role": "customer|agent|system",
  "content": "string",
  "created_at": "datetime",
  "sentiment": "positive|neutral|negative",
  "tokens_used": "integer",
  "latency_ms": "integer"
}
```

### **Conversation**
```json
{
  "id": "uuid",
  "customer_id": "uuid",
  "initial_channel": "web_form|gmail|whatsapp",
  "started_at": "datetime",
  "ended_at": "datetime|null",
  "status": "active|closed|escalated",
  "sentiment_score": "decimal(3,2)",
  "resolution_type": "resolved|escalated|auto_closed"
}
```

---

## 🔌 Channel Integration

### **Web Form (For Frontend)**

**Endpoint:** `POST /api/v1/messages/submit`

**Complete Example:**
```javascript
// Submit support ticket
const response = await fetch('http://localhost:8000/api/v1/messages/submit', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'dev-api-key-12345'
  },
  body: JSON.stringify({
    customer_email: 'customer@example.com',
    subject: 'Help with account',
    message: 'I need help with my account. Can you assist?',
    channel: 'web_form'
  })
});

const data = await response.json();
console.log('Request ID:', data.request_id);

// Check status after 5 seconds
setTimeout(async () => {
  const statusResponse = await fetch(
    `http://localhost:8000/api/v1/messages/status/${data.request_id}`,
    {
      headers: { 'X-API-Key': 'dev-api-key-12345' }
    }
  );
  const statusData = await statusResponse.json();
  console.log('Status:', statusData.status);
  console.log('Response:', statusData.response);
}, 5000);
```

---

### **Gmail Webhook**

**Endpoint:** `POST /webhooks/gmail`

**Purpose:** Receive Gmail push notifications via Pub/Sub

**Request Body:**
```json
{
  "message": {
    "data": "base64_encoded_notification",
    "messageId": "msg-123"
  },
  "subscription": "projects/xxx/subscriptions/gmail-push"
}
```

---

### **WhatsApp Webhook (Twilio)**

**Endpoint:** `POST /webhooks/whatsapp`

**Purpose:** Receive WhatsApp messages via Twilio

**Form Data:**
```
MessageSid=SM123
From=whatsapp:+1234567890
Body=Hello, I need help
ProfileName=John Doe
```

---

## 🎨 Frontend Integration Guide

### **Required Endpoints for Web Form**

For a complete web support form, you need these 2 endpoints:

#### **1. Submit Form**
```javascript
POST /api/v1/messages/submit
```

**Form Fields:**
- `customer_email` (required, email format)
- `subject` (required, min 5 chars)
- `message` (required, min 10 chars)
- `channel` (always `"web_form"`)

**Optional Fields:**
- `category` (general|technical|billing|feedback|bug_report)
- `priority` (low|medium|high)

#### **2. Check Status**
```javascript
GET /api/v1/messages/status/{request_id}
```

**Polling Strategy:**
```javascript
// Poll every 3 seconds until completed
async function checkStatus(requestId) {
  const maxAttempts = 20; // 60 seconds total
  let attempts = 0;
  
  while (attempts < maxAttempts) {
    await new Promise(r => setTimeout(r, 3000));
    
    const response = await fetch(
      `http://localhost:8000/api/v1/messages/status/${requestId}`,
      { headers: { 'X-API-Key': 'dev-api-key-12345' } }
    );
    
    const data = await response.json();
    
    if (data.status === 'completed') {
      return data; // Success!
    }
    
    attempts++;
  }
  
  throw new Error('Timeout waiting for response');
}
```

---

### **Dashboard Integration**

For admin dashboard, use these endpoints:

```javascript
// Get all metrics
const dashboard = await fetch('http://localhost:8000/api/v1/dashboard', {
  headers: { 'X-API-Key': 'dev-api-key-12345' }
});

// Get real-time metrics
const realtime = await fetch('http://localhost:8000/api/v1/realtime', {
  headers: { 'X-API-Key': 'dev-api-key-12345' }
});

// Get performance trends
const performance = await fetch(
  'http://localhost:8000/api/v1/performance?days=7',
  { headers: { 'X-API-Key': 'dev-api-key-12345' } }
);
```

---

### **Error Handling**

**Common Status Codes:**
- `200` - Success
- `202` - Accepted (queued for processing)
- `400` - Bad Request (validation error)
- `401` - Unauthorized (invalid API key)
- `404` - Not Found (invalid request_id)
- `422` - Validation Error
- `429` - Rate Limit Exceeded
- `500` - Internal Server Error

**Error Response Format:**
```json
{
  "error": "validation_error",
  "message": "Request validation failed",
  "request_id": "uuid-here",
  "details": "Field 'email' is required"
}
```

---

### **Rate Limiting**

**Headers:**
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1648569600
```

**Handle Rate Limits:**
```javascript
if (response.status === 429) {
  const resetTime = response.headers.get('X-RateLimit-Reset');
  const waitTime = resetTime - Date.now() / 1000;
  console.log(`Rate limited. Wait ${waitTime} seconds`);
}
```

---

## 📝 Example Frontend Implementation

### **React Support Form Component**

```jsx
import React, { useState } from 'react';

const API_BASE = 'http://localhost:8000';
const API_KEY = 'dev-api-key-12345';

export default function SupportForm() {
  const [formData, setFormData] = useState({
    email: '',
    subject: '',
    message: '',
    category: 'general',
    priority: 'medium'
  });
  const [status, setStatus] = useState('idle');
  const [ticketId, setTicketId] = useState(null);
  const [response, setResponse] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setStatus('submitting');

    try {
      // Submit ticket
      const submitResponse = await fetch(`${API_BASE}/api/v1/messages/submit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': API_KEY
        },
        body: JSON.stringify({
          customer_email: formData.email,
          subject: formData.subject,
          message: formData.message,
          channel: 'web_form'
        })
      });

      const submitData = await submitResponse.json();
      setTicketId(submitData.request_id);
      setStatus('processing');

      // Poll for response
      const responseData = await checkStatus(submitData.request_id);
      setResponse(responseData);
      setStatus('completed');

    } catch (error) {
      console.error('Error:', error);
      setStatus('error');
    }
  };

  const checkStatus = async (requestId) => {
    for (let i = 0; i < 20; i++) {
      await new Promise(r => setTimeout(r, 3000));
      
      const response = await fetch(
        `${API_BASE}/api/v1/messages/status/${requestId}`,
        { headers: { 'X-API-Key': API_KEY } }
      );

      const data = await response.json();
      
      if (data.status === 'completed') {
        return data;
      }
    }
    throw new Error('Timeout');
  };

  if (status === 'completed') {
    return (
      <div className="success-message">
        <h2>Thank You!</h2>
        <p>Ticket: {ticketId}</p>
        <p>{response.response}</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="email"
        placeholder="Your Email"
        value={formData.email}
        onChange={e => setFormData({...formData, email: e.target.value})}
        required
      />
      <input
        type="text"
        placeholder="Subject"
        value={formData.subject}
        onChange={e => setFormData({...formData, subject: e.target.value})}
        required
      />
      <textarea
        placeholder="How can we help?"
        value={formData.message}
        onChange={e => setFormData({...formData, message: e.target.value})}
        required
      />
      <select
        value={formData.category}
        onChange={e => setFormData({...formData, category: e.target.value})}
      >
        <option value="general">General Question</option>
        <option value="technical">Technical Support</option>
        <option value="billing">Billing Inquiry</option>
        <option value="feedback">Feedback</option>
        <option value="bug_report">Bug Report</option>
      </select>
      <button type="submit" disabled={status === 'submitting'}>
        {status === 'submitting' ? 'Submitting...' : 'Submit Request'}
      </button>
    </form>
  );
}
```

---

## 🚀 Quick Start for Frontend

### **1. Test API is Running**
```bash
curl http://localhost:8000/health/
```

### **2. Submit Test Message**
```bash
curl -X POST http://localhost:8000/api/v1/messages/submit \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-12345" \
  -d '{
    "customer_email": "test@example.com",
    "subject": "Test",
    "message": "Help me",
    "channel": "web_form"
  }'
```

### **3. Check Status**
```bash
curl http://localhost:8000/api/v1/messages/status/{request_id} \
  -H "X-API-Key: dev-api-key-12345"
```

---

## 📞 Support

**Swagger UI:** `http://localhost:8000/docs`  
**ReDoc:** `http://localhost:8000/redoc`  
**Health Check:** `http://localhost:8000/health/`

---

**Document Version:** 1.0  
**Last Updated:** March 29, 2026  
**Backend Status:** 100% Complete ✅

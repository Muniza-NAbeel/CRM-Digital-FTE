"""
Message API Schemas

Schemas for asynchronous message submission and status tracking.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Literal
from enum import Enum
from pydantic import BaseModel, Field


# ============================================================================
# Request Schemas
# ============================================================================

class MessageSubmit(BaseModel):
    """
    Submit a new inbound message.
    """
    customer_email: str = Field(
        ...,
        description="Customer's email address",
        examples=["customer@example.com"],
        pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
    )
    subject: str = Field(
        "",
        description="Message subject",
        examples=["Help with my account"],
    )
    message: str = Field(
        ...,
        description="Message content",
        examples=["I need assistance with..."],
        min_length=1,
    )
    channel: Literal["web_form", "gmail", "whatsapp"] = Field(
        "web_form",
        description="Source channel",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "customer_email": "customer@example.com",
                "subject": "Help with my account",
                "message": "I'm having trouble accessing my account. Can you help?",
                "channel": "web_form",
                "metadata": {
                    "ip_address": "192.168.1.1",
                    "user_agent": "Mozilla/5.0...",
                },
            }
        }


# ============================================================================
# Response Schemas
# ============================================================================

class MessageResponse(BaseModel):
    """
    Immediate acknowledgment response after message submission.
    """
    request_id: str = Field(
        ...,
        description="Unique request identifier for tracking",
    )
    trace_id: str = Field(
        ...,
        description="Trace identifier for distributed tracing",
    )
    status: Literal["received", "queued"] = Field(
        ...,
        description="Initial status",
    )
    message: str = Field(
        ...,
        description="Acknowledgment message",
    )
    estimated_response_time: str = Field(
        ...,
        description="Expected response time",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "uuid-1234-5678",
                "trace_id": "uuid-9012-3456",
                "status": "received",
                "message": "Message received and queued for processing",
                "estimated_response_time": "24 hours",
            }
        }


class MessageStatus(str, Enum):
    """
    Processing status enumeration.
    """
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    FAILED = "failed"


class MessageStatusResponse(BaseModel):
    """
    Detailed status response for a submitted message.
    """
    request_id: str = Field(
        ...,
        description="Original request identifier",
    )
    trace_id: str = Field(
        ...,
        description="Trace identifier",
    )
    status: MessageStatus = Field(
        ...,
        description="Current processing status",
    )
    message: str = Field(
        ...,
        description="Status message",
    )
    ticket_number: str = Field(
        ...,
        description="Assigned ticket number",
    )
    ticket_status: str = Field(
        ...,
        description="Ticket status (new, in_progress, resolved, etc.)",
    )
    subject: str = Field(
        ...,
        description="Message subject",
    )
    channel: str = Field(
        ...,
        description="Source channel",
    )
    created_at: datetime = Field(
        ...,
        description="When the message was received",
    )
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp",
    )
    customer_email: Optional[str] = Field(
        None,
        description="Customer email",
    )
    conversation_id: Optional[str] = Field(
        None,
        description="Conversation ID if created",
    )
    message_count: int = Field(
        ...,
        description="Number of messages in conversation",
    )
    messages: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Recent messages (limited to 5)",
    )
    escalation_status: str = Field(
        "none",
        description="Escalation status",
    )
    sentiment: Optional[str] = Field(
        None,
        description="Detected sentiment",
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "request_id": "uuid-1234-5678",
                "trace_id": "uuid-9012-3456",
                "status": "completed",
                "message": "Processing complete",
                "ticket_number": "CS-2024-00001",
                "ticket_status": "resolved",
                "subject": "Help with my account",
                "channel": "web_form",
                "created_at": "2024-01-01T12:00:00Z",
                "updated_at": "2024-01-01T12:30:00Z",
                "customer_email": "customer@example.com",
                "conversation_id": "conv-uuid",
                "message_count": 2,
                "messages": [],
                "escalation_status": "none",
                "sentiment": "neutral",
            }
        }


# ============================================================================
# Internal Schemas
# ============================================================================

class KafkaInboundMessage(BaseModel):
    """
    Internal schema for Kafka inbound messages.
    """
    request_id: str
    trace_id: str
    customer_email: str
    subject: str
    message: str
    channel: str
    metadata: Dict[str, Any]
    submitted_at: datetime


class ProcessingResult(BaseModel):
    """
    Result of message processing (stored in database).
    """
    request_id: str
    trace_id: str
    ticket_id: str
    ticket_number: str
    customer_id: str
    conversation_id: Optional[str]
    response_generated: bool
    sentiment: Optional[str]
    escalated: bool
    processed_at: datetime

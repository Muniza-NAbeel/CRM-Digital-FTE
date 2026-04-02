"""
Ticket Pydantic schemas.
"""

from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class TicketStatus(str, Enum):
    """
    Ticket status values.
    """
    new = "new"
    in_progress = "in_progress"
    pending_customer = "pending_customer"
    pending_internal = "pending_internal"
    escalated = "escalated"
    resolved = "resolved"
    closed = "closed"


class TicketPriority(str, Enum):
    """
    Ticket priority values.
    """
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ChannelType(str, Enum):
    """
    Support channel types.
    """
    web_form = "web_form"
    gmail = "gmail"
    whatsapp = "whatsapp"


class TicketBase(BaseModel):
    """
    Base ticket schema.
    """
    subject: str = Field(..., min_length=1, max_length=512)
    description: Optional[str] = None
    channel: ChannelType
    priority: Optional[TicketPriority] = TicketPriority.medium
    sla_tier: Optional[str] = "standard"
    metadata: Optional[dict] = Field(default_factory=dict)


class TicketCreate(TicketBase):
    """
    Schema for creating a ticket.
    """
    customer_id: UUID


class TicketUpdate(BaseModel):
    """
    Schema for updating a ticket.
    All fields are optional.
    """
    subject: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    assigned_to: Optional[str] = None
    sla_tier: Optional[str] = None
    escalation_status: Optional[str] = None
    escalation_reason: Optional[str] = None
    resolution_summary: Optional[str] = None
    resolution_category: Optional[str] = None
    satisfaction_score: Optional[int] = Field(None, ge=1, le=5)
    tags: Optional[List[str]] = None
    metadata: Optional[dict] = None


class TicketResponse(BaseModel):
    """
    Schema for ticket response.
    """
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    ticket_number: str
    customer_id: UUID
    subject: str
    description: Optional[str]
    channel: ChannelType
    status: TicketStatus
    priority: TicketPriority
    assigned_to: Optional[str]
    sla_tier: str
    first_response_due_at: Optional[datetime]
    first_response_at: Optional[datetime]
    resolution_due_at: Optional[datetime]
    resolved_at: Optional[datetime]
    closed_at: Optional[datetime]
    sla_breached: bool
    escalation_status: str
    escalation_level: int
    escalation_reason: Optional[str]
    escalated_at: Optional[datetime]
    escalated_to: Optional[str]
    resolution_summary: Optional[str]
    resolution_category: Optional[str]
    satisfaction_score: Optional[int]
    satisfaction_feedback: Optional[str]
    ai_handled: bool
    ai_model_used: Optional[str]
    total_ai_tokens: int
    total_ai_latency_ms: int
    handoff_to_human_at: Optional[datetime]
    tags: List[str]
    metadata: dict
    created_at: datetime
    updated_at: datetime


class TicketListResponse(BaseModel):
    """
    Schema for paginated ticket list.
    """
    tickets: List[TicketResponse]
    total: int
    page: int
    page_size: int

"""
Customer Pydantic schemas.
"""

from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr, ConfigDict


class CustomerBase(BaseModel):
    """
    Base customer schema.
    """
    email: Optional[str] = Field(None, description="Customer email address")
    phone: Optional[str] = Field(None, description="Customer phone number")
    full_name: Optional[str] = Field(None, description="Customer full name")
    company_name: Optional[str] = Field(None, description="Company name")
    customer_tier: Optional[str] = Field("standard", description="Customer tier")
    preferred_language: Optional[str] = Field("en", description="Preferred language")
    metadata: Optional[dict] = Field(default_factory=dict, description="Additional metadata")


class CustomerCreate(CustomerBase):
    """
    Schema for creating a customer.
    """
    email: Optional[str] = Field(None, description="Customer email address")
    full_name: Optional[str] = Field(None, description="Customer full name")
    preferred_channel: Optional[str] = Field("web_form", description="Preferred channel")


class CustomerUpdate(BaseModel):
    """
    Schema for updating a customer.
    All fields are optional.
    """
    email: Optional[str] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    customer_tier: Optional[str] = None
    preferred_channel: Optional[str] = None
    preferred_language: Optional[str] = None
    metadata: Optional[dict] = None
    is_blocked: Optional[bool] = None
    block_reason: Optional[str] = None


class CustomerResponse(CustomerBase):
    """
    Schema for customer response.
    """
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    customer_since: datetime
    total_tickets: int = 0
    resolved_tickets: int = 0
    avg_satisfaction_score: Optional[float] = None
    is_active: bool = True
    is_blocked: bool = False
    created_at: datetime
    updated_at: datetime
    last_interaction_at: Optional[datetime] = None


class CustomerListResponse(BaseModel):
    """
    Schema for paginated customer list.
    """
    customers: List[CustomerResponse]
    total: int
    page: int
    page_size: int

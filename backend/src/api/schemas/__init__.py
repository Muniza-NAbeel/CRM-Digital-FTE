"""
API Schemas module.
Pydantic models for request/response validation.
"""

from .common import BaseResponse, PaginatedResponse
from .customers import (
    CustomerResponse,
    CustomerCreate,
    CustomerUpdate,
    CustomerListResponse,
)
from .tickets import (
    TicketResponse,
    TicketCreate,
    TicketUpdate,
    TicketListResponse,
    TicketStatus,
    TicketPriority,
)

__all__ = [
    "BaseResponse",
    "PaginatedResponse",
    "CustomerResponse",
    "CustomerCreate",
    "CustomerUpdate",
    "CustomerListResponse",
    "TicketResponse",
    "TicketCreate",
    "TicketUpdate",
    "TicketListResponse",
    "TicketStatus",
    "TicketPriority",
]

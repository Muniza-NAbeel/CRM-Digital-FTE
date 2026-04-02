"""
Tickets API Routes

Core ticket management - the heart of the CRM system.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from asyncpg import Connection

from src.database import get_db_connection
from src.api.dependencies import get_pagination, PaginationParams
from src.api.schemas.tickets import (
    TicketResponse,
    TicketCreate,
    TicketUpdate,
    TicketListResponse,
    TicketStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=TicketListResponse)
async def list_tickets(
    pagination: PaginationParams = Depends(get_pagination),
    status_filter: Optional[TicketStatus] = Query(None, alias="status"),
    priority: Optional[str] = Query(None),
    customer_id: Optional[UUID] = Query(None),
    db: Connection = Depends(get_db_connection),
):
    """
    List tickets with filters and pagination.
    """
    base_query = "SELECT * FROM tickets WHERE 1=1"
    count_query = "SELECT COUNT(*) FROM tickets WHERE 1=1"
    
    params = []
    param_count = 1
    
    if status_filter:
        base_query += f" AND status = ${param_count}"
        count_query += f" AND status = ${param_count}"
        params.append(status_filter.value)
        param_count += 1
    
    if priority:
        base_query += f" AND priority = ${param_count}"
        count_query += f" AND priority = ${param_count}"
        params.append(priority)
        param_count += 1
    
    if customer_id:
        base_query += f" AND customer_id = ${param_count}"
        count_query += f" AND customer_id = ${param_count}"
        params.append(customer_id)
        param_count += 1
    
    base_query += f" ORDER BY created_at DESC LIMIT ${param_count} OFFSET ${param_count + 1}"
    params.extend([pagination.page_size, pagination.offset])
    
    tickets = await db.fetch(base_query, *params)
    total_count = await db.fetchval(count_query, *params[:-2])
    
    return TicketListResponse(
        tickets=[TicketResponse.model_validate(t) for t in tickets],
        total=int(total_count),
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: UUID,
    db: Connection = Depends(get_db_connection),
):
    """
    Get a specific ticket by ID.
    """
    ticket = await db.fetchrow(
        "SELECT * FROM tickets WHERE id = $1",
        ticket_id,
    )
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found",
        )
    
    return TicketResponse.model_validate(ticket)


@router.post("/", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    ticket_data: TicketCreate,
    db: Connection = Depends(get_db_connection),
):
    """
    Create a new ticket.

    This is the FIRST step in the customer support flow.
    Ticket MUST be created BEFORE any response is sent.
    """
    # Calculate SLA due dates based on tier
    sla_first_response_hours = 24  # Default standard
    sla_resolution_hours = 72

    if ticket_data.sla_tier == "premium":
        sla_first_response_hours = 4
        sla_resolution_hours = 24
    elif ticket_data.sla_tier == "enterprise":
        sla_first_response_hours = 1
        sla_resolution_hours = 8

    ticket = await db.fetchrow(
        """
        INSERT INTO tickets (
            customer_id, subject, description, channel,
            priority, sla_tier, first_response_due_at, resolution_due_at,
            metadata
        )
        VALUES ($1, $2, $3, $4, $5, $6,
                NOW() + INTERVAL '1 hour' * $7,
                NOW() + INTERVAL '1 hour' * $8,
                $9)
        RETURNING *
        """,
        ticket_data.customer_id,
        ticket_data.subject,
        ticket_data.description,
        ticket_data.channel,
        ticket_data.priority or "medium",
        ticket_data.sla_tier or "standard",
        sla_first_response_hours,
        sla_resolution_hours,
        ticket_data.metadata or {},
    )

    logger.info(f"Ticket created: {ticket['ticket_number']} for customer {ticket_data.customer_id}")

    # Publish event to Kafka (asynchronous - do not wait for processing)
    try:
        from src.kafka import publish_agent_event
        await publish_agent_event(
            event_type="ticket_created",
            ticket_id=str(ticket["id"]),
            customer_id=str(ticket_data.customer_id),
            event_data={
                "ticket_number": ticket["ticket_number"],
                "subject": ticket_data.subject,
                "channel": ticket_data.channel,
                "priority": ticket_data.priority or "medium",
            },
        )
        logger.info(f"Ticket creation event published to Kafka: {ticket['ticket_number']}")
    except Exception as e:
        logger.warning(f"Failed to publish ticket event to Kafka: {e}")
        # Continue anyway - Kafka has fallback to in-memory queue

    return TicketResponse.model_validate(ticket)


@router.put("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: UUID,
    ticket_data: TicketUpdate,
    db: Connection = Depends(get_db_connection),
):
    """
    Update a ticket (status, assignment, escalation, etc.).
    """
    updates = []
    params = []
    param_count = 1
    
    update_fields = ticket_data.model_dump(exclude_unset=True)
    
    # Handle escalation specially
    if "escalation_status" in update_fields:
        updates.append(f"escalation_status = ${param_count}")
        params.append(update_fields["escalation_status"])
        param_count += 1
        
        if update_fields["escalation_status"] == "escalated":
            updates.append(f"escalated_at = CURRENT_TIMESTAMP")
    
    # Handle status changes
    if "status" in update_fields:
        updates.append(f"status = ${param_count}")
        params.append(update_fields["status"])
        param_count += 1
        
        if update_fields["status"] == "resolved":
            updates.append(f"resolved_at = CURRENT_TIMESTAMP")
    
    # Handle other fields
    for field, value in update_fields.items():
        if field not in ["escalation_status", "status"]:
            updates.append(f"{field} = ${param_count}")
            params.append(value)
            param_count += 1
    
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )
    
    updates.append(f"updated_at = CURRENT_TIMESTAMP")
    params.append(ticket_id)
    
    query = f"""
    UPDATE tickets
    SET {', '.join(updates)}
    WHERE id = ${param_count}
    RETURNING *
    """
    
    ticket = await db.fetchrow(query, *params)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found",
        )
    
    logger.info(f"Ticket updated: {ticket_id} - {update_fields.keys()}")
    
    return TicketResponse.model_validate(ticket)


@router.post("/{ticket_id}/escalate", response_model=TicketResponse)
async def escalate_ticket(
    ticket_id: UUID,
    reason: str = Query(..., description="Escalation reason"),
    details: Optional[str] = Query(None, description="Additional details"),
    escalated_to: Optional[str] = Query(None, description="Escalate to specific person/team"),
    db: Connection = Depends(get_db_connection),
):
    """
    Escalate a ticket to human agent or higher level.
    """
    ticket = await db.fetchrow(
        """
        UPDATE tickets
        SET 
            escalation_status = 'escalated',
            escalation_level = escalation_level + 1,
            escalation_reason = $2,
            escalation_details = $3,
            escalated_to = $4,
            escalated_at = CURRENT_TIMESTAMP,
            status = 'escalated',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = $1
        RETURNING *
        """,
        ticket_id,
        reason,
        details,
        escalated_to,
    )
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found",
        )
    
    logger.info(f"Ticket escalated: {ticket_id} - reason: {reason}")
    
    return TicketResponse.model_validate(ticket)

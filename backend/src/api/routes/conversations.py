"""
Conversations API Routes

Cross-channel conversation thread management.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from asyncpg import Connection

from src.database import get_db_connection
from src.api.dependencies import get_pagination, PaginationParams

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def list_conversations(
    pagination: PaginationParams = Depends(get_pagination),
    ticket_id: Optional[UUID] = Query(None),
    customer_id: Optional[UUID] = Query(None),
    channel: Optional[str] = Query(None),
    db: Connection = Depends(get_db_connection),
):
    """
    List conversations with filters.
    """
    base_query = "SELECT * FROM conversations WHERE 1=1"
    count_query = "SELECT COUNT(*) FROM conversations WHERE 1=1"
    
    params = []
    param_count = 1
    
    if ticket_id:
        base_query += f" AND ticket_id = ${param_count}"
        count_query += f" AND ticket_id = ${param_count}"
        params.append(ticket_id)
        param_count += 1
    
    if customer_id:
        base_query += f" AND customer_id = ${param_count}"
        count_query += f" AND customer_id = ${param_count}"
        params.append(customer_id)
        param_count += 1
    
    if channel:
        base_query += f" AND channel = ${param_count}"
        count_query += f" AND channel = ${param_count}"
        params.append(channel)
        param_count += 1
    
    base_query += f" ORDER BY last_message_at DESC NULLS LAST LIMIT ${param_count} OFFSET ${param_count + 1}"
    params.extend([pagination.page_size, pagination.offset])
    
    conversations = await db.fetch(base_query, *params)
    total_count = await db.fetchval(count_query, *params[:-2])
    
    return {
        "conversations": [dict(c) for c in conversations],
        "total": int(total_count),
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    db: Connection = Depends(get_db_connection),
):
    """
    Get a specific conversation by ID.
    """
    conversation = await db.fetchrow(
        "SELECT * FROM conversations WHERE id = $1",
        conversation_id,
    )
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )
    
    return dict(conversation)


@router.get("/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: UUID,
    pagination: PaginationParams = Depends(get_pagination),
    db: Connection = Depends(get_db_connection),
):
    """
    Get all messages in a conversation.
    """
    messages = await db.fetch(
        """
        SELECT * FROM messages 
        WHERE conversation_id = $1 
        ORDER BY created_at ASC
        LIMIT $2 OFFSET $3
        """,
        conversation_id,
        pagination.page_size,
        pagination.offset,
    )
    
    total = await db.fetchval(
        "SELECT COUNT(*) FROM messages WHERE conversation_id = $1",
        conversation_id,
    )
    
    return {
        "messages": [dict(m) for m in messages],
        "total": int(total),
        "page": pagination.page,
        "page_size": pagination.page_size,
    }

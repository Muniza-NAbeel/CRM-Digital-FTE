"""
Agent Tools for Customer Success Agent

Tools available to the AI agent:
- create_ticket (MUST be called first)
- get_customer_history
- search_knowledge_base
- escalate_to_human
- send_response (MUST be called to respond)

All tools are wrapped with Pydantic validation and error handling.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
import json

from pydantic import BaseModel, Field, validator
from asyncpg import Connection

logger = logging.getLogger(__name__)


# ============================================================================
# Tool Input/Output Schemas (Pydantic)
# ============================================================================

class CreateTicketInput(BaseModel):
    """Input for create_ticket tool."""
    customer_id: str = Field(..., description="Customer UUID")
    subject: str = Field(..., min_length=5, max_length=512, description="Ticket subject")
    description: str = Field(..., min_length=1, max_length=10000, description="Issue description")
    channel: str = Field(..., description="Channel: web_form, gmail, whatsapp")
    priority: str = Field(default="medium", description="Priority: low, medium, high, critical")
    customer_email: Optional[str] = Field(None, description="Customer email")
    customer_phone: Optional[str] = Field(None, description="Customer phone")
    metadata: Optional[Dict] = Field(default_factory=dict, description="Additional metadata")


class CreateTicketOutput(BaseModel):
    """Output from create_ticket tool."""
    success: bool
    ticket_id: Optional[str] = None
    ticket_number: Optional[str] = None
    error: Optional[str] = None


class GetCustomerHistoryInput(BaseModel):
    """Input for get_customer_history tool."""
    customer_id: str = Field(..., description="Customer UUID")
    limit: int = Field(default=10, ge=1, le=50, description="Number of tickets to retrieve")


class CustomerHistoryOutput(BaseModel):
    """Output from get_customer_history tool."""
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_tier: str = "standard"
    total_tickets: int = 0
    resolved_tickets: int = 0
    recent_tickets: List[Dict] = Field(default_factory=list)
    avg_satisfaction: Optional[float] = None


class SearchKnowledgeBaseInput(BaseModel):
    """Input for search_knowledge_base tool."""
    query: str = Field(..., min_length=3, max_length=500, description="Search query")
    limit: int = Field(default=5, ge=1, le=20, description="Number of results")
    category: Optional[str] = Field(None, description="Optional category filter")


class KnowledgeBaseResult(BaseModel):
    """Single knowledge base result."""
    id: str
    title: str
    content: str
    category: Optional[str] = None
    relevance_score: float = 0.0


class SearchKnowledgeBaseOutput(BaseModel):
    """Output from search_knowledge_base tool."""
    results: List[KnowledgeBaseResult] = Field(default_factory=list)
    count: int = 0
    query: str


class EscalateToHumanInput(BaseModel):
    """Input for escalate_to_human tool."""
    ticket_id: str = Field(..., description="Ticket UUID")
    reason: str = Field(..., min_length=10, max_length=500, description="Escalation reason")
    details: Optional[str] = Field(None, description="Additional context")
    urgency: str = Field(default="normal", description="normal, high, critical")


class EscalateToHumanOutput(BaseModel):
    """Output from escalate_to_human tool."""
    success: bool
    escalated: bool = False
    assigned_to: Optional[str] = None
    error: Optional[str] = None


class SendResponseInput(BaseModel):
    """Input for send_response tool."""
    ticket_id: str = Field(..., description="Ticket UUID")
    conversation_id: str = Field(..., description="Conversation UUID")
    customer_id: str = Field(..., description="Customer UUID")
    message: str = Field(..., min_length=1, max_length=5000, description="Response message")
    channel: str = Field(..., description="Channel: web_form, gmail, whatsapp")
    is_final: bool = Field(default=False, description="Is this the final response?")
    requires_followup: bool = Field(default=False, description="Does this require follow-up?")


class SendResponseOutput(BaseModel):
    """Output from send_response tool."""
    success: bool
    message_id: Optional[str] = None
    delivery_status: str = "pending"
    error: Optional[str] = None


# ============================================================================
# Agent Tools Class
# ============================================================================

class AgentTools:
    """
    Tool implementations for Customer Success Agent.
    
    Each tool:
    - Validates input with Pydantic
    - Executes database operations
    - Handles errors gracefully
    - Returns structured output
    """
    
    def __init__(self, db_connection: Connection):
        """
        Initialize agent tools.

        Args:
            db_connection: Async PostgreSQL connection
        """
        self.db = db_connection
        self.logger = logging.getLogger(f"{__name__}.AgentTools")
        self._openai_client = None

    async def _get_openai_client(self):
        """Get or create OpenAI client."""
        if self._openai_client is None:
            try:
                from openai import AsyncOpenAI
                import os
                
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    self.logger.warning("OPENAI_API_KEY not found, using fallback")
                    return None
                
                self._openai_client = AsyncOpenAI(api_key=api_key)
                self.logger.info("OpenAI client initialized")
                return self._openai_client
                
            except Exception as e:
                self.logger.error(f"Failed to initialize OpenAI client: {e}", exc_info=True)
                return None
        
        return self._openai_client

    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for text using OpenAI embeddings API.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing embedding, or None if failed
        """
        try:
            client = await self._get_openai_client()
            if not client:
                return None
            
            response = await client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
                dimensions=1536
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            self.logger.error(f"Failed to generate embedding: {e}", exc_info=True)
            return None
    
    # ========================================================================
    # Tool: create_ticket
    # MUST be called first before any other action
    # ========================================================================
    
    async def create_ticket(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new support ticket.
        
        CRITICAL: This MUST be the first tool called for any new conversation.
        No response should be sent without a ticket.
        
        Args:
            input_data: Dict with customer_id, subject, description, channel, etc.
            
        Returns:
            Dict with ticket_id, ticket_number, success status
        """
        try:
            # Validate input
            validated = CreateTicketInput(**input_data)
            
            self.logger.info(f"Creating ticket for customer {validated.customer_id}")
            
            # Calculate SLA due dates based on tier
            # In production, fetch tier from customer record
            sla_hours = {
                "standard": (24, 72),
                "premium": (4, 24),
                "enterprise": (1, 8),
            }
            first_response_hours, resolution_hours = sla_hours.get("standard", (24, 72))
            
            # Create ticket
            ticket = await self.db.fetchrow(
                """
                INSERT INTO tickets (
                    customer_id, subject, description, channel,
                    priority, sla_tier, status, assigned_to,
                    first_response_due_at, resolution_due_at,
                    metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8,
                        NOW() + INTERVAL '1 hour' * $9,
                        NOW() + INTERVAL '1 hour' * $10,
                        $11)
                RETURNING id, ticket_number
                """,
                validated.customer_id,
                validated.subject,
                validated.description,
                validated.channel,
                validated.priority,
                "standard",
                "new",
                "ai_agent",
                first_response_hours,
                resolution_hours,
                validated.metadata or {},
            )
            
            # Create conversation linked to ticket
            conversation = await self.db.fetchrow(
                """
                INSERT INTO conversations (
                    ticket_id, customer_id, channel, status
                )
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                ticket["id"],
                validated.customer_id,
                validated.channel,
                "active",
            )
            
            self.logger.info(
                f"Ticket created: {ticket['ticket_number']} "
                f"(id={ticket['id']}, conversation={conversation['id']})"
            )
            
            return CreateTicketOutput(
                success=True,
                ticket_id=str(ticket["id"]),
                ticket_number=ticket["ticket_number"],
            ).model_dump()
            
        except Exception as e:
            self.logger.error(f"Failed to create ticket: {e}", exc_info=True)
            return CreateTicketOutput(
                success=False,
                error=f"Failed to create ticket: {str(e)}",
            ).model_dump()
    
    # ========================================================================
    # Tool: get_customer_history
    # ========================================================================
    
    async def get_customer_history(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get customer's ticket history and profile.
        
        Args:
            input_data: Dict with customer_id, limit
            
        Returns:
            Dict with customer info and recent tickets
        """
        try:
            validated = GetCustomerHistoryInput(**input_data)
            
            # Get customer profile
            customer = await self.db.fetchrow(
                """
                SELECT id, full_name, email, customer_tier,
                       total_tickets, resolved_tickets, avg_satisfaction_score
                FROM customers
                WHERE id = $1
                """,
                validated.customer_id,
            )
            
            if not customer:
                return CustomerHistoryOutput(
                    customer_tier="unknown",
                    error="Customer not found",
                ).model_dump()
            
            # Get recent tickets
            tickets = await self.db.fetch(
                """
                SELECT ticket_number, subject, status, priority,
                       created_at, resolved_at, satisfaction_score
                FROM tickets
                WHERE customer_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                validated.customer_id,
                validated.limit,
            )
            
            return CustomerHistoryOutput(
                customer_name=customer["full_name"],
                customer_email=customer["email"],
                customer_tier=customer["customer_tier"] or "standard",
                total_tickets=customer["total_tickets"] or 0,
                resolved_tickets=customer["resolved_tickets"] or 0,
                avg_satisfaction=float(customer["avg_satisfaction_score"]) if customer["avg_satisfaction_score"] else None,
                recent_tickets=[dict(t) for t in tickets],
            ).model_dump()
            
        except Exception as e:
            self.logger.error(f"Failed to get customer history: {e}", exc_info=True)
            return CustomerHistoryOutput(
                customer_tier="unknown",
                error=str(e),
            ).model_dump()
    
    # ========================================================================
    # Tool: search_knowledge_base
    # ========================================================================
    
    async def search_knowledge_base(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search knowledge base for relevant articles.
        
        Uses hybrid search:
        1. Vector similarity search (if embeddings available)
        2. Full-text search fallback

        Args:
            input_data: Dict with query, limit, category

        Returns:
            Dict with search results
        """
        try:
            validated = SearchKnowledgeBaseInput(**input_data)
            
            # Try vector search first
            embedding = await self._generate_embedding(validated.query)
            
            if embedding:
                # Vector similarity search with pgvector
                embedding_str = "[" + ",".join(map(str, embedding)) + "]"
                results = await self.db.fetch(
                    """
                    SELECT id, title, content, category,
                           1 - (embedding <=> $1::vector) AS similarity
                    FROM knowledge_base
                    WHERE status = 'published'
                      AND ($2::text IS NULL OR category = $2)
                    ORDER BY embedding <=> $1::vector
                    LIMIT $3
                    """,
                    embedding_str,
                    validated.category,
                    validated.limit,
                )
                
                self.logger.info(f"Vector search returned {len(results)} results")
                
            else:
                # Fallback to full-text search
                results = await self.db.fetch(
                    """
                    SELECT id, title, content, category,
                           ts_rank_cd(search_vector, to_tsquery('english', $1)) AS rank
                    FROM knowledge_base
                    WHERE status = 'published'
                      AND search_vector @@ to_tsquery('english', $1)
                      AND ($2::text IS NULL OR category = $2)
                    ORDER BY rank DESC
                    LIMIT $3
                    """,
                    validated.query,
                    validated.category,
                    validated.limit,
                )
                
                self.logger.info(f"Full-text search returned {len(results)} results")

            return SearchKnowledgeBaseOutput(
                results=[
                    KnowledgeBaseResult(
                        id=str(r["id"]),
                        title=r["title"],
                        content=r["content"][:500] + "..." if len(r["content"]) > 500 else r["content"],
                        category=r["category"],
                        relevance_score=float(r.get("similarity", r.get("rank", 0))),
                    )
                    for r in results
                ],
                count=len(results),
                query=validated.query,
            ).model_dump()

        except Exception as e:
            self.logger.error(f"Failed to search knowledge base: {e}", exc_info=True)
            return SearchKnowledgeBaseOutput(
                results=[],
                count=0,
                query=input_data.get("query", ""),
                error=str(e),
            ).model_dump()
    
    # ========================================================================
    # Tool: escalate_to_human
    # ========================================================================
    
    async def escalate_to_human(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Escalate ticket to human agent.
        
        Args:
            input_data: Dict with ticket_id, reason, details, urgency
            
        Returns:
            Dict with escalation status
        """
        try:
            validated = EscalateToHumanInput(**input_data)
            
            # Determine escalation level based on urgency
            urgency_levels = {
                "normal": 1,
                "high": 2,
                "critical": 3,
            }
            escalation_level = urgency_levels.get(validated.urgency, 1)
            
            # Determine assignment based on urgency
            assigned_to = "support_team"
            if validated.urgency == "critical":
                assigned_to = "senior_support"
            elif validated.urgency == "high":
                assigned_to = "support_lead"
            
            # Update ticket
            ticket = await self.db.fetchrow(
                """
                UPDATE tickets
                SET 
                    status = 'escalated',
                    escalation_status = 'escalated',
                    escalation_level = $2,
                    escalation_reason = 'customer_request',
                    escalation_details = $3,
                    assigned_to = $4,
                    escalated_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = $1
                RETURNING id, ticket_number
                """,
                validated.ticket_id,
                escalation_level,
                validated.details or validated.reason,
                assigned_to,
            )
            
            if not ticket:
                return EscalateToHumanOutput(
                    success=False,
                    error=f"Ticket {validated.ticket_id} not found",
                ).model_dump()
            
            self.logger.info(
                f"Ticket escalated: {ticket['ticket_number']} "
                f"to {assigned_to} (urgency={validated.urgency})"
            )
            
            return EscalateToHumanOutput(
                success=True,
                escalated=True,
                assigned_to=assigned_to,
            ).model_dump()
            
        except Exception as e:
            self.logger.error(f"Failed to escalate ticket: {e}", exc_info=True)
            return EscalateToHumanOutput(
                success=False,
                error=str(e),
            ).model_dump()
    
    # ========================================================================
    # Tool: send_response
    # MUST be called to send any response to customer
    # ========================================================================
    
    async def send_response(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send response to customer.
        
        CRITICAL: All customer responses MUST go through this tool.
        Never respond directly without using this tool.
        
        Args:
            input_data: Dict with ticket_id, conversation_id, customer_id, message, channel
            
        Returns:
            Dict with message_id and delivery status
        """
        try:
            validated = SendResponseInput(**input_data)
            
            self.logger.info(
                f"Sending response to ticket {validated.ticket_id} "
                f"via {validated.channel}"
            )
            
            # Create message record
            message = await self.db.fetchrow(
                """
                INSERT INTO messages (
                    ticket_id, conversation_id, customer_id,
                    content, content_type, direction, channel,
                    sentiment, delivery_status,
                    ai_model_used, ai_handled,
                    metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                RETURNING id
                """,
                validated.ticket_id,
                validated.conversation_id,
                validated.customer_id,
                validated.message,
                "text/plain",
                "outbound",
                validated.channel,
                "neutral",
                "sent",
                "gpt-4",
                True,
                {
                    "is_final": validated.is_final,
                    "requires_followup": validated.requires_followup,
                },
            )
            
            # Update ticket status if this is first response
            await self.db.execute(
                """
                UPDATE tickets
                SET first_response_at = CURRENT_TIMESTAMP
                WHERE id = $1 AND first_response_at IS NULL
                """,
                validated.ticket_id,
            )
            
            # Update conversation
            await self.db.execute(
                """
                UPDATE conversations
                SET 
                    last_message_at = CURRENT_TIMESTAMP,
                    last_message_from = 'agent',
                    message_count = message_count + 1
                WHERE id = $1
                """,
                validated.conversation_id,
            )
            
            # If final response, mark ticket as pending customer or resolved
            if validated.is_final:
                await self.db.execute(
                    """
                    UPDATE tickets
                    SET status = 'pending_customer',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = $1
                    """,
                    validated.ticket_id,
                )
            
            self.logger.info(
                f"Response sent: message_id={message['id']}, "
                f"ticket={validated.ticket_id}"
            )
            
            return SendResponseOutput(
                success=True,
                message_id=str(message["id"]),
                delivery_status="sent",
            ).model_dump()
            
        except Exception as e:
            self.logger.error(f"Failed to send response: {e}", exc_info=True)
            return SendResponseOutput(
                success=False,
                error=f"Failed to send response: {str(e)}",
            ).model_dump()
    
    # ========================================================================
    # Helper: Get ticket and conversation info
    # ========================================================================
    
    async def get_ticket_info(self, ticket_id: str) -> Optional[Dict]:
        """
        Get ticket details for context.
        """
        try:
            ticket = await self.db.fetchrow(
                """
                SELECT t.*, c.full_name as customer_name, c.email as customer_email
                FROM tickets t
                JOIN customers c ON t.customer_id = c.id
                WHERE t.id = $1
                """,
                ticket_id,
            )
            return dict(ticket) if ticket else None
        except Exception as e:
            self.logger.error(f"Failed to get ticket info: {e}")
            return None

"""
Customer Success Agent using OpenAI Agents SDK

Main agent implementation that:
- Processes incoming messages
- Uses tools for all actions
- Enforces ticket-first policy
- Adapts responses per channel
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID

from asyncpg import Connection

from .tools import AgentTools
from .prompts import SystemPrompts
from ..services import TicketLifecycleManager, EscalationReason

logger = logging.getLogger(__name__)


class AgentContext:
    """
    Context for agent conversation.
    Tracks state across multiple turns.
    """
    
    def __init__(
        self,
        ticket_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        channel: str = "web_form",
    ):
        self.ticket_id = ticket_id
        self.conversation_id = conversation_id
        self.customer_id = customer_id
        self.channel = channel
        self.ticket_created = ticket_id is not None
        self.response_sent = False
        self.escalated = False
        self.message_count = 0
        self.metadata: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticket_id": self.ticket_id,
            "conversation_id": self.conversation_id,
            "customer_id": self.customer_id,
            "channel": self.channel,
            "ticket_created": self.ticket_created,
            "response_sent": self.response_sent,
            "escalated": self.escalated,
            "message_count": self.message_count,
        }


class CustomerSuccessAgent:
    """
    Customer Success AI Agent using OpenAI Agents SDK.
    
    This agent:
    1. ALWAYS creates a ticket first
    2. Uses tools for all actions
    3. NEVER responds directly (always via send_response tool)
    4. Adapts tone per channel (email/WhatsApp/web)
    5. Escalates based on rules
    
    Usage:
        agent = CustomerSuccessAgent(db_connection)
        result = await agent.process_message(
            content="I can't log in",
            customer_email="user@example.com",
            channel="web_form",
        )
    """
    
    def __init__(
        self,
        db_connection: Connection,
        openai_api_key: Optional[str] = None,
        model: str = "gpt-4",
        kafka_producer=None,
    ):
        """
        Initialize Customer Success Agent.

        Args:
            db_connection: Async PostgreSQL connection
            openai_api_key: OpenAI API key (falls back to env)
            model: OpenAI model to use
            kafka_producer: Kafka producer for events (optional)
        """
        self.db = db_connection
        self.model = model
        self.openai_api_key = openai_api_key
        self.kafka_producer = kafka_producer
        self.tools = AgentTools(db_connection)
        self.lifecycle = TicketLifecycleManager(db_connection, kafka_producer)
        self.logger = logging.getLogger(f"{__name__}.CustomerSuccessAgent")

        # Agent state
        self._context: Optional[AgentContext] = None
        self._conversation_history: List[Dict[str, str]] = []
    
    async def process_message(
        self,
        content: str,
        customer_id: str,
        channel: str = "web_form",
        ticket_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        customer_email: Optional[str] = None,
        customer_phone: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Process incoming customer message.
        
        CRITICAL FLOW:
        1. Create ticket (if new conversation)
        2. Get customer history
        3. Search knowledge base
        4. Generate response via AI
        5. Send response via tool
        
        Args:
            content: Customer message content
            customer_id: Customer UUID
            channel: Channel type (web_form, gmail, whatsapp)
            ticket_id: Existing ticket ID (if any)
            conversation_id: Existing conversation ID (if any)
            customer_email: Customer email (for lookup if no customer_id)
            customer_phone: Customer phone (for lookup if no customer_id)
            metadata: Additional metadata
            
        Returns:
            Dict with processing result including ticket_id, message_id, etc.
        """
        self.logger.info(
            f"Processing message from customer {customer_id} via {channel}"
        )
        
        try:
            # Initialize context
            self._context = AgentContext(
                ticket_id=ticket_id,
                conversation_id=conversation_id,
                customer_id=customer_id,
                channel=channel,
            )
            
            # Step 1: Create ticket if not exists (MANDATORY FIRST STEP)
            if not ticket_id:
                ticket_result = await self._create_ticket(
                    content=content,
                    customer_id=customer_id,
                    channel=channel,
                    customer_email=customer_email,
                    customer_phone=customer_phone,
                    metadata=metadata,
                )
                
                if not ticket_result.get("success"):
                    self.logger.error(f"Failed to create ticket: {ticket_result}")
                    return {
                        "success": False,
                        "error": "Failed to create ticket",
                        "details": ticket_result.get("error"),
                    }
                
                self._context.ticket_id = ticket_result.get("ticket_id")
                self._context.ticket_created = True
                
                self.logger.info(f"Ticket created: {self._context.ticket_id}")
            
            # Step 2: Get customer history
            history_result = await self.tools.get_customer_history({
                "customer_id": customer_id,
                "limit": 5,
            })
            
            # Step 3: Search knowledge base
            kb_result = await self.tools.search_knowledge_base({
                "query": self._extract_search_query(content),
                "limit": 3,
            })
            
            # Step 4: Generate AI response
            ai_response = await self._generate_ai_response(
                customer_message=content,
                customer_history=history_result,
                kb_results=kb_result,
                channel=channel,
            )
            
            # Step 5: Send response via tool (MANDATORY)
            response_result = await self.tools.send_response({
                "ticket_id": self._context.ticket_id,
                "conversation_id": self._get_or_create_conversation(),
                "customer_id": customer_id,
                "message": ai_response.get("response", ""),
                "channel": channel,
                "is_final": ai_response.get("is_final", False),
                "requires_followup": ai_response.get("requires_followup", False),
            })
            
            self._context.response_sent = True
            self._context.message_count += 1

            # Check if escalation needed (AI-detected)
            if ai_response.get("should_escalate"):
                escalation_result = await self.tools.escalate_to_human({
                    "ticket_id": self._context.ticket_id,
                    "reason": ai_response.get("escalation_reason", "AI request"),
                    "details": ai_response.get("escalation_details"),
                    "urgency": ai_response.get("escalation_urgency", "normal"),
                })
                self._context.escalated = escalation_result.get("escalated", False)
            
            # Also check lifecycle-based escalation (sentiment, keywords, etc.)
            if not self._context.escalated:
                escalation_reason = await self.lifecycle.check_escalation(
                    ticket_id=self._context.ticket_id,
                    content=content,
                    sentiment_score=ai_response.get("sentiment_score"),
                    customer_id=customer_id,
                )
                if escalation_reason:
                    self._context.escalated = True
                    self._context.metadata["escalation_reason"] = escalation_reason.value

            return {
                "success": True,
                "ticket_id": self._context.ticket_id,
                "ticket_number": ticket_result.get("ticket_number") if not ticket_id else None,
                "conversation_id": self._context.conversation_id,
                "message_id": response_result.get("message_id"),
                "response_sent": True,
                "escalated": self._context.escalated,
                "ai_tokens": ai_response.get("tokens", 0),
                "ai_latency_ms": ai_response.get("latency_ms", 0),
            }
            
        except Exception as e:
            self.logger.error(f"Error processing message: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Processing failed: {str(e)}",
            }
    
    async def _create_ticket(
        self,
        content: str,
        customer_id: str,
        channel: str,
        customer_email: Optional[str],
        customer_phone: Optional[str],
        metadata: Optional[Dict],
    ) -> Dict[str, Any]:
        """
        Create ticket (MUST be first action).
        """
        # Extract subject from first line or first sentence
        subject = content.split("\n")[0][:100]
        if len(subject) < 10:
            subject = content[:100]
        
        return await self.tools.create_ticket({
            "customer_id": customer_id,
            "subject": f"Support Request - {subject[:50]}",
            "description": content,
            "channel": channel,
            "priority": "medium",
            "customer_email": customer_email,
            "customer_phone": customer_phone,
            "metadata": metadata or {},
        })
    
    def _get_or_create_conversation(self) -> str:
        """
        Get or create conversation ID.
        """
        if self._context.conversation_id:
            return self._context.conversation_id
        
        # In production, create conversation record here
        # For now, generate a placeholder
        import uuid
        self._context.conversation_id = str(uuid.uuid4())
        return self._context.conversation_id
    
    def _extract_search_query(self, content: str) -> str:
        """
        Extract search query from customer message for KB search.
        """
        # Simple extraction - in production, use AI to extract key topics
        words = content.split()
        # Take significant words (skip common words)
        skip_words = {"i", "my", "the", "a", "an", "is", "are", "was", "were", 
                      "have", "has", "had", "do", "does", "did", "can", "could",
                      "will", "would", "should", "to", "of", "in", "for", "on",
                      "with", "at", "by", "from", "as", "into", "through",
                      "help", "please", "need", "want", "trying"}
        
        significant = [w.lower().strip(".,!?;:") for w in words 
                       if w.lower() not in skip_words and len(w) > 2]
        
        return " ".join(significant[:10]) or content[:50]
    
    async def _generate_ai_response(
        self,
        customer_message: str,
        customer_history: Dict[str, Any],
        kb_results: Dict[str, Any],
        channel: str,
    ) -> Dict[str, Any]:
        """
        Generate response using OpenAI.
        
        This method would use OpenAI Agents SDK in production.
        For now, it's a placeholder that demonstrates the structure.
        """
        import time
        start_time = time.time()
        
        try:
            # Import OpenAI
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI(api_key=self.openai_api_key)
            
            # Build messages for AI
            system_prompt = SystemPrompts.get_system_prompt(
                channel=channel,
                include_sentiment=True,
            )
            
            # Build user message with context
            user_content = self._build_user_message(
                customer_message=customer_message,
                customer_history=customer_history,
                kb_results=kb_results,
            )
            
            # Call OpenAI
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.7,
                max_tokens=1000,
            )
            
            ai_response = response.choices[0].message.content
            
            # Parse response for escalation signals
            should_escalate = self._check_escalation_signals(ai_response, customer_message)
            
            return {
                "response": ai_response,
                "is_final": not should_escalate,
                "requires_followup": False,
                "should_escalate": should_escalate,
                "escalation_reason": None,
                "escalation_details": None,
                "escalation_urgency": "normal",
                "tokens": response.usage.total_tokens if response.usage else 0,
                "latency_ms": int((time.time() - start_time) * 1000),
            }
            
        except ImportError:
            self.logger.warning("OpenAI not available, using fallback response")
            return self._fallback_response(channel)
        except Exception as e:
            self.logger.error(f"AI generation failed: {e}")
            return self._fallback_response(channel)
    
    def _build_user_message(
        self,
        customer_message: str,
        customer_history: Dict[str, Any],
        kb_results: Dict[str, Any],
    ) -> str:
        """
        Build user message for AI with context.
        """
        context_parts = []
        
        # Customer message
        context_parts.append(f"Customer Message:\n{customer_message}\n")
        
        # Customer history summary
        if customer_history.get("customer_name"):
            context_parts.append(
                f"Customer: {customer_history['customer_name']} "
                f"({customer_history.get('customer_email', 'N/A')})"
            )
            context_parts.append(
                f"Tier: {customer_history.get('customer_tier', 'standard')}"
            )
            context_parts.append(
                f"Total Tickets: {customer_history.get('total_tickets', 0)}"
            )
            context_parts.append("")
        
        # Knowledge base results
        if kb_results.get("results"):
            context_parts.append("Knowledge Base Articles:")
            for result in kb_results["results"][:2]:
                context_parts.append(f"- {result['title']}: {result['content'][:200]}...")
            context_parts.append("")
        
        # Recent tickets
        if customer_history.get("recent_tickets"):
            context_parts.append("Recent Tickets:")
            for ticket in customer_history["recent_tickets"][:3]:
                context_parts.append(
                    f"- {ticket['ticket_number']}: {ticket['subject']} "
                    f"({ticket['status']})"
                )
        
        return "\n".join(context_parts)
    
    def _check_escalation_signals(
        self,
        response: str,
        customer_message: str,
    ) -> bool:
        """
        Check if response indicates need for escalation.
        """
        escalation_keywords = [
            "escalate", "human agent", "speak to someone",
            "specialist", "supervisor", "manager",
            "unable to resolve", "beyond my capabilities",
        ]
        
        response_lower = response.lower()
        message_lower = customer_message.lower()
        
        # Check customer message for escalation requests
        if any(word in message_lower for word in ["human", "person", "real agent", "supervisor"]):
            return True
        
        # Check response for escalation signals
        if any(word in response_lower for word in escalation_keywords):
            return True
        
        return False
    
    def _fallback_response(self, channel: str) -> Dict[str, Any]:
        """
        Fallback response when AI is unavailable.
        """
        fallback_messages = {
            "gmail": """Dear Valued Customer,

Thank you for contacting our support team. We have received your inquiry and are reviewing it.

Your ticket has been created and our team will respond with a detailed solution shortly.

Best regards,
Customer Success Team""",
            
            "whatsapp": """Hi! Thanks for reaching out. We've received your message and are looking into it. Our team will get back to you soon with a solution! 😊""",
            
            "web_form": """Hello,

Thank you for contacting us. We have received your support request and our team is reviewing it.

You will receive a detailed response shortly.

Best regards,
Customer Success Team""",
        }
        
        return {
            "response": fallback_messages.get(channel, fallback_messages["web_form"]),
            "is_final": False,
            "requires_followup": True,
            "should_escalate": False,
            "tokens": 0,
            "latency_ms": 0,
        }
    
    def get_context(self) -> Optional[AgentContext]:
        """
        Get current agent context.
        """
        return self._context
    
    def clear_context(self):
        """
        Clear agent context for new conversation.
        """
        self._context = None
        self._conversation_history = []

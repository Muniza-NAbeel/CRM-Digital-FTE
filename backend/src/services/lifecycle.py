"""
Ticket Lifecycle and Escalation Engine

Manages ticket state transitions and automatic escalation.

States:
- open (new ticket)
- in_progress (being handled)
- resolved (solution provided)
- escalated (transferred to human)
- closed (finalized)

Escalation Triggers:
- Negative sentiment detection
- Pricing/refund/legal queries
- Repeated failures
- VIP customer issues
- SLA breach risk
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# Ticket States
# ============================================================================

class TicketState(str, Enum):
    """
    Ticket lifecycle states.
    """
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    CLOSED = "closed"


class EscalationReason(str, Enum):
    """
    Reasons for ticket escalation.
    """
    NEGATIVE_SENTIMENT = "negative_sentiment"
    CUSTOMER_REQUEST = "customer_request"
    PRICING_QUERY = "pricing_query"
    REFUND_QUERY = "refund_query"
    LEGAL_QUERY = "legal_query"
    REPEATED_FAILURE = "repeated_failure"
    VIP_CUSTOMER = "vip_customer"
    SLA_BREACH_RISK = "sla_breach_risk"
    COMPLEX_ISSUE = "complex_issue"
    AI_CONFIDENCE_LOW = "ai_confidence_low"
    MANUAL_REVIEW = "manual_review"


class EscalationLevel(str, Enum):
    """
    Escalation severity levels.
    """
    LEVEL_1 = "level_1"  # Standard support
    LEVEL_2 = "level_2"  # Senior support
    LEVEL_3 = "level_3"  # Specialist/Manager
    CRITICAL = "critical"  # Urgent escalation


# ============================================================================
# State Transition Rules
# ============================================================================

class StateTransition:
    """
    Defines valid state transitions.
    """
    
    # Valid transitions from each state
    VALID_TRANSITIONS = {
        TicketState.OPEN: [
            TicketState.IN_PROGRESS,
            TicketState.ESCALATED,
            TicketState.CLOSED,
        ],
        TicketState.IN_PROGRESS: [
            TicketState.RESOLVED,
            TicketState.ESCALATED,
            TicketState.CLOSED,
        ],
        TicketState.RESOLVED: [
            TicketState.IN_PROGRESS,  # Reopened
            TicketState.CLOSED,
        ],
        TicketState.ESCALATED: [
            TicketState.IN_PROGRESS,  # Returned from escalation
            TicketState.RESOLVED,
            TicketState.CLOSED,
        ],
        TicketState.CLOSED: [
            TicketState.IN_PROGRESS,  # Reopened (rare)
        ],
    }
    
    @classmethod
    def is_valid(cls, from_state: TicketState, to_state: TicketState) -> bool:
        """
        Check if transition is valid.
        """
        allowed = cls.VALID_TRANSITIONS.get(from_state, [])
        return to_state in allowed
    
    @classmethod
    def get_allowed_transitions(cls, state: TicketState) -> List[TicketState]:
        """
        Get allowed transitions from a state.
        """
        return cls.VALID_TRANSITIONS.get(state, [])


# ============================================================================
# Escalation Trigger Detection
# ============================================================================

class EscalationTriggers:
    """
    Detects conditions that should trigger escalation.
    """
    
    # Keywords that indicate escalation-needed topics
    PRICING_KEYWORDS = [
        "price", "pricing", "cost", "expensive", "cheap", "afford",
        "payment", "pay", "bill", "billing", "charge", "fee",
        "subscription", "plan", "upgrade", "downgrade",
    ]
    
    REFUND_KEYWORDS = [
        "refund", "return", "money back", "cancel", "cancellation",
        "reimburse", "chargeback", "dispute",
    ]
    
    LEGAL_KEYWORDS = [
        "law", "legal", "lawyer", "attorney", "sue", "lawsuit",
        "court", "regulation", "compliance", "gdpr", "privacy",
        "terms", "contract", "agreement", "liability",
    ]
    
    NEGATIVE_SENTIMENT_KEYWORDS = [
        "angry", "frustrated", "disappointed", "terrible", "awful",
        "worst", "hate", "useless", "waste", "scam", "fraud",
        "unacceptable", "ridiculous", "outrageous",
    ]
    
    ESCALATION_REQUEST_KEYWORDS = [
        "human", "person", "agent", "supervisor", "manager",
        "speak to someone", "real person", "customer service",
        "escalate", "escalation", "complaint",
    ]
    
    @classmethod
    def check_pricing_query(cls, content: str) -> bool:
        """
        Check if message contains pricing-related queries.
        """
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in cls.PRICING_KEYWORDS)
    
    @classmethod
    def check_refund_query(cls, content: str) -> bool:
        """
        Check if message contains refund-related queries.
        """
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in cls.REFUND_KEYWORDS)
    
    @classmethod
    def check_legal_query(cls, content: str) -> bool:
        """
        Check if message contains legal-related queries.
        """
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in cls.LEGAL_KEYWORDS)
    
    @classmethod
    def check_escalation_request(cls, content: str) -> bool:
        """
        Check if customer is requesting human agent.
        """
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in cls.ESCALATION_REQUEST_KEYWORDS)
    
    @classmethod
    def check_negative_sentiment_keywords(cls, content: str) -> bool:
        """
        Check for negative sentiment keywords (fallback if no sentiment analysis).
        """
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in cls.NEGATIVE_SENTIMENT_KEYWORDS)
    
    @classmethod
    def detect_escalation_need(
        cls,
        content: str,
        sentiment_score: Optional[float] = None,
        customer_tier: str = "standard",
        failure_count: int = 0,
    ) -> Optional[EscalationReason]:
        """
        Detect if escalation is needed based on message content and context.
        
        Args:
            content: Customer message content
            sentiment_score: Sentiment score (-1.0 to 1.0)
            customer_tier: Customer tier (standard, premium, enterprise)
            failure_count: Number of previous failed resolutions
            
        Returns:
            EscalationReason if escalation needed, None otherwise
        """
        # Check for explicit escalation request (highest priority)
        if cls.check_escalation_request(content):
            return EscalationReason.CUSTOMER_REQUEST
        
        # Check for legal queries (must escalate)
        if cls.check_legal_query(content):
            return EscalationReason.LEGAL_QUERY
        
        # Check for refund queries (usually needs human)
        if cls.check_refund_query(content):
            return EscalationReason.REFUND_QUERY
        
        # Check for pricing queries (may need sales/billing team)
        if cls.check_pricing_query(content):
            return EscalationReason.PRICING_QUERY
        
        # Check sentiment score
        if sentiment_score is not None and sentiment_score < -0.5:
            return EscalationReason.NEGATIVE_SENTIMENT
        
        # Check negative keywords
        if cls.check_negative_sentiment_keywords(content):
            return EscalationReason.NEGATIVE_SENTIMENT
        
        # Check repeated failures
        if failure_count >= 2:
            return EscalationReason.REPEATED_FAILURE
        
        # Check VIP customer with complex issues
        if customer_tier in ["premium", "enterprise"] and failure_count >= 1:
            return EscalationReason.VIP_CUSTOMER
        
        return None


# ============================================================================
# Escalation Configuration
# ============================================================================

@dataclass
class EscalationConfig:
    """
    Configuration for escalation behavior.
    """
    # Sentiment threshold for auto-escalation
    sentiment_threshold: float = -0.5
    
    # Max AI attempts before escalation
    max_ai_attempts: int = 3
    
    # Auto-escalate for VIP customers
    vip_auto_escalate: bool = False
    
    # Escalation assignments by level
    assignments: Dict[str, str] = field(default_factory=lambda: {
        "level_1": "support_team",
        "level_2": "senior_support",
        "level_3": "support_manager",
        "critical": "on_call_manager",
    })
    
    # SLA breach warning threshold (minutes before breach)
    sla_warning_threshold: int = 60


# ============================================================================
# Ticket Lifecycle Manager
# ============================================================================

class TicketLifecycleManager:
    """
    Manages ticket state transitions and escalation logic.
    
    Usage:
        lifecycle = TicketLifecycleManager(db_connection, kafka_producer)
        
        # Transition state
        await lifecycle.transition(ticket_id, TicketState.IN_PROGRESS)
        
        # Check and apply escalation
        await lifecycle.check_escalation(ticket_id, content, sentiment_score)
        
        # Auto-close resolved tickets
        await lifecycle.auto_close_resolved_tickets()
    """
    
    def __init__(
        self,
        db_connection,
        kafka_producer=None,
        config: Optional[EscalationConfig] = None,
    ):
        """
        Initialize lifecycle manager.
        
        Args:
            db_connection: Async PostgreSQL connection
            kafka_producer: Kafka producer for events
            config: Escalation configuration
        """
        self.db = db_connection
        self.producer = kafka_producer
        self.config = config or EscalationConfig()
        self.logger = logging.getLogger(f"{__name__}.TicketLifecycleManager")
    
    async def transition(
        self,
        ticket_id: str,
        new_state: TicketState,
        reason: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """
        Transition ticket to new state.
        
        Args:
            ticket_id: Ticket UUID
            new_state: Target state
            reason: Reason for transition
            metadata: Additional metadata
            
        Returns:
            bool: True if transition successful
        """
        try:
            # Get current state
            ticket = await self.db.fetchrow(
                "SELECT id, status FROM tickets WHERE id = $1",
                ticket_id,
            )
            
            if not ticket:
                self.logger.error(f"Ticket not found: {ticket_id}")
                return False
            
            current_state = TicketState(ticket["status"])
            
            # Validate transition
            if not StateTransition.is_valid(current_state, new_state):
                self.logger.warning(
                    f"Invalid transition: {current_state} → {new_state} "
                    f"for ticket {ticket_id}"
                )
                return False
            
            # Build update query
            updates = ["status = $2"]
            params = [ticket_id, new_state.value]
            param_count = 3
            
            # Add state-specific updates
            if new_state == TicketState.IN_PROGRESS:
                updates.append(f"assigned_at = CURRENT_TIMESTAMP")
            
            elif new_state == TicketState.RESOLVED:
                updates.append(f"resolved_at = CURRENT_TIMESTAMP")
                updates.append(f"status = $3")
                params[-1] = "resolved"
                param_count += 1
            
            elif new_state == TicketState.ESCALATED:
                updates.append(f"escalated_at = CURRENT_TIMESTAMP")
            
            elif new_state == TicketState.CLOSED:
                updates.append(f"closed_at = CURRENT_TIMESTAMP")
            
            # Add metadata
            if metadata:
                updates.append(f"metadata = COALESCE(metadata, '{{}}'::jsonb) || ${param_count}")
                params.append(json.dumps(metadata))
                param_count += 1
            
            # Add reason to metadata
            if reason:
                reason_meta = {"transition_reason": reason}
                updates.append(f"metadata = COALESCE(metadata, '{{}}'::jsonb) || ${param_count}")
                params.append(json.dumps(reason_meta))
            
            # Execute update
            query = f"""
            UPDATE tickets
            SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            RETURNING id, status, ticket_number
            """
            
            result = await self.db.fetchrow(query, *params)
            
            self.logger.info(
                f"Ticket transition: {ticket_id} ({result['ticket_number']}) "
                f"{current_state.value} → {new_state.value}"
            )
            
            # Publish event
            if self.producer:
                await self.producer.send_event(
                    event_type="ticket_state_changed",
                    event_data={
                        "ticket_id": ticket_id,
                        "ticket_number": result["ticket_number"],
                        "from_state": current_state.value,
                        "to_state": new_state.value,
                        "reason": reason,
                    },
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Transition failed: {e}", exc_info=True)
            return False
    
    async def check_escalation(
        self,
        ticket_id: str,
        content: str,
        sentiment_score: Optional[float] = None,
        customer_id: Optional[str] = None,
    ) -> Optional[EscalationReason]:
        """
        Check if ticket needs escalation and apply if needed.
        
        Args:
            ticket_id: Ticket UUID
            content: Customer message content
            sentiment_score: Sentiment score (-1.0 to 1.0)
            customer_id: Customer UUID (for tier lookup)
            
        Returns:
            EscalationReason if escalated, None otherwise
        """
        try:
            # Get ticket and customer info
            ticket = await self.db.fetchrow(
                """
                SELECT t.*, c.customer_tier
                FROM tickets t
                JOIN customers c ON t.customer_id = c.id
                WHERE t.id = $1
                """,
                ticket_id,
            )
            
            if not ticket:
                return None
            
            # Get failure count for this ticket
            failure_count = ticket.get("handoff_count", 0)
            customer_tier = ticket.get("customer_tier", "standard")
            
            # Detect escalation need
            escalation_reason = EscalationTriggers.detect_escalation_need(
                content=content,
                sentiment_score=sentiment_score,
                customer_tier=customer_tier,
                failure_count=failure_count,
            )
            
            if escalation_reason:
                self.logger.info(
                    f"Escalation triggered for ticket {ticket_id}: "
                    f"{escalation_reason.value}"
                )
                
                # Determine escalation level
                level = self._determine_escalation_level(
                    escalation_reason, customer_tier
                )
                
                # Apply escalation
                await self.escalate(
                    ticket_id=ticket_id,
                    reason=escalation_reason,
                    level=level,
                    content=content,
                    sentiment_score=sentiment_score,
                )
                
                return escalation_reason
            
            return None
            
        except Exception as e:
            self.logger.error(f"Escalation check failed: {e}", exc_info=True)
            return None
    
    async def escalate(
        self,
        ticket_id: str,
        reason: EscalationReason,
        level: EscalationLevel = EscalationLevel.LEVEL_1,
        details: Optional[str] = None,
        content: Optional[str] = None,
        sentiment_score: Optional[float] = None,
    ) -> bool:
        """
        Escalate ticket to human agent.
        
        Args:
            ticket_id: Ticket UUID
            reason: Escalation reason
            level: Escalation level
            details: Additional details
            content: Original message content
            sentiment_score: Sentiment score
            
        Returns:
            bool: True if escalation successful
        """
        try:
            # Get assignment for level
            assigned_to = self.config.assignments.get(level.value, "support_team")
            
            # Build escalation details
            escalation_details = {
                "reason": reason.value,
                "level": level.value,
                "triggered_at": datetime.utcnow().isoformat(),
                "sentiment_score": sentiment_score,
                "details": details,
            }
            
            if content:
                escalation_details["trigger_content"] = content[:500]
            
            # Update ticket
            result = await self.db.fetchrow(
                """
                UPDATE tickets
                SET 
                    status = 'escalated',
                    escalation_status = 'escalated',
                    escalation_level = $2,
                    escalation_reason = $3,
                    escalation_details = $4,
                    assigned_to = $5,
                    escalated_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = $1
                RETURNING id, ticket_number
                """,
                ticket_id,
                level.value,
                reason.value,
                json.dumps(escalation_details),
                assigned_to,
            )
            
            if not result:
                self.logger.error(f"Ticket not found for escalation: {ticket_id}")
                return False
            
            self.logger.info(
                f"Ticket escalated: {ticket_id} ({result['ticket_number']}) "
                f"reason={reason.value}, level={level.value}, assigned_to={assigned_to}"
            )
            
            # Publish event
            if self.producer:
                await self.producer.send_event(
                    event_type="ticket_escalated",
                    event_data={
                        "ticket_id": ticket_id,
                        "ticket_number": result["ticket_number"],
                        "reason": reason.value,
                        "level": level.value,
                        "assigned_to": assigned_to,
                        "sentiment_score": sentiment_score,
                    },
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Escalation failed: {e}", exc_info=True)
            return False
    
    def _determine_escalation_level(
        self,
        reason: EscalationReason,
        customer_tier: str,
    ) -> EscalationLevel:
        """
        Determine escalation level based on reason and customer tier.
        """
        # Critical issues
        if reason in [EscalationReason.LEGAL_QUERY]:
            return EscalationLevel.CRITICAL
        
        # High priority
        if reason in [EscalationReason.REFUND_QUERY, EscalationReason.NEGATIVE_SENTIMENT]:
            if customer_tier == "enterprise":
                return EscalationLevel.LEVEL_3
            return EscalationLevel.LEVEL_2
        
        # VIP customers
        if customer_tier == "enterprise":
            return EscalationLevel.LEVEL_2
        if customer_tier == "premium":
            return EscalationLevel.LEVEL_2
        
        # Standard escalation
        return EscalationLevel.LEVEL_1
    
    async def increment_handoff_count(self, ticket_id: str) -> int:
        """
        Increment AI handoff count for ticket.
        
        Returns:
            int: New handoff count
        """
        result = await self.db.fetchrow(
            """
            UPDATE tickets
            SET handoff_count = handoff_count + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            RETURNING handoff_count
            """,
            ticket_id,
        )
        
        if result:
            return result["handoff_count"]
        return 0
    
    async def auto_close_resolved_tickets(
        self,
        days_after_resolution: int = 7,
    ) -> int:
        """
        Auto-close tickets that have been resolved for N days.
        
        Args:
            days_after_resolution: Days after resolution to auto-close
            
        Returns:
            int: Number of tickets closed
        """
        try:
            cutoff = datetime.utcnow() - timedelta(days=days_after_resolution)
            
            result = await self.db.execute(
                """
                UPDATE tickets
                SET 
                    status = 'closed',
                    closed_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE status = 'resolved'
                  AND resolved_at < $1
                  AND closed_at IS NULL
                """,
                cutoff,
            )
            
            # Parse result (e.g., "UPDATE 5")
            count = int(result.split()[-1]) if result else 0
            
            self.logger.info(f"Auto-closed {count} resolved tickets")
            
            return count
            
        except Exception as e:
            self.logger.error(f"Auto-close failed: {e}", exc_info=True)
            return 0
    
    async def check_sla_breaches(self) -> List[str]:
        """
        Check for SLA breaches and mark tickets.
        
        Returns:
            List of ticket IDs that breached SLA
        """
        try:
            # Find tickets with breached first response SLA
            breached = await self.db.fetch(
                """
                UPDATE tickets
                SET sla_breached = TRUE,
                    updated_at = CURRENT_TIMESTAMP
                WHERE first_response_due_at < CURRENT_TIMESTAMP
                  AND first_response_at IS NULL
                  AND sla_breached = FALSE
                  AND status NOT IN ('closed', 'resolved')
                RETURNING id, ticket_number
                """,
            )
            
            ticket_ids = [t["id"] for t in breached]
            
            if ticket_ids:
                self.logger.warning(
                    f"SLA breach detected for {len(ticket_ids)} tickets: "
                    f"{[t['ticket_number'] for t in breached]}"
                )
                
                # Publish events
                if self.producer:
                    for ticket in breached:
                        await self.producer.send_event(
                            event_type="sla_breached",
                            event_data={
                                "ticket_id": str(ticket["id"]),
                                "ticket_number": ticket["ticket_number"],
                                "breach_type": "first_response",
                            },
                        )
            
            return ticket_ids
            
        except Exception as e:
            self.logger.error(f"SLA breach check failed: {e}", exc_info=True)
            return []


# Import json for metadata handling
import json

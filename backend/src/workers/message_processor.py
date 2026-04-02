"""
Message Processor - Core Processing Logic

Handles the complete message processing pipeline:
1. Identify/create customer
2. Create ticket with ticket_number
3. Run AI agent (mock if needed)
4. Analyze sentiment
5. Check escalation rules
6. Save results

Usage:
    from src.workers.message_processor import MessageProcessor
    processor = MessageProcessor(db_connection)
    await processor.process(message)
"""

import logging
import json
import random
from typing import Optional, Dict, Any
from datetime import datetime, timezone

import asyncpg

logger = logging.getLogger(__name__)


class MessageProcessor:
    """
    Core message processor for the async pipeline.
    
    Processes messages through the full pipeline:
    - Customer identification/creation
    - Ticket creation
    - AI response generation
    - Sentiment analysis
    - Escalation detection
    """

    def __init__(self, db: asyncpg.Connection):
        self.db = db

    async def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a message through the complete pipeline.
        
        Args:
            message: Message record from message_queue
            
        Returns:
            Dict with processing results
        """
        request_id = message["request_id"]
        customer_email = message["customer_email"]
        subject = message["subject"]
        message_text = message["message"]
        channel = message["channel"]

        logger.info(f"📝 Processing started: {request_id}")

        # ===== STEP 1: Identify or Create Customer =====
        logger.info(f"Step 1/6: Identifying customer: {customer_email}")
        customer = await self._get_or_create_customer(customer_email, channel)
        customer_id = customer["id"]
        logger.info(f"✓ Customer identified: {customer_id}")

        # ===== STEP 2: Create Ticket =====
        logger.info(f"Step 2/6: Creating ticket")
        ticket = await self._create_ticket(customer_id, subject, message_text, channel)
        ticket_id = ticket["id"]
        ticket_number = ticket["ticket_number"]
        logger.info(f"✓ Ticket created: {ticket_number}")

        # ===== STEP 3: Run AI Agent =====
        logger.info(f"Step 3/6: Running AI agent")
        ai_response = await self._run_ai_agent(message_text, subject, ticket_number)
        logger.info(f"✓ AI response generated: {len(ai_response)} chars")

        # ===== STEP 4: Analyze Sentiment =====
        logger.info(f"Step 4/6: Analyzing sentiment")
        sentiment = await self._analyze_sentiment(message_text)
        logger.info(f"✓ Sentiment analyzed: {sentiment['label']} (score: {sentiment['score']})")

        # ===== STEP 5: Check Escalation =====
        logger.info(f"Step 5/6: Checking escalation")
        escalation = await self._check_escalation(message_text, sentiment)
        logger.info(f"✓ Escalation check: {'ESCALATED' if escalation['escalated'] else 'OK'}")

        # ===== STEP 6: Save Results =====
        logger.info(f"Step 6/6: Saving results")
        result = await self._save_results(
            ticket_id=ticket_id,
            customer_id=customer_id,
            channel=channel,
            ai_response=ai_response,
            sentiment=sentiment,
            escalation=escalation,
        )
        logger.info(f"✓ Results saved: conversation={result['conversation_id']}")

        logger.info(f"✅ Processing completed: {request_id}")

        return {
            "ticket_id": str(ticket_id),
            "ticket_number": ticket_number,
            "customer_id": str(customer_id),
            "conversation_id": str(result["conversation_id"]),
            "response": ai_response,
            "sentiment": sentiment["label"],
            "sentiment_score": sentiment["score"],
            "escalated": escalation["escalated"],
            "escalation_reason": escalation.get("reason"),
        }

    async def _get_or_create_customer(
        self,
        email: str,
        channel: str,
    ) -> Dict[str, Any]:
        """Identify or create customer record."""
        customer = await self.db.fetchrow(
            "SELECT * FROM customers WHERE email = $1",
            email,
        )

        if not customer:
            logger.info(f"Creating new customer: {email}")
            customer = await self.db.fetchrow(
                """
                INSERT INTO customers (
                    email, full_name, preferred_channel,
                    customer_tier, is_active
                )
                VALUES ($1, $2, $3, $4, TRUE)
                RETURNING *
                """,
                email,
                email.split("@")[0],
                channel,
                "standard",
            )

        return dict(customer)

    async def _create_ticket(
        self,
        customer_id: str,
        subject: str,
        description: str,
        channel: str,
    ) -> Dict[str, Any]:
        """Create ticket with auto-generated ticket_number."""
        # Generate unique ticket number
        ticket_number = await self._generate_ticket_number()
        logger.info(f"   Generating ticket number: {ticket_number}")

        ticket = await self.db.fetchrow(
            """
            INSERT INTO tickets (
                customer_id, subject, description, channel,
                priority, status, sla_tier, ticket_number,
                first_response_due_at, resolution_due_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8,
                    NOW() + INTERVAL '24 HOURS',
                    NOW() + INTERVAL '72 HOURS')
            RETURNING *
            """,
            customer_id,
            subject,
            description,
            channel,
            "medium",
            "new",
            "standard",
            ticket_number,
        )
        logger.info(f"   ✓ Ticket created with ticket_number: {ticket_number}")
        return dict(ticket)

    async def _generate_ticket_number(self) -> str:
        """
        Generate a unique ticket number.
        
        Format: CS-<YEAR>-<RANDOM_5_DIGIT>
        Example: CS-2026-48392
        
        Returns:
            str: Unique ticket number
        """
        year = datetime.now().year
        random_digits = random.randint(10000, 99999)
        ticket_number = f"CS-{year}-{random_digits}"
        
        # Ensure uniqueness by checking database
        existing = await self.db.fetchval(
            "SELECT 1 FROM tickets WHERE ticket_number = $1",
            ticket_number,
        )
        
        # If collision (extremely rare), generate new one
        if existing:
            return await self._generate_ticket_number()
        
        return ticket_number

    async def _run_ai_agent(
        self,
        message: str,
        subject: str,
        ticket_number: str,
    ) -> str:
        """
        Generate AI response (mock implementation).
        
        In production, this would call OpenAI API.
        """
        responses = [
            f"Thank you for contacting us about '{subject}'. Your ticket number is {ticket_number}. "
            f"We have received your message: \"{message[:100]}...\" "
            f"Our team will review your request and get back to you within 24 hours. "
            f"Is there anything else we can help you with?",

            f"Hello! We've received your inquiry regarding '{subject}' (Ticket: {ticket_number}). "
            f"Thank you for reaching out. We understand you mentioned: \"{message[:100]}...\" "
            f"We're looking into this and will provide a detailed response shortly. "
            f"Your satisfaction is our priority!",

            f"Thanks for contacting Customer Success! Ticket {ticket_number} has been created for: '{subject}'. "
            f"We've noted your concern: \"{message[:100]}...\" "
            f"Our specialists are reviewing your case. Expected response time: 24 hours. "
            f"We appreciate your patience!",
        ]

        idx = len(message) % len(responses)
        return responses[idx]

    async def _analyze_sentiment(self, message: str) -> Dict[str, Any]:
        """
        Analyze message sentiment (keyword-based mock).
        
        In production, this would use OpenAI or ML model.
        """
        message_lower = message.lower()

        negative_keywords = [
            "angry", "terrible", "awful", "hate", "worst",
            "disappointed", "frustrated", "unhappy", "bad",
            "useless", "waste", "refund", "cancel", "complaint",
        ]

        positive_keywords = [
            "thank", "great", "excellent", "awesome", "love",
            "happy", "pleased", "satisfied", "wonderful", "good",
        ]

        negative_count = sum(1 for word in negative_keywords if word in message_lower)
        positive_count = sum(1 for word in positive_keywords if word in message_lower)

        total = positive_count + negative_count

        if total == 0:
            score = 0.0
            label = "neutral"
        else:
            score = (positive_count - negative_count) / max(total, 1)
            if score > 0.3:
                label = "positive"
            elif score < -0.3:
                label = "negative"
            else:
                label = "neutral"

        return {
            "label": label,
            "score": round(score, 3),
            "confidence": min(1.0, total / 5.0),
        }

    async def _check_escalation(
        self,
        message: str,
        sentiment: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Check if message requires escalation.
        
        Triggers:
        - Negative sentiment (score < -0.5)
        - Escalation keywords
        - Legal/refund threats
        """
        message_lower = message.lower()

        if sentiment["score"] < -0.5:
            return {
                "escalated": True,
                "reason": "negative_sentiment",
            }

        escalation_keywords = [
            "escalate", "manager", "supervisor", "complaint",
            "lawsuit", "legal", "sue", "attorney",
            "cancel subscription", "unsubscrib", "refund immediately",
        ]

        for keyword in escalation_keywords:
            if keyword in message_lower:
                return {
                    "escalated": True,
                    "reason": "customer_request",
                }

        return {
            "escalated": False,
            "reason": None,
        }

    async def _save_results(
        self,
        ticket_id: str,
        customer_id: str,
        channel: str,
        ai_response: str,
        sentiment: Dict[str, Any],
        escalation: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Save conversation, messages, and update ticket."""
        # Create conversation
        conversation = await self.db.fetchrow(
            """
            INSERT INTO conversations (
                ticket_id, customer_id, channel,
                message_count, overall_sentiment, sentiment_score,
                status
            )
            VALUES ($1, $2, $3, 1, $4, $5, 'active')
            RETURNING *
            """,
            ticket_id,
            customer_id,
            channel,
            sentiment["label"],
            sentiment["score"],
        )
        conversation_id = conversation["id"]

        # Save inbound message
        await self.db.execute(
            """
            INSERT INTO messages (
                ticket_id, conversation_id, customer_id,
                content, direction, channel,
                sentiment, sentiment_score
            )
            VALUES ($1, $2, $3, $4, 'inbound', $5, $6, $7)
            """,
            ticket_id,
            conversation_id,
            customer_id,
            ai_response[:500],
            channel,
            sentiment["label"],
            sentiment["score"],
        )

        # Save outbound response
        await self.db.execute(
            """
            INSERT INTO messages (
                ticket_id, conversation_id, customer_id,
                content, direction, channel,
                ai_model_used
            )
            VALUES ($1, $2, $3, $4, 'outbound', $5, $6)
            """,
            ticket_id,
            conversation_id,
            customer_id,
            ai_response,
            channel,
            "mock-ai",
        )

        # Update ticket status
        await self.db.execute(
            """
            UPDATE tickets
            SET status = 'resolved',
                resolution_summary = $1,
                resolved_at = CURRENT_TIMESTAMP
            WHERE id = $2
            """,
            ai_response[:500],
            ticket_id,
        )

        return {"conversation_id": conversation_id}

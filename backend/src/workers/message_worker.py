"""
Message Worker - Background Processor

Continuously polls message_queue table and processes pending messages.

Flow:
1. Poll message_queue WHERE status = 'pending'
2. Update status to 'processing'
3. Process message (customer, ticket, AI, sentiment, escalation)
4. Update status to 'completed' with results

Usage:
    uv run python -m src.workers.message_worker
"""

import asyncio
import logging
import json
import os
import random
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import uuid4

import asyncpg
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class MessageWorker:
    """
    Background worker that processes messages from message_queue.
    """

    def __init__(self, poll_interval: float = 2.0):
        self.poll_interval = poll_interval
        self.running = False
        self.processed_count = 0
        self.error_count = 0
        self.db: Optional[asyncpg.Connection] = None
        self.last_poll: Optional[datetime] = None

    async def start(self):
        """Start the worker."""
        logger.info("=" * 60)
        logger.info("Starting Message Worker")
        logger.info("=" * 60)

        # Connect to database
        db_url = os.getenv("APP_DATABASE_URL")
        if not db_url:
            raise RuntimeError("APP_DATABASE_URL not configured")

        asyncpg_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
        # Disable statement cache to prevent cached plan errors after migrations
        self.db = await asyncpg.connect(asyncpg_url, statement_cache_size=0)
        logger.info("✓ Database connected (statement cache disabled)")
        
        self.running = True
        logger.info("✓ Worker started - polling for messages")
        logger.info("=" * 60)

    async def stop(self):
        """Stop the worker gracefully."""
        logger.info("Stopping worker...")
        self.running = False
        
        if self.db:
            await self.db.close()
            logger.info("✓ Database connection closed")
        
        logger.info(f"Worker stopped. Processed: {self.processed_count}, Errors: {self.error_count}")

    async def run(self):
        """Main worker loop - poll and process messages."""
        while self.running:
            try:
                await self.poll_and_process()
                self.last_poll = datetime.now(timezone.utc)
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                logger.info("Worker cancelled")
                break
            except Exception as e:
                error_msg = str(e)
                
                # Check for cached statement error - need to reconnect
                if "cached statement plan is invalid" in error_msg:
                    logger.warning("Cached statement invalid - reconnecting to database...")
                    try:
                        await self.db.close()
                        db_url = os.getenv("APP_DATABASE_URL")
                        asyncpg_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
                        # Reconnect with statement cache disabled
                        self.db = await asyncpg.connect(asyncpg_url, statement_cache_size=0)
                        logger.info("✓ Database reconnected (statement cache disabled)")
                    except Exception as reconnect_error:
                        logger.error(f"Reconnection failed: {reconnect_error}", exc_info=True)
                
                logger.error(f"Poll error: {e}", exc_info=True)
                self.error_count += 1
                await asyncio.sleep(self.poll_interval)

    async def poll_and_process(self):
        """Poll for pending messages and process them with retry logic and DLQ."""

        # Get one pending message (with lock to prevent duplicates)
        # Also fetch retry_count to implement retry logic
        message = await self.db.fetchrow("""
            UPDATE message_queue
            SET status = 'processing',
                last_retry_at = CURRENT_TIMESTAMP
            WHERE id = (
                SELECT id FROM message_queue
                WHERE status IN ('pending', 'retry')
                AND (retry_count IS NULL OR retry_count < 3)
                ORDER BY created_at ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            RETURNING *
        """)

        if not message:
            # No pending messages
            return

        request_id = message["request_id"]
        retry_count = message.get("retry_count", 0) or 0

        logger.info("=" * 50)
        logger.info(f"📨 Picked message: {request_id}")
        if retry_count > 0:
            logger.info(f"🔄 Retry attempt: {retry_count}/3")
        logger.info(f"📝 Processing started: {request_id}")
        logger.info(f"   Email: {message['customer_email']}")
        logger.info(f"   Subject: {message['subject']}")
        logger.info("=" * 50)

        try:
            # Process the message
            await self.process_message(message)

            logger.info("=" * 50)
            logger.info(f"✅ Processing completed: {request_id}")
            logger.info("=" * 50)
            self.processed_count += 1

        except Exception as e:
            logger.error(f"❌ Processing failed: {request_id} - {e}", exc_info=True)
            self.error_count += 1
            error_msg = str(e)
            import traceback
            error_stack = traceback.format_exc()

            # Check if we should retry
            new_retry_count = retry_count + 1
            max_retries = 3

            if new_retry_count < max_retries:
                # Retry with exponential backoff
                backoff_seconds = (2 ** retry_count) * 5  # 5s, 10s, 20s
                logger.warning(f"⚠️ Scheduling retry {new_retry_count}/{max_retries} in {backoff_seconds}s: {request_id}")

                await self.db.execute("""
                    UPDATE message_queue
                    SET status = 'pending',
                        retry_count = $1,
                        last_retry_at = CURRENT_TIMESTAMP,
                        error_message = $2
                    WHERE request_id = $3
                """, new_retry_count, f"Retry {new_retry_count}/{max_retries}: {error_msg}", request_id)

                logger.info(f"⚠️ Message will be retried in {backoff_seconds} seconds: {request_id}")
            else:
                # Max retries exceeded - move to Dead Letter Queue
                logger.error(f"🚫 Max retries ({max_retries}) exceeded: {request_id}")
                logger.info(f"📦 Moving message to Dead Letter Queue: {request_id}")

                await self._move_to_dlq(message, error_msg, error_stack)

                logger.info(f"✅ Message moved to DLQ: {request_id}")

    async def _move_to_dlq(self, message: dict, error_message: str, error_stack: str):
        """Move failed message to Dead Letter Queue."""
        request_id = message["request_id"]
        retry_count = message.get("retry_count", 0) or 0
        
        try:
            # Insert into DLQ
            await self.db.execute("""
                INSERT INTO dead_letter_queue (
                    original_request_id,
                    original_trace_id,
                    customer_email,
                    subject,
                    message,
                    channel,
                    failure_reason,
                    error_message,
                    error_stack_trace,
                    retry_count,
                    max_retries,
                    first_attempt_at,
                    last_attempt_at,
                    last_error_at,
                    dlq_status,
                    original_metadata
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11,
                    $12, $13, CURRENT_TIMESTAMP, 'new', $14
                )
            """,
                request_id,
                message.get("trace_id"),
                message["customer_email"],
                message["subject"],
                message["message"],
                message.get("channel", "web_form"),
                f"Max retries exceeded after {retry_count + 1} attempts",
                error_message,
                error_stack,
                retry_count + 1,
                3,
                message.get("created_at"),
                message.get("last_retry_at") or message.get("created_at"),
                message.get("metadata", "{}"),
            )

            # Update original message_queue status
            await self.db.execute("""
                UPDATE message_queue
                SET status = 'failed',
                    retry_count = $1,
                    error_message = $2,
                    completed_at = CURRENT_TIMESTAMP
                WHERE request_id = $3
            """, retry_count + 1, f"Moved to DLQ: {error_message}", request_id)

            logger.info(f"✓ DLQ record created for: {request_id}")

        except Exception as e:
            logger.error(f"❌ Failed to move to DLQ: {request_id} - {e}", exc_info=True)
            # Still mark as failed even if DLQ insert fails
            await self.db.execute("""
                UPDATE message_queue
                SET status = 'failed',
                    retry_count = $1,
                    error_message = $2,
                    completed_at = CURRENT_TIMESTAMP
                WHERE request_id = $3
            """, retry_count + 1, f"DLQ insert failed: {error_message}", request_id)

    async def process_message(self, message: Dict[str, Any]):
        """
        Process a single message through the full pipeline.

        Pipeline:
        1. Identify/create customer
        2. Create ticket
        3. Run AI agent
        4. Analyze sentiment
        5. Check escalation
        6. Save results
        7. Send response via channel
        """
        request_id = message["request_id"]
        customer_email = message.get("customer_email")
        
        # Extract customer_phone from message or metadata
        customer_phone = message.get("customer_phone")
        if not customer_phone:
            metadata = message.get("metadata", {})
            if isinstance(metadata, str):
                import json
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}
            customer_phone = metadata.get("customer_phone")
        
        subject = message["subject"]
        message_text = message["message"]
        channel = message["channel"]

        # ===== STEP 1: Identify or Create Customer =====
        logger.info(f"👤 Step 1/6: Identifying customer")

        customer = None
        
        # Try to find by email first
        if customer_email:
            customer = await self.db.fetchrow("""
                SELECT * FROM customers
                WHERE email = $1
            """, customer_email)

        # Try to find by phone (for WhatsApp)
        if not customer and customer_phone:
            customer = await self.db.fetchrow("""
                SELECT * FROM customers
                WHERE phone = $1
            """, customer_phone)

        # Create new customer if not found
        if not customer:
            logger.info(f"   Creating new customer")
            customer = await self.db.fetchrow("""
                INSERT INTO customers (
                    email, phone, full_name, preferred_channel,
                    customer_tier, is_active
                )
                VALUES ($1, $2, $3, $4, 'standard', TRUE)
                RETURNING *
            """,
                customer_email,
                customer_phone,
                customer_email.split("@")[0] if customer_email else customer_phone,
                channel
            )
        else:
            # Update customer phone if it's missing and we have it
            if not customer.get('phone') and customer_phone:
                logger.info(f"   Updating customer phone number")
                await self.db.execute("""
                    UPDATE customers SET phone = $1 WHERE id = $2
                """, customer_phone, customer['id'])
                customer = await self.db.fetchrow("""
                    SELECT * FROM customers WHERE id = $1
                """, customer['id'])

        customer_id = customer["id"]
        logger.info(f"   ✓ Customer identified: {customer_id} (email={customer.get('email')}, phone={customer.get('phone')})")

        # ===== STEP 2: Create Ticket =====
        logger.info(f"🎫 Step 2/6: Creating ticket")

        try:
            # Generate unique ticket number
            ticket_number = await self._generate_ticket_number()
            logger.info(f"   Generating ticket number: {ticket_number}")

            ticket = await self.db.fetchrow("""
                INSERT INTO tickets (
                    customer_id, subject, description, channel,
                    priority, status, sla_tier, ticket_number,
                    first_response_due_at, resolution_due_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8,
                        NOW() + INTERVAL '24 HOURS',
                        NOW() + INTERVAL '72 HOURS')
                RETURNING *
            """, customer_id, subject, message_text, channel, "medium", "new", "standard", ticket_number)

            ticket_id = ticket["id"]
            ticket_number = ticket["ticket_number"]
            logger.info(f"   ✓ Ticket created with ticket_number: {ticket_number}")
        except Exception as e:
            logger.error(f"   ✗ Ticket creation failed: {e}", exc_info=True)
            raise Exception(f"Failed to create ticket: {e}")

        # ===== STEP 3: Run AI Agent (Mock Response) =====
        logger.info(f"🤖 Step 3/6: Running AI agent")

        ai_response = await self.run_ai_agent(message_text, subject, ticket_number)
        logger.info(f"   ✓ AI response generated: {len(ai_response)} chars")

        # ===== STEP 4: Analyze Sentiment =====
        logger.info(f"📊 Step 4/6: Analyzing sentiment")
        
        sentiment = await self.analyze_sentiment(message_text)
        logger.info(f"✓ Sentiment analyzed: {sentiment['label']} (score: {sentiment['score']})")
        
        # ===== STEP 5: Check Escalation =====
        logger.info(f"⚠️ Step 5/6: Checking escalation")

        escalation = await self.check_escalation(message_text, sentiment)
        escalation_status = 'ESCALATED' if escalation['escalated'] else 'OK'
        logger.info(f"   ✓ Escalation check: {escalation_status}")
        if escalation['escalated']:
            logger.warning(f"   ⚠️ Escalation reason: {escalation.get('reason')}")

        # ===== STEP 6: Save Results =====
        logger.info(f"💾 Step 6/6: Saving results")
        
        # Create conversation
        conversation = await self.db.fetchrow("""
            INSERT INTO conversations (
                ticket_id, customer_id, channel,
                message_count, overall_sentiment, sentiment_score,
                status
            )
            VALUES ($1, $2, $3, 1, $4, $5, 'active')
            RETURNING *
        """, ticket_id, customer_id, channel, sentiment["label"], sentiment["score"])
        
        conversation_id = conversation["id"]
        
        # Save inbound message
        await self.db.execute("""
            INSERT INTO messages (
                ticket_id, conversation_id, customer_id,
                content, direction, channel,
                sentiment, sentiment_score
            )
            VALUES ($1, $2, $3, $4, 'inbound', $5, $6, $7)
        """, ticket_id, conversation_id, customer_id, message_text, channel, 
            sentiment["label"], sentiment["score"])
        
        # Save outbound response
        await self.db.execute("""
            INSERT INTO messages (
                ticket_id, conversation_id, customer_id,
                content, direction, channel,
                ai_model_used
            )
            VALUES ($1, $2, $3, $4, 'outbound', $5, $6)
        """, ticket_id, conversation_id, customer_id, ai_response, channel, "mock-ai")

        # ===== STEP 7: Send Response via Channel =====
        logger.info(f"📤 Step 7/7: Sending response via {channel}")

        try:
            if channel == "gmail":
                await self._send_gmail_response(customer_email, subject, ai_response, ticket_number)
            elif channel == "whatsapp":
                await self._send_whatsapp_response(customer, ai_response)
            else:  # web_form
                await self._send_web_form_response(customer_email, subject, ai_response)
            
            logger.info(f"   ✓ Response sent successfully via {channel}")
        except Exception as e:
            logger.error(f"   ✗ Failed to send response via {channel}: {e}", exc_info=True)
            # Don't fail the ticket - response delivery failure is non-fatal
            # Ticket is still resolved, just couldn't deliver response

        # Update ticket status
        await self.db.execute("""
            UPDATE tickets
            SET status = 'resolved',
                resolution_summary = $1,
                resolved_at = CURRENT_TIMESTAMP
            WHERE id = $2
        """, ai_response[:500], ticket_id)
        
        # Update message_queue with results
        await self.db.execute("""
            UPDATE message_queue
            SET status = 'completed',
                ticket_id = $1,
                response = $2,
                sentiment = $3,
                is_escalated = $4,
                escalation_reason = $5,
                metadata = metadata || $6::jsonb,
                completed_at = CURRENT_TIMESTAMP
            WHERE request_id = $7
        """, ticket_id, ai_response, sentiment["label"], escalation["escalated"],
            escalation.get("reason"), json.dumps({
                "sentiment_score": sentiment["score"],
                "conversation_id": str(conversation_id),
            }), request_id)

        logger.info(f"✓ Results saved: ticket={ticket_number}, conversation={conversation_id}")

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

    async def run_ai_agent(self, message: str, subject: str, ticket_number: str) -> str:
        """
        Generate AI response (mock implementation).
        
        In production, this would call OpenAI API.
        """
        # Simple template-based response
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
        
        # Select response based on message length (simple mock logic)
        idx = len(message) % len(responses)
        return responses[idx]

    async def analyze_sentiment(self, message: str) -> Dict[str, Any]:
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

    async def check_escalation(
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
        
        # Check sentiment threshold
        if sentiment["score"] < -0.5:
            return {
                "escalated": True,
                "reason": "negative_sentiment",
            }
        
        # Check escalation keywords
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

    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics."""
        return {
            "running": self.running,
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "last_poll": self.last_poll.isoformat() if self.last_poll else None,
        }

    # ========================================================================
    # Response Delivery Methods
    # ========================================================================

    async def _send_gmail_response(self, to_email: str, subject: str, content: str, ticket_number: str):
        """
        Send response via Gmail API.

        # === MISSING RESPONSE SENDING PART - GMAIL ===
        This method sends the AI response back to the customer via Gmail API.

        Args:
            to_email: Customer email address
            subject: Original subject
            content: AI response content
            ticket_number: Ticket number for reference
        """
        try:
            from src.channels.gmail_handler import GmailResponseSender
            import os
            import pickle

            # Check if Gmail credentials are configured
            gmail_client_id = os.getenv("APP_GMAIL_CLIENT_ID")
            gmail_client_secret = os.getenv("APP_GMAIL_CLIENT_SECRET")
            gmail_refresh_token = os.getenv("APP_GMAIL_REFRESH_TOKEN")
            gmail_sender_email = os.getenv("APP_GMAIL_SENDER_EMAIL")

            # Try to load refresh token from token.json if not in .env
            if not gmail_refresh_token:
                token_path = os.path.join(os.path.dirname(__file__), '..', '..', 'token.json')
                if os.path.exists(token_path):
                    try:
                        with open(token_path, 'rb') as f:
                            creds = pickle.load(f)
                        gmail_refresh_token = creds.refresh_token
                        logger.info("✓ Loaded refresh token from token.json")
                    except Exception as e:
                        logger.warning(f"Failed to load token.json: {e}")

            if not all([gmail_client_id, gmail_client_secret, gmail_refresh_token, gmail_sender_email]):
                logger.warning("⚠️ Gmail credentials not configured, skipping email delivery")
                logger.warning("⚠️ Add Gmail credentials to .env file to enable email responses")
                return

            # Initialize Gmail sender
            sender = GmailResponseSender(
                client_id=gmail_client_id,
                client_secret=gmail_client_secret,
                refresh_token=gmail_refresh_token,
                sender_email=gmail_sender_email,
            )

            # Format email with proper greeting and signature
            email_content = f"""Dear Customer,

Thank you for contacting TechCorp Support.

{content}

If you have any further questions, please don't hesitate to reply to this email.

Best regards,
TechCorp AI Support Team
---
Ticket Reference: {ticket_number}
"""

            logger.info(f"   📧 Sending Gmail response to {to_email}...")
            
            # Send email
            result = await sender.send_reply(
                to_email=to_email,
                subject=f"Re: {subject} (Ticket: {ticket_number})",
                content=email_content,
            )

            if result.get("success"):
                logger.info(f"   ✅ Gmail response sent successfully to {to_email}")
                logger.info(f"   📧 Message ID: {result.get('message_id')}")
            else:
                logger.error(f"   ❌ Gmail send failed: {result.get('error')}")

        except Exception as e:
            logger.error(f"   ❌ Failed to send Gmail response: {e}", exc_info=True)
            # Don't raise - allow processing to continue

    async def _send_whatsapp_response(self, customer: dict, content: str):
        """
        Send response via WhatsApp/Twilio API.
        
        # === MISSING RESPONSE SENDING PART - WHATSAPP ===
        This method sends the AI response back to the customer via Twilio WhatsApp API.

        Args:
            customer: Customer dict with phone number
            content: AI response content
        """
        try:
            from src.channels.whatsapp_handler import WhatsAppHandler, WhatsAppResponseSender
            import os

            # Check if Twilio credentials are configured
            twilio_sid = os.getenv("APP_TWILIO_ACCOUNT_SID")
            twilio_token = os.getenv("APP_TWILIO_AUTH_TOKEN")
            twilio_number = os.getenv("APP_TWILIO_WHATSAPP_NUMBER")

            if not all([twilio_sid, twilio_token, twilio_number]):
                logger.warning("⚠️ Twilio credentials not configured, skipping WhatsApp delivery")
                logger.warning("⚠️ Add Twilio credentials to .env file to enable WhatsApp responses")
                return

            # Get customer phone from customer record
            customer_phone = customer.get("phone")
            if not customer_phone:
                logger.warning("⚠️ Customer phone number not found, cannot send WhatsApp")
                return

            # Initialize WhatsApp sender
            sender = WhatsAppResponseSender(
                account_sid=twilio_sid,
                auth_token=twilio_token,
                from_number=twilio_number,
            )

            # Format for WhatsApp (short, conversational)
            whatsapp_content = f"Hi! Thanks for contacting TechCorp Support. 🙏\n\n{content}\n\nReply for more help or type 'human' for live support."

            logger.info(f"   📱 Sending WhatsApp response to {customer_phone}...")
            
            # Use handler to split long messages (correct method)
            handler = WhatsAppHandler()
            messages = handler.format_reply_for_whatsapp(whatsapp_content)

            # Send each message
            for msg in messages:
                result = await sender.send_message(customer_phone, msg)
                delivery_status = result.get('delivery_status', 'unknown')
                logger.info(f"   ✅ WhatsApp response sent to {customer_phone}: {delivery_status}")

        except Exception as e:
            logger.error(f"   ❌ Failed to send WhatsApp response: {e}", exc_info=True)
            # Don't raise - allow processing to continue

    async def _send_web_form_response(self, to_email: str, subject: str, content: str):
        """
        Send response for web form submission via email notification.
        
        Args:
            to_email: Customer email address
            subject: Original subject
            content: AI response content
        """
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            import os
            
            # For web form, send email notification
            # This is a simple SMTP implementation
            # In production, use a proper email service
            
            smtp_server = os.getenv("SMTP_SERVER")
            smtp_port = int(os.getenv("SMTP_PORT", 587))
            smtp_user = os.getenv("SMTP_USER")
            smtp_password = os.getenv("SMTP_PASSWORD")
            from_email = os.getenv("FROM_EMAIL", "support@techcorp.com")
            
            if not smtp_server:
                logger.info(f"Web form response generated (email notification skipped - SMTP not configured)")
                logger.info(f"Response would be sent to: {to_email}")
                logger.info(f"Content: {content[:200]}...")
                return
            
            # Create email
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Subject'] = f"Re: {subject}"
            
            email_body = f"""Hello,

Thank you for contacting TechCorp Support.

{content}

If you have any further questions, please reply to this email or submit a new ticket through our website.

Best regards,
TechCorp Support Team
"""
            
            msg.attach(MIMEText(email_body, 'plain'))
            
            # Send via SMTP
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                if smtp_user and smtp_password:
                    server.login(smtp_user, smtp_password)
                server.send_message(msg)
            
            logger.info(f"✓ Web form response email sent to {to_email}")
            
        except Exception as e:
            logger.error(f"Failed to send web form response email: {e}", exc_info=True)
            # Non-fatal - web form response is stored in DB


# ============================================================================
# Global Worker Instance
# ============================================================================

_worker: Optional[MessageWorker] = None


def get_worker() -> MessageWorker:
    """Get or create global worker instance."""
    global _worker
    if _worker is None:
        _worker = MessageWorker()
    return _worker


async def start_worker():
    """Start the global worker."""
    worker = get_worker()
    await worker.start()
    return worker


async def stop_worker():
    """Stop the global worker."""
    worker = get_worker()
    await worker.stop()


async def run_worker():
    """Run the worker (blocking)."""
    worker = get_worker()
    await worker.run()


def get_worker_stats() -> Dict[str, Any]:
    """Get worker statistics."""
    worker = get_worker()
    return worker.get_stats()

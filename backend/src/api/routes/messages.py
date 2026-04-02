"""
Messages API Routes - Async Kafka Integration with GUARANTEED Persistence

CRITICAL: Message MUST be stored in database before returning success.

Platinum Features:
- API Key Authentication
- Rate Limiting
- Retry Mechanism
- Dead Letter Queue
"""

import logging
import asyncpg
import json
import os
import time
from typing import Optional
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Request
from dotenv import load_dotenv

from src.security import authenticate_request, check_rate_limit_middleware, APIKeyInfo, optional_auth
from src.security import record_request_metrics

load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_db():
    """
    Get direct asyncpg connection with cleanup.
    Uses PRIMARY database (Neon) - NOT fallback.

    Note: Creates a new connection for each request and clears
    statement cache to avoid cached plan issues after schema changes.
    """
    db_url = os.getenv("APP_DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not configured in environment")
        raise HTTPException(status_code=500, detail="Database not configured")

    # Convert to asyncpg format
    asyncpg_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    logger.info(f"Connecting to database: {asyncpg_url[:60]}...")

    conn = None
    try:
        # Connect with statement cache disabled to prevent cached plan errors
        conn = await asyncpg.connect(
            asyncpg_url,
            statement_cache_size=0,  # Disable statement caching
        )
        logger.info("Database connection established (statement cache disabled)")
        yield conn
        logger.info("Database connection closing")
    except asyncpg.exceptions.InvalidCachedStatementError as e:
        logger.warning(f"Cached statement error - reconnecting: {e}")
        # Connection is tainted, don't use it
        raise HTTPException(status_code=503, detail="Database statement cache invalid - please retry")
    except Exception as e:
        logger.error(f"Database connection failed: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")
    finally:
        if conn:
            try:
                await conn.close()
                logger.info("Database connection closed")
            except Exception:
                pass


@router.post(
    "/submit",
    response_model=dict,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit Inbound Message",
)
async def submit_message(
    message_data: dict,
    request: Request,
    auth: APIKeyInfo = Depends(authenticate_request),
    db: asyncpg.Connection = Depends(get_db),
):
    """
    Submit an inbound message for asynchronous processing.

    Supports multiple channels:
    - web_form (default): Web form submissions
    - whatsapp: WhatsApp messages (via Twilio)
    - gmail: Email messages

    Requires API Key authentication via X-API-Key header.
    Rate limited based on API key tier.

    CRITICAL FLOW:
    1. Validate input (fail fast)
    2. Store in message_queue WITH COMMIT (REQUIRED)
    3. Publish to Kafka (best effort - doesn't block)
    4. Return 202 ONLY if DB insert succeeded

    Worker will process asynchronously.
    """
    start_time = time.time()
    request_id = str(uuid4())
    trace_id = str(uuid4())

    logger.info(
        f"📨 Message received: {request_id}",
        extra={
            "request_id": request_id,
            "trace_id": trace_id,
            "stage": "intake",
            "api_key": auth.name if auth else "anonymous",
            "api_key_tier": auth.tier if auth else "none",
        }
    )

    # ===== STEP 1: VALIDATE INPUT (FAIL FAST) =====
    # Support both email (web/gmail) and phone (whatsapp)
    customer_email = message_data.get("customer_email", "").strip()
    customer_phone = message_data.get("customer_phone", "").strip()
    message = message_data.get("message", "").strip()
    subject = message_data.get("subject", "No Subject").strip() or "No Subject"
    channel = message_data.get("channel", "web_form")

    # Validate customer identification (email OR phone required)
    if not customer_email and not customer_phone:
        logger.warning(f"No customer identification provided")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="customer_email or customer_phone is required",
        )

    # For WhatsApp: if no email provided, generate one from phone
    if channel == "whatsapp" and not customer_email and customer_phone:
        # Generate a placeholder email from phone number
        # This is needed because current DB schema requires customer_email
        clean_phone = customer_phone.replace("+", "").replace("-", "").replace(" ", "")
        customer_email = f"whatsapp_{clean_phone}@channel.internal"
        logger.info(f"Generated placeholder email for WhatsApp: {customer_email}")

    # Validate email format if provided
    if customer_email and ("@" not in customer_email or "." not in customer_email.split("@")[-1]):
        logger.warning(f"Invalid email: {customer_email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid customer_email is required",
        )

    if not message or len(message) == 0:
        logger.warning(f"Empty message for email: {customer_email or customer_phone}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty",
        )

    # Validate channel
    valid_channels = ["web_form", "whatsapp", "gmail"]
    if channel not in valid_channels:
        logger.warning(f"Invalid channel: {channel}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid channel. Must be one of: {valid_channels}",
        )

    logger.info(
        f"Input validated: email={customer_email or 'N/A'}, "
        f"phone={customer_phone or 'N/A'}, "
        f"subject={subject}, channel={channel}"
    )

    # ===== STEP 2: STORE IN DATABASE (REQUIRED - NO SILENT FAIL) =====
    metadata = {
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "ip_address": None,
        "user_agent": None,
        "customer_phone": customer_phone or None,
        "channel": channel,
    }

    logger.info(f"Inserting message into message_queue: request_id={request_id}")

    try:
        # CRITICAL: This MUST succeed or we return error
        result = await db.execute(
            """
            INSERT INTO message_queue (
                request_id, trace_id, customer_email, subject,
                message, channel, status, metadata
            )
            VALUES ($1, $2, $3, $4, $5, $6, 'pending', $7)
            """,
            request_id,
            trace_id,
            customer_email or None,  # Can be null for WhatsApp
            subject,
            message,
            channel,
            json.dumps(metadata),  # JSON string for JSONB
        )
        
        # Verify insert succeeded
        if not result or result == "":
            logger.error(f"DB execute returned empty result: {result}")
            raise Exception("DB execute returned no confirmation")
        
        logger.info(f"✓ Message queued in database: request_id={request_id}, db_result={result}")
        
        # VERIFY THE INSERT WORKED
        verify = await db.fetchrow(
            "SELECT id, request_id, status FROM message_queue WHERE request_id = $1",
            request_id,
        )
        
        if verify:
            logger.info(f"✓ Insert verified: queue_id={verify['id']}, status={verify['status']}")
        else:
            logger.error(f"CRITICAL: Insert returned success but record not found! request_id={request_id}")
            raise Exception("Insert verification failed - record not found after insert")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"✗ CRITICAL: Failed to store in message_queue: {e}",
            extra={
                "request_id": request_id,
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        # DO NOT return success if DB insert failed!
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue message: {str(e)}",
        )

    # ===== STEP 3: PUBLISH TO KAFKA (BEST EFFORT - DOESN'T BLOCK) =====
    kafka_message = {
        "request_id": request_id,
        "trace_id": trace_id,
        "customer_email": customer_email,
        "customer_phone": customer_phone,
        "subject": subject,
        "message": message,
        "channel": channel,
        "metadata": metadata,
    }

    try:
        from src.kafka import publish_inbound_message

        result = await publish_inbound_message(
            customer_email=customer_email,
            customer_phone=customer_phone,
            subject=subject,
            message=message,
            channel=channel,
            metadata=kafka_message["metadata"],
        )
        logger.info(
            f"✓ Message published to Kafka: {request_id}",
            extra={
                "kafka_message_id": result.get("message_id"),
                "mode": result.get("mode"),
            }
        )
    except Exception as e:
        # Kafka failure is OK - we already stored in DB
        logger.warning(f"Kafka publish failed (DB already saved): {e}")

    # ===== STEP 4: RETURN SUCCESS (ONLY REACHED IF DB INSERT SUCCEEDED) =====
    logger.info(f"✓ Submit complete: {request_id}")
    
    # Record metrics
    duration_ms = (time.time() - start_time) * 1000
    record_request_metrics(duration_ms, success=True)

    return {
        "request_id": request_id,
        "trace_id": trace_id,
        "status": "received",
        "message": "Message received and queued for processing",
        "estimated_response_time": "24 hours",
        "rate_limit": {
            "remaining": getattr(request.state, 'rate_limit_info', {}).get('remaining', 'N/A'),
            "limit": getattr(request.state, 'rate_limit_info', {}).get('limit', 'N/A'),
        } if hasattr(request.state, 'rate_limit_info') else None,
    }


@router.get(
    "/status/{request_id}",
    response_model=dict,
    summary="Get Message Processing Status",
)
async def get_message_status(
    request_id: str,
    db: asyncpg.Connection = Depends(get_db),
):
    """
    Get processing status - NEVER fails.
    
    Returns safe states:
    - pending: Not processed yet
    - processing: Being worked on
    - completed: Done
    - failed: Error occurred
    - not_found: No such request
    """
    try:
        logger.info(f"🔍 Status check: {request_id}")
        
        # First check message_queue
        queue_record = await db.fetchrow(
            """
            SELECT * FROM message_queue
            WHERE request_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            request_id,
        )
        
        if queue_record:
            logger.info(f"✓ Found in queue: {request_id}, status={queue_record['status']}")

            queue_status = queue_record["status"]
            ticket_id = queue_record.get("ticket_id")
            error_msg = queue_record.get("error_message")

            # Map queue status to API status
            status_map = {
                "pending": "pending",
                "processing": "processing",
                "completed": "completed",
                "failed": "failed",
            }

            api_status = status_map.get(queue_status, "pending")

            # If completed, get ticket details
            ticket_number = None
            ticket_status = None
            subject = queue_record["subject"]
            channel = queue_record["channel"]
            customer_email = queue_record["customer_email"]
            
            # Handle metadata - could be JSON string or dict
            metadata = queue_record.get("metadata")
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except (json.JSONDecodeError, TypeError):
                    metadata = {}
            elif metadata is None:
                metadata = {}
            customer_phone = metadata.get("customer_phone")
            
            created_at = queue_record["created_at"]
            response = queue_record.get("response")
            sentiment = queue_record.get("sentiment")
            is_escalated = queue_record.get("is_escalated", False)
            messages = []
            ticket = None  # Initialize ticket variable

            if ticket_id and api_status == "completed":
                try:
                    ticket = await db.fetchrow(
                        """
                        SELECT t.*, c.email as customer_email, c.full_name as customer_name
                        FROM tickets t
                        JOIN customers c ON t.customer_id = c.id
                        WHERE t.id = $1
                        """,
                        ticket_id,
                    )
                    if ticket:
                        ticket_number = ticket["ticket_number"]
                        ticket_status = ticket["status"]
                        # Use ticket's customer_email if queue record doesn't have it
                        if not customer_email and ticket.get("customer_email"):
                            customer_email = ticket["customer_email"]
                        # Use ticket's created_at if queue record doesn't have it
                        if not created_at:
                            created_at = ticket["created_at"]

                        # Get conversation messages
                        conv = await db.fetchrow(
                            """
                            SELECT id FROM conversations
                            WHERE ticket_id = $1
                            LIMIT 1
                            """,
                            ticket_id,
                        )
                        if conv:
                            msg_rows = await db.fetch(
                                """
                                SELECT content, direction, created_at
                                FROM messages
                                WHERE conversation_id = $1
                                ORDER BY created_at ASC
                                LIMIT 5
                                """,
                                conv["id"],
                            )
                            messages = [
                                {
                                    "content": r["content"],
                                    "direction": r["direction"],
                                    "created_at": str(r["created_at"]),
                                }
                                for r in msg_rows
                            ]
                except Exception as e:
                    logger.warning(f"Failed to get ticket details: {e}")

            return {
                "request_id": request_id,
                "trace_id": queue_record["trace_id"],
                "status": api_status,
                "message": _get_status_message(api_status, error_msg),
                "ticket_number": ticket_number,
                "ticket_status": ticket_status,
                "subject": subject,
                "channel": channel,
                "customer_email": customer_email,
                "customer_name": ticket.get("customer_name") if ticket else None,
                "customer_phone": customer_phone,
                "created_at": str(created_at) if created_at else None,
                "response": response,
                "sentiment": sentiment,
                "is_escalated": is_escalated,
                "messages": messages,
                "error": error_msg,
            }
        
        # Not in queue - check if ticket exists with this request_id
        ticket = await db.fetchrow(
            """
            SELECT t.*, c.email as customer_email, c.full_name as customer_name
            FROM tickets t
            JOIN customers c ON t.customer_id = c.id
            WHERE t.metadata->>'request_id' = $1
            ORDER BY t.created_at DESC
            LIMIT 1
            """,
            request_id,
        )

        if ticket:
            logger.info(f"✓ Found in tickets (worker created): {request_id}")

            # Handle metadata - could be JSON string or dict
            ticket_metadata = ticket.get("metadata")
            if isinstance(ticket_metadata, str):
                try:
                    ticket_metadata = json.loads(ticket_metadata)
                except (json.JSONDecodeError, TypeError):
                    ticket_metadata = {}
            elif ticket_metadata is None:
                ticket_metadata = {}

            return {
                "request_id": request_id,
                "trace_id": ticket_metadata.get("trace_id", "unknown"),
                "status": "completed",
                "message": "Processing complete",
                "ticket_number": ticket["ticket_number"],
                "ticket_status": ticket["status"],
                "subject": ticket["subject"],
                "channel": ticket["channel"],
                "customer_email": ticket.get("customer_email"),
                "customer_name": ticket.get("customer_name"),
                "customer_phone": ticket_metadata.get("customer_phone"),
                "created_at": str(ticket["created_at"]) if ticket.get("created_at") else None,
                "messages": [],
                "error": None,
            }
        
        # Not found anywhere
        logger.info(f"✗ Request not found: {request_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "request_id": request_id,
                "status": "not_found",
                "message": "Message not found. It may still be processing.",
            },
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"✗ Status check error: {e}", exc_info=True)
        # Return safe error response instead of crashing
        return {
            "request_id": request_id,
            "trace_id": "unknown",
            "status": "error",
            "message": "Unable to retrieve status at this time",
            "error": str(e),
            "ticket_number": None,
            "ticket_status": None,
            "subject": None,
            "channel": None,
            "customer_email": None,
            "created_at": None,
            "messages": [],
        }


def _get_status_message(status: str, error_msg: Optional[str] = None) -> str:
    """Get human-readable status message."""
    messages = {
        "pending": "Message queued for processing",
        "processing": "Message being processed",
        "completed": "Processing complete",
        "failed": f"Processing failed: {error_msg}" if error_msg else "Processing failed",
    }
    return messages.get(status, "Status unknown")


@router.get("/queue/debug", response_model=dict, tags=["Debug"])
async def debug_queue(
    db: asyncpg.Connection = Depends(get_db),
):
    """
    Debug endpoint - shows last 10 messages in queue.
    For development/testing only.
    """
    try:
        records = await db.fetch(
            """
            SELECT request_id, trace_id, customer_email, subject,
                   channel, status, ticket_id, error_message, created_at, metadata
            FROM message_queue
            ORDER BY created_at DESC
            LIMIT 10
            """
        )

        return {
            "count": len(records),
            "messages": [
                {
                    "request_id": r["request_id"],
                    "trace_id": r["trace_id"],
                    "customer_email": r["customer_email"],
                    "customer_phone": r["metadata"].get("customer_phone") if r["metadata"] else None,
                    "subject": r["subject"],
                    "channel": r["channel"],
                    "status": r["status"],
                    "ticket_id": str(r["ticket_id"]) if r["ticket_id"] else None,
                    "error_message": r["error_message"],
                    "created_at": str(r["created_at"]),
                }
                for r in records
            ],
        }
    except Exception as e:
        logger.error(f"Debug query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

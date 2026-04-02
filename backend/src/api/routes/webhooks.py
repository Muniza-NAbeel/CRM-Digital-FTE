"""
Channel Webhook Routes - COMPLETE IMPLEMENTATION

Endpoints for receiving messages from external channels:
- WhatsApp (Twilio webhook) - FULLY IMPLEMENTED
- Gmail (Google Pub/Sub webhook) - FULLY IMPLEMENTED

Features:
- Proper signature/validation for each channel
- Fast response times (< 15 seconds for Twilio)
- Normalization and Kafka publishing
- Error handling and logging
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Request, Depends, Header, HTTPException
from fastapi.responses import JSONResponse

from src.channels import (
    ChannelIntakeService,
    WhatsAppHandler,
    WhatsAppWebhookHandler,
    GmailHandler,
    GmailWebhookHandler,
    ChannelValidationError,
    ChannelType,
)
from src.config import settings
from src.kafka import publish_inbound_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


# ============================================================================
# Initialize Channel Handlers
# ============================================================================

# WhatsApp handler with Twilio auth token
_whatsapp_handler = WhatsAppHandler(
    twilio_auth_token=settings.twilio_auth_token or None,
)
_whatsapp_webhook = WhatsAppWebhookHandler(_whatsapp_handler)

# Gmail handler
_gmail_handler = GmailHandler()
_gmail_webhook = GmailWebhookHandler(_gmail_handler)

# Unified intake service for Kafka publishing
_intake_service = ChannelIntakeService(
    twilio_auth_token=settings.twilio_auth_token or None,
)


# ============================================================================
# WhatsApp Webhook Endpoints
# ============================================================================

@router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    x_twilio_signature: Optional[str] = Header(None, alias="X-Twilio-Signature"),
):
    """
    WhatsApp webhook endpoint for Twilio.

    Twilio sends POST requests to this endpoint when new WhatsApp messages arrive.
    Must respond within 15 seconds or Twilio will retry.

    Features:
    - Signature validation using X-Twilio-Signature header
    - Message normalization
    - Kafka publishing for async processing
    - Fast response to Twilio

    Returns:
        JSON response to Twilio
    """
    request_id = "whatsapp-webhook"
    logger.info(f"📨 WhatsApp webhook received")

    try:
        # Get form data (Twilio sends application/x-www-form-urlencoded)
        form_data = await request.form()
        data = dict(form_data)

        # Log message info
        message_sid = data.get("MessageSid", "unknown")
        from_number = data.get("From", "unknown")
        body_preview = data.get("Body", "")[:100]
        logger.info(f"WhatsApp message: {message_sid} from {from_number} - '{body_preview}...'")

        # Process with handler (includes signature validation)
        result = await _whatsapp_webhook.handle(request)

        # If successfully received, publish to Kafka for async processing
        if result.get("status") == "received":
            try:
                # Normalize the message
                normalized = _whatsapp_handler.process(data)

                # Extract customer info
                customer_phone = normalized.customer_phone
                content = normalized.content

                # Publish to Kafka
                kafka_result = await publish_inbound_message(
                    customer_email=None,  # WhatsApp uses phone, not email
                    customer_phone=customer_phone,
                    subject=f"WhatsApp: {data.get('Body', '')[:50]}...",
                    message=content,
                    channel="whatsapp",
                    metadata={
                        "twilio_message_sid": message_sid,
                        "twilio_conversation_sid": data.get("ConversationSid"),
                        "from_number": from_number,
                        "to_number": data.get("To"),
                    },
                )

                logger.info(
                    f"✓ WhatsApp message published to Kafka: {message_sid} "
                    f"(mode={kafka_result.get('mode', 'unknown')})"
                )

                # Add Kafka info to response
                result["kafka_published"] = True
                result["kafka_message_id"] = kafka_result.get("message_id")

            except Exception as kafka_error:
                logger.error(f"Failed to publish WhatsApp to Kafka: {kafka_error}")
                # Don't fail the webhook - Kafka failure is OK
                result["kafka_published"] = False
                result["kafka_error"] = str(kafka_error)

        # Log for monitoring
        if result.get("status") == "rejected":
            logger.warning(f"WhatsApp message rejected: {result.get('reason')}")
        elif result.get("status") == "error":
            logger.error(f"WhatsApp webhook error: {result.get('reason')}")

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"WhatsApp webhook error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "reason": str(e),
                "message_sid": None,
            },
        )


@router.get("/whatsapp")
async def whatsapp_webhook_verify(
    token: Optional[str] = None,
):
    """
    WhatsApp webhook verification endpoint.

    Twilio sends GET request to verify the webhook URL during setup.
    Returns the challenge token to confirm ownership.
    """
    logger.info("WhatsApp webhook verification requested")

    # Twilio expects the challenge token to be returned
    if token:
        return token

    return "webhook_verified"


# ============================================================================
# Gmail Webhook Endpoints
# ============================================================================

@router.post("/gmail")
async def gmail_webhook(
    request: Request,
    x_goog_channel_id: Optional[str] = Header(None, alias="X-Goog-Channel-ID"),
    x_goog_resource_id: Optional[str] = Header(None, alias="X-Goog-Resource-ID"),
    x_goog_resource_state: Optional[str] = Header(None, alias="X-Goog-Resource-State"),
    x_goog_resource_uri: Optional[str] = Header(None, alias="X-Goog-Resource-URI"),
    x_goog_message_number: Optional[str] = Header(None, alias="X-Goog-Message-Number"),
    x_goog_history_id: Optional[str] = Header(None, alias="X-Goog-History-ID"),
):
    """
    Gmail webhook endpoint for Google Pub/Sub notifications.

    Google sends POST requests when new emails arrive in the monitored mailbox.
    The request body contains a base64-encoded message data.

    Features:
    - Pub/Sub notification handling
    - Email fetching via Gmail API
    - Message normalization
    - Kafka publishing

    Headers received:
    - X-Goog-Channel-ID: The ID of the notification channel
    - X-Goog-Resource-ID: The ID of the watched resource (user's email)
    - X-Goog-Resource-State: State number for the notification
    - X-Goog-Resource-URI: The URI of the watched resource
    - X-Goog-Message-Number: The message number (for email list)
    - X-Goog-History-ID: The history ID for the mailbox

    Returns:
        JSON response to Google (must be 2xx within 10 seconds)
    """
    request_id = "gmail-webhook"
    logger.info(f"📧 Gmail webhook received")

    try:
        # Get request body (may contain message data)
        body = await request.body()
        body_text = body.decode("utf-8") if body else ""

        # Log notification info
        logger.info(
            f"Gmail notification: "
            f"channel={x_goog_channel_id}, "
            f"resource={x_goog_resource_id}, "
            f"state={x_goog_resource_state}, "
            f"message_num={x_goog_message_number}"
        )

        # Process the notification
        result = await _gmail_webhook.handle_notification(
            channel_id=x_goog_channel_id,
            resource_id=x_goog_resource_id,
            resource_state=x_goog_resource_state,
            resource_uri=x_goog_resource_uri,
            message_number=x_goog_message_number,
            history_id=x_goog_history_id,
            raw_body=body_text,
        )

        # If messages were found, process them
        if result.get("messages_found", 0) > 0:
            logger.info(f"Found {result['messages_found']} new Gmail messages")

            # Process each message
            for msg_data in result.get("messages", []):
                try:
                    # Normalize the message
                    normalized = _gmail_handler.process(msg_data)

                    # Extract info
                    customer_email = normalized.customer_email
                    content = normalized.content
                    subject = normalized.metadata.get("subject", "No Subject")

                    # Publish to Kafka
                    kafka_result = await publish_inbound_message(
                        customer_email=customer_email,
                        subject=subject,
                        message=content,
                        channel="gmail",
                        metadata={
                            "gmail_message_id": normalized.external_message_id,
                            "gmail_thread_id": normalized.external_thread_id,
                            "snippet": normalized.metadata.get("snippet"),
                        },
                    )

                    logger.info(
                        f"✓ Gmail message published to Kafka: {normalized.external_message_id} "
                        f"(mode={kafka_result.get('mode', 'unknown')})"
                    )

                except Exception as msg_error:
                    logger.error(f"Failed to process Gmail message: {msg_error}")

        # Return success to Google (must be fast)
        return JSONResponse(
            status_code=200,
            content={
                "status": "received",
                "messages_found": result.get("messages_found", 0),
                "channel_id": x_goog_channel_id,
            },
        )

    except Exception as e:
        logger.error(f"Gmail webhook error: {e}", exc_info=True)
        # Still return 200 to prevent Google from retrying
        return JSONResponse(
            status_code=200,
            content={
                "status": "error",
                "reason": str(e),
                "messages_found": 0,
            },
        )


@router.get("/gmail")
async def gmail_webhook_verify(
    challenge: Optional[str] = None,
):
    """
    Gmail webhook verification endpoint.

    Google may send a verification request during setup.
    """
    logger.info("Gmail webhook verification requested")

    if challenge:
        return challenge

    return "gmail_webhook_verified"


# ============================================================================
# Webhook Status Endpoint
# ============================================================================

@router.get("/status")
async def webhook_status():
    """
    Get webhook configuration status for all channels.
    """
    return {
        "whatsapp": {
            "enabled": bool(settings.twilio_account_sid and settings.twilio_auth_token),
            "account_sid": settings.twilio_account_sid[:8] + "..." if settings.twilio_account_sid else None,
            "webhook_url": "/webhooks/whatsapp",
        },
        "gmail": {
            "enabled": bool(settings.gmail_client_id and settings.gmail_refresh_token),
            "client_id": settings.gmail_client_id[:8] + "..." if settings.gmail_client_id else None,
            "webhook_url": "/webhooks/gmail",
        },
    }

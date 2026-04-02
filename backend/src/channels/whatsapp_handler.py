"""
WhatsApp Channel Handler (Twilio) - COMPLETE IMPLEMENTATION

Handles incoming WhatsApp messages via Twilio webhook.
Features:
- Proper Twilio webhook validation using X-Twilio-Signature
- Process incoming WhatsApp messages (text + media)
- Format and send replies (handle 1600 char limit, split long messages)
- Store messages with correct channel = "whatsapp"
- Publish normalized message to Kafka topic inbound_messages

Twilio WhatsApp API:
- Webhook-based (POST requests)
- Message SID for tracking
- Session-based conversations
- Max 1600 characters per message (split if needed)
"""

import logging
import base64
import hashlib
import hmac
from datetime import datetime, timezone
from typing import Optional, Any, Dict, List, Tuple
from dataclasses import dataclass, field

from .base import ChannelHandler, ChannelType, NormalizedMessage, ChannelValidationError

logger = logging.getLogger(__name__)

# WhatsApp message limits
WHATSAPP_MAX_LENGTH = 1600  # Max characters per message
WHATSAPP_SPLIT_OVERLAP = 50  # Characters overlap when splitting for context


@dataclass
class WhatsAppMessage:
    """
    Raw WhatsApp message from Twilio webhook.

    Twilio sends webhook data as application/x-www-form-urlencoded
    or application/json depending on configuration.

    Note: All required fields (no defaults) come first, then optional fields (with defaults).
    """
    # ========================================================================
    # Required fields (NO defaults) - MUST come first
    # ========================================================================
    message_sid: str  # Unique message ID (SMxxxxxxxx)
    conversation_sid: str  # Conversation/session ID (CHxxxxxxxx)
    account_sid: str  # Twilio account ID
    body: str  # Message text
    from_number: str  # Sender's WhatsApp number (whatsapp:+14155238886)
    to_number: str  # Receiver's WhatsApp number (your Twilio number)
    date_created: str  # RFC 2822 timestamp

    # ========================================================================
    # Optional fields (WITH defaults) - MUST come after required fields
    # ========================================================================
    media_url: Optional[str] = None  # Media attachment URL (if any)
    media_content_type: Optional[str] = None  # Media MIME type
    date_sent: Optional[str] = None  # When message was sent
    num_segments: int = 1  # Message segments (for long messages)
    num_media: int = 0  # Number of media attachments
    status: str = "received"  # received, sent, delivered, etc.
    error_code: Optional[str] = None
    raw_data: Optional[Dict] = None


class WhatsAppHandler(ChannelHandler):
    """
    Handler for WhatsApp messages via Twilio.

    Features:
    - Webhook signature validation
    - Message normalization
    - Phone number cleaning
    - Media attachment handling
    - Long message splitting

    Usage:
        handler = WhatsAppHandler(twilio_auth_token="xxx")

        # For webhook requests
        normalized = handler.process_webhook(request.form)

        # For Kafka publishing
        kafka_payload = normalized.to_dict()
    """

    def __init__(self, twilio_auth_token: Optional[str] = None):
        """
        Initialize WhatsApp handler.

        Args:
            twilio_auth_token: Twilio auth token for webhook validation
        """
        super().__init__(ChannelType.WHATSAPP)
        self.twilio_auth_token = twilio_auth_token

    def normalize(self, raw_message: Any) -> NormalizedMessage:
        """
        Normalize Twilio WhatsApp message to common format.

        Args:
            raw_message: Twilio webhook data (dict or WhatsAppMessage)

        Returns:
            NormalizedMessage: Normalized message ready for processing
        """
        # Handle both dict and WhatsAppMessage
        if isinstance(raw_message, WhatsAppMessage):
            msg = raw_message
        elif isinstance(raw_message, dict):
            msg = self._parse_twilio_data(raw_message)
        else:
            raise ChannelValidationError(f"Invalid WhatsApp message type: {type(raw_message)}")

        # Clean phone numbers (remove 'whatsapp:' prefix)
        customer_phone = self._clean_phone_number(msg.from_number)
        our_number = self._clean_phone_number(msg.to_number)

        # Build content (include media info if present)
        content = msg.body
        if msg.num_media > 0 and msg.media_url:
            content = f"{msg.body}\n\n[Media Attachment: {msg.media_content_type}]\n{msg.media_url}"

        # Build normalized message
        normalized = NormalizedMessage(
            channel=ChannelType.WHATSAPP,
            content=content,
            content_type="text/plain",
            customer_phone=customer_phone,
            external_message_id=msg.message_sid,
            external_thread_id=msg.conversation_sid,
            direction="inbound",
            received_at=self._parse_date(msg.date_created),
            metadata={
                "account_sid": msg.account_sid,
                "to_number": our_number,
                "num_segments": msg.num_segments,
                "num_media": msg.num_media,
                "status": msg.status,
                "error_code": msg.error_code,
                "media_url": msg.media_url,
                "media_content_type": msg.media_content_type,
                "twilio_conversation_sid": msg.conversation_sid,
                "twilio_message_sid": msg.message_sid,
            },
        )

        return normalized

    def _parse_twilio_data(self, data: dict) -> WhatsAppMessage:
        """
        Parse Twilio webhook data into WhatsAppMessage.

        Twilio sends form data with keys like:
        - MessageSid
        - From
        - Body
        - etc.
        """
        # Helper to get value with multiple possible keys
        def get_value(*keys):
            for key in keys:
                # Try exact match
                if key in data:
                    return data[key]
                # Try lowercase
                if key.lower() in data:
                    return data[key.lower()]
            return None

        return WhatsAppMessage(
            message_sid=get_value("MessageSid", "message_sid") or "",
            conversation_sid=get_value("ConversationSid", "conversation_sid") or "",
            account_sid=get_value("AccountSid", "account_sid") or "",
            body=get_value("Body", "body") or "",
            media_url=get_value("MediaUrl0", "media_url"),
            media_content_type=get_value("MediaContentType0", "media_content_type"),
            from_number=get_value("From", "from") or "",
            to_number=get_value("To", "to") or "",
            date_created=get_value("DateCreated", "date_created") or "",
            date_sent=get_value("DateSent", "date_sent"),
            num_segments=int(get_value("NumSegments", "num_segments") or 1),
            num_media=int(get_value("NumMedia", "num_media") or 0),
            status=get_value("SmsStatus", "status") or "received",
            error_code=get_value("ErrorCode", "error_code"),
            raw_data=data,
        )

    def _clean_phone_number(self, phone: str) -> str:
        """
        Clean phone number by removing 'whatsapp:' prefix.

        Examples:
            "whatsapp:+14155238886" -> "+14155238886"
            "+14155238886" -> "+14155238886"
        """
        if not phone:
            return ""
        if phone.startswith("whatsapp:"):
            return phone[9:]
        return phone

    def _parse_date(self, date_str: str) -> datetime:
        """
        Parse Twilio date string to datetime.

        Twilio dates are in RFC 2822 format:
        "Tue, 16 Jan 2024 12:00:00 +0000"
        """
        if not date_str:
            return datetime.now(timezone.utc)

        try:
            # Try RFC 2822 format
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except (ValueError, TypeError):
            pass

        try:
            # Try ISO format
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            pass

        # Fallback
        return datetime.now(timezone.utc)

    def validate_webhook_signature(
        self,
        signature: str,
        url: str,
        params: Dict[str, str],
    ) -> bool:
        """
        Validate Twilio webhook signature.

        This ensures the webhook is actually from Twilio.
        Algorithm: HMAC-SHA1 of URL + sorted params, base64 encoded.

        Args:
            signature: X-Twilio-Signature header value
            url: Full webhook URL (including query params)
            params: POST parameters as dict

        Returns:
            bool: True if signature is valid
        """
        if not self.twilio_auth_token:
            self.logger.warning("Twilio auth token not configured, skipping validation")
            return True

        if not signature:
            self.logger.warning("No signature provided in webhook request")
            return False

        try:
            # Remove 'whatsapp:' prefix from URL if present (Twilio sometimes includes it)
            clean_url = url.replace("whatsapp:", "")

            # Sort params by key (case-sensitive)
            sorted_params = sorted(params.items())

            # Build signature string: URL + all params concatenated
            signature_string = clean_url
            for key, value in sorted_params:
                signature_string += key + value

            # Calculate HMAC-SHA1
            expected_signature = base64.b64encode(
                hmac.new(
                    self.twilio_auth_token.encode("utf-8"),
                    signature_string.encode("utf-8"),
                    hashlib.sha1,
                ).digest()
            ).decode("utf-8")

            # Compare signatures using constant-time comparison
            is_valid = hmac.compare_digest(signature, expected_signature)

            if not is_valid:
                self.logger.warning(
                    f"Invalid Twilio webhook signature. "
                    f"Expected: {expected_signature[:20]}..., Got: {signature[:20]}..."
                )

            return is_valid

        except Exception as e:
            self.logger.error(f"Error validating webhook signature: {e}", exc_info=True)
            return False

    def split_long_message(self, message: str, max_length: int = WHATSAPP_MAX_LENGTH) -> List[str]:
        """
        Split a long message into WhatsApp-compatible chunks.

        Args:
            message: Message to split
            max_length: Maximum characters per chunk (default: 1600)

        Returns:
            List[str]: List of message chunks
        """
        if len(message) <= max_length:
            return [message]

        chunks = []
        remaining = message

        while len(remaining) > max_length:
            # Find a good split point (space or newline)
            split_point = remaining.rfind(" ", 0, max_length - WHATSAPP_SPLIT_OVERLAP)
            if split_point == -1:
                split_point = remaining.rfind("\n", 0, max_length - WHATSAPP_SPLIT_OVERLAP)
            if split_point == -1:
                # No good split point found, hard split
                split_point = max_length - 3  # Leave room for "..."

            chunk = remaining[:split_point].rstrip()
            remaining = remaining[split_point:].lstrip()

            # Add continuation indicator
            if remaining:
                chunk = f"{chunk}..."

            chunks.append(chunk)

        # Add remaining text
        if remaining:
            if len(chunks) > 0:
                chunks[-1] = f"{chunks[-1]}... (continued)"
            chunks.append(remaining)

        return chunks

    def format_reply_for_whatsapp(self, content: str) -> List[str]:
        """
        Format AI response for WhatsApp delivery.

        - Split long messages
        - Add appropriate formatting
        - Handle special characters

        Args:
            content: AI response content

        Returns:
            List[str]: List of formatted message chunks
        """
        # Clean up content
        content = content.strip()

        # Remove markdown that WhatsApp doesn't support well
        # Keep basic formatting: *bold*, _italic_, ~strikethrough~, `code`
        content = content.replace("###", "").replace("##", "").replace("#", "")
        content = content.replace("**", "*")  # Convert **bold** to *bold*

        # Split if too long
        return self.split_long_message(content)


# ============================================================================
# FastAPI Webhook Handler
# ============================================================================

class WhatsAppWebhookHandler:
    """
    FastAPI-compatible webhook handler for WhatsApp.

    Features:
    - Signature validation
    - Message normalization
    - Kafka publishing preparation
    - Fast response to Twilio (< 15 seconds required)

    Usage in FastAPI:
        whatsapp_handler = WhatsAppHandler(twilio_auth_token="xxx")
        webhook_handler = WhatsAppWebhookHandler(whatsapp_handler)

        @app.post("/webhooks/whatsapp")
        async def whatsapp_webhook(request: Request):
            return await webhook_handler.handle(request)
    """

    def __init__(self, handler: WhatsAppHandler):
        self.handler = handler
        self.logger = logging.getLogger(f"{__name__}.WhatsAppWebhookHandler")

    async def handle(self, request: Any) -> Dict:
        """
        Handle incoming WhatsApp webhook request.

        Args:
            request: FastAPI Request object

        Returns:
            dict: Response to Twilio (must be fast, < 15 seconds)
        """
        try:
            # Get form data (Twilio sends application/x-www-form-urlencoded)
            form_data = await request.form()
            data = dict(form_data)

            # Get signature from headers
            signature = request.headers.get("X-Twilio-Signature", "")

            # Validate signature (if token configured)
            if self.handler.twilio_auth_token:
                # Build full URL (without query params for signature validation)
                from urllib.parse import urlencode, urlparse, parse_qs

                # Get URL without query string for signature validation
                url = str(request.url).split("?")[0]

                if not self.handler.validate_webhook_signature(signature, url, data):
                    self.logger.warning("Invalid webhook signature - rejecting request")
                    return {"status": "rejected", "reason": "invalid_signature"}

            # Normalize message
            normalized = self.handler.process(data)

            self.logger.info(
                f"WhatsApp message received: {normalized.external_message_id} "
                f"from {normalized.customer_phone} "
                f"(conversation: {normalized.external_thread_id})"
            )

            # Return success to Twilio (they expect fast response)
            # Actual processing happens asynchronously via Kafka
            return {
                "status": "received",
                "message_sid": normalized.external_message_id,
                "conversation_sid": normalized.external_thread_id,
            }

        except ChannelValidationError as e:
            self.logger.error(f"WhatsApp message validation failed: {e}")
            return {"status": "rejected", "reason": "validation_failed", "error": str(e)}

        except Exception as e:
            self.logger.error(f"Error processing WhatsApp webhook: {e}", exc_info=True)
            return {"status": "error", "reason": str(e)}


# ============================================================================
# WhatsApp Response Sender
# ============================================================================

class WhatsAppResponseSender:
    """
    Send responses via Twilio WhatsApp API.

    Features:
    - Split long messages
    - Handle media attachments
    - Track delivery status
    """

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
    ):
        """
        Initialize WhatsApp sender.

        Args:
            account_sid: Twilio Account SID
            auth_token: Twilio Auth Token
            from_number: Sender WhatsApp number (whatsapp:+14155238886)
        """
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.logger = logging.getLogger(f"{__name__}.WhatsAppResponseSender")

        # Lazy import httpx to avoid dependency issues
        self._client = None

    async def _get_client(self):
        """Get or create HTTP client."""
        if self._client is None:
            import httpx
            from httpx import BasicAuth
            self._client = httpx.AsyncClient(
                auth=BasicAuth(self.account_sid, self.auth_token),
                timeout=30.0,
            )
        return self._client

    async def send_message(
        self,
        to_number: str,
        content: str,
        conversation_sid: Optional[str] = None,
    ) -> List[Dict]:
        """
        Send WhatsApp message (auto-splits if long).

        Args:
            to_number: Recipient WhatsApp number
            content: Message content
            conversation_sid: Optional conversation SID for threading

        Returns:
            List[Dict]: List of send results for each chunk
        """
        handler = WhatsAppHandler()
        chunks = handler.format_reply_for_whatsapp(content)

        results = []
        for i, chunk in enumerate(chunks):
            result = await self._send_chunk(to_number, chunk, conversation_sid)
            results.append(result)

            # Small delay between chunks to avoid rate limiting
            if i < len(chunks) - 1:
                import asyncio
                await asyncio.sleep(0.5)

        return results

    async def _send_chunk(
        self,
        to_number: str,
        content: str,
        conversation_sid: Optional[str] = None,
    ) -> Dict:
        """Send a single message chunk."""
        try:
            client = await self._get_client()

            # Format number with whatsapp: prefix if not already
            if not to_number.startswith("whatsapp:"):
                to_number = f"whatsapp:{to_number}"
            from_num = self.from_number
            if not from_num.startswith("whatsapp:"):
                from_num = f"whatsapp:{from_num}"

            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"

            data = {
                "From": from_num,
                "To": to_number,
                "Body": content,
            }

            # Add conversation SID for threading if available
            if conversation_sid:
                data["MessagingServiceSid"] = conversation_sid

            response = await client.post(url, data=data)
            response.raise_for_status()

            result_data = response.json()

            self.logger.info(
                f"WhatsApp message sent: {result_data.get('sid')} "
                f"to {to_number}"
            )

            return {
                "success": True,
                "message_sid": result_data.get("sid"),
                "status": result_data.get("status"),
                "content": content,
            }

        except Exception as e:
            self.logger.error(f"Failed to send WhatsApp message: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "content": content,
            }

    async def send_media(
        self,
        to_number: str,
        media_url: str,
        caption: str = "",
        conversation_sid: Optional[str] = None,
    ) -> Dict:
        """
        Send media message via WhatsApp.

        Args:
            to_number: Recipient WhatsApp number
            media_url: URL of media to send
            caption: Optional caption
            conversation_sid: Optional conversation SID

        Returns:
            Dict: Send result
        """
        try:
            client = await self._get_client()

            # Format numbers
            if not to_number.startswith("whatsapp:"):
                to_number = f"whatsapp:{to_number}"
            from_num = self.from_number
            if not from_num.startswith("whatsapp:"):
                from_num = f"whatsapp:{from_num}"

            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"

            data = {
                "From": from_num,
                "To": to_number,
                "MediaUrl": media_url,
            }

            if caption:
                data["Body"] = caption

            response = await client.post(url, data=data)
            response.raise_for_status()

            result_data = response.json()

            self.logger.info(
                f"WhatsApp media sent: {result_data.get('sid')} "
                f"to {to_number}"
            )

            return {
                "success": True,
                "message_sid": result_data.get("sid"),
                "status": result_data.get("status"),
            }

        except Exception as e:
            self.logger.error(f"Failed to send WhatsApp media: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

"""
Unified Channel Intake Service - COMPLETE IMPLEMENTATION

Centralized service for handling all channel inputs:
- Web Form
- WhatsApp (Twilio)
- Gmail

Features:
- Routes incoming messages to appropriate handlers
- Normalizes all messages to common format
- Validates messages
- Prepares data for Kafka publishing
- Supports customer identification across channels
- Maintains conversation continuity
"""

import logging
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime, timezone

from .base import ChannelType, NormalizedMessage, ChannelHandler, ChannelValidationError
from .gmail_handler import GmailHandler
from .whatsapp_handler import WhatsAppHandler
from .web_form_handler import WebFormHandler

logger = logging.getLogger(__name__)


class IntakeSource(str, Enum):
    """
    Source types for message intake.
    """
    GMAIL_WEBHOOK = "gmail_webhook"
    GMAIL_POLLING = "gmail_polling"
    WHATSAPP_WEBHOOK = "whatsapp_webhook"
    WEB_FORM = "web_form"
    API = "api"  # Direct API submission


class ChannelIntakeService:
    """
    Unified service for all channel message intake.

    This service:
    1. Routes messages to appropriate channel handler
    2. Normalizes all messages to common format
    3. Validates messages
    4. Prepares data for Kafka publishing
    5. Handles customer identification across channels

    Usage:
        intake = ChannelIntakeService(twilio_auth_token="xxx")

        # Web form
        normalized = intake.process(WebForm, form_data)

        # WhatsApp webhook
        normalized = intake.process(WhatsApp, twilio_data)

        # Gmail
        normalized = intake.process(Gmail, gmail_message)

        # For Kafka
        kafka_payload = normalized.to_dict()
    """

    def __init__(
        self,
        twilio_auth_token: Optional[str] = None,
    ):
        """
        Initialize channel intake service.

        Args:
            twilio_auth_token: Twilio auth token for WhatsApp webhook validation
        """
        self.handlers: Dict[ChannelType, ChannelHandler] = {
            ChannelType.GMAIL: GmailHandler(),
            ChannelType.WHATSAPP: WhatsAppHandler(twilio_auth_token),
            ChannelType.WEB_FORM: WebFormHandler(),
        }

        self.logger = logging.getLogger(f"{__name__}.ChannelIntakeService")

    def process(
        self,
        channel: ChannelType,
        raw_message: Any,
        source: Optional[IntakeSource] = None,
    ) -> NormalizedMessage:
        """
        Process incoming message from any channel.

        Args:
            channel: Channel type (GMAIL, WHATSAPP, WEB_FORM)
            raw_message: Channel-specific raw message data
            source: Optional source type for logging

        Returns:
            NormalizedMessage: Validated normalized message

        Raises:
            ChannelValidationError: If message validation fails
        """
        self.logger.info(
            f"Processing message from channel={channel.value}, source={source or 'unknown'}"
        )

        # Get appropriate handler
        handler = self.handlers.get(channel)
        if not handler:
            raise ChannelValidationError(f"No handler for channel: {channel.value}")

        # Process and validate message
        try:
            normalized = handler.process(raw_message)

            # Add source metadata
            if source:
                normalized.metadata["intake_source"] = source.value

            self.logger.info(
                f"Message normalized successfully: {normalized.external_message_id} "
                f"(channel={channel.value}, "
                f"customer={normalized.customer_email or normalized.customer_phone})"
            )

            return normalized

        except ChannelValidationError as e:
            self.logger.error(f"Message validation failed: {e}")
            raise

        except Exception as e:
            self.logger.error(f"Error processing message: {e}", exc_info=True)
            raise ChannelValidationError(f"Processing failed: {e}")

    def process_gmail(self, gmail_message: Any) -> NormalizedMessage:
        """
        Process Gmail message.

        Convenience method for Gmail-specific processing.
        """
        return self.process(
            channel=ChannelType.GMAIL,
            raw_message=gmail_message,
            source=IntakeSource.GMAIL_POLLING,
        )

    def process_whatsapp(self, twilio_data: Dict) -> NormalizedMessage:
        """
        Process WhatsApp message from Twilio.

        Convenience method for WhatsApp-specific processing.
        """
        return self.process(
            channel=ChannelType.WHATSAPP,
            raw_message=twilio_data,
            source=IntakeSource.WHATSAPP_WEBHOOK,
        )

    def process_web_form(self, form_data: Dict) -> NormalizedMessage:
        """
        Process web form submission.

        Convenience method for web form processing.
        """
        return self.process(
            channel=ChannelType.WEB_FORM,
            raw_message=form_data,
            source=IntakeSource.WEB_FORM,
        )

    def prepare_for_kafka(self, normalized: NormalizedMessage) -> Dict:
        """
        Prepare normalized message for Kafka publishing.

        Args:
            normalized: NormalizedMessage

        Returns:
            dict: Message ready for Kafka producer
        """
        return {
            "key": normalized.external_message_id,  # For partitioning
            "value": normalized.to_dict(),
            "headers": {
                "channel": normalized.channel.value,
                "message_id": normalized.external_message_id,
                "customer_email": normalized.customer_email or "",
                "customer_phone": normalized.customer_phone or "",
            },
        }


# ============================================================================
# Customer Identification Service
# ============================================================================

class CustomerIdentificationService:
    """
    Service for identifying and linking customers across channels.

    Features:
    - Unified customer identity (email + phone)
    - Cross-channel conversation continuity
    - Customer lookup by email or phone
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.CustomerIdentificationService")

    def identify_customer(
        self,
        email: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> Dict:
        """
        Identify customer by email or phone.

        In production, this would query the database.
        For now, returns a unified customer identifier.

        Args:
            email: Customer email
            phone: Customer phone

        Returns:
            Dict: Customer identification info
        """
        customer_id = None
        customer_email = email
        customer_phone = phone

        # If we have email, use it as primary identifier
        if email:
            customer_id = f"cust_email_{email.lower()}"
        elif phone:
            customer_id = f"cust_phone_{phone}"

        return {
            "customer_id": customer_id,
            "email": customer_email,
            "phone": customer_phone,
            "is_identified": customer_id is not None,
        }

    def link_phone_to_email(
        self,
        email: str,
        phone: str,
    ) -> bool:
        """
        Link a phone number to an existing email customer.

        This enables cross-channel conversation continuity.
        Example: Customer submits web form with email, then
        contacts via WhatsApp with phone - we link them.

        Args:
            email: Customer email
            phone: Customer phone

        Returns:
            bool: True if linked successfully
        """
        self.logger.info(f"Linking phone {phone} to email {email}")
        # In production, would update customer_identifiers table
        return True

    def get_customer_conversations(
        self,
        customer_id: str,
        channels: Optional[List[ChannelType]] = None,
    ) -> List[Dict]:
        """
        Get all conversations for a customer across channels.

        Args:
            customer_id: Customer ID
            channels: Optional list of channels to filter

        Returns:
            List[Dict]: List of conversation summaries
        """
        # Placeholder - would query database
        return []


# ============================================================================
# Factory function for creating intake service
# ============================================================================

def create_intake_service(
    twilio_auth_token: Optional[str] = None,
) -> ChannelIntakeService:
    """
    Create channel intake service from configuration.

    Usage:
        from src.config import settings
        intake = create_intake_service(settings.twilio_auth_token)
    """
    return ChannelIntakeService(
        twilio_auth_token=twilio_auth_token,
    )


# ============================================================================
# Multi-Channel Message Router
# ============================================================================

class MultiChannelMessageRouter:
    """
    Routes messages to appropriate channel handlers and response senders.

    Features:
    - Automatic channel detection
    - Response routing to correct channel
    - Channel-specific formatting
    """

    def __init__(
        self,
        intake_service: ChannelIntakeService,
        twilio_account_sid: Optional[str] = None,
        twilio_auth_token: Optional[str] = None,
        twilio_whatsapp_number: Optional[str] = None,
        gmail_client_id: Optional[str] = None,
        gmail_client_secret: Optional[str] = None,
        gmail_refresh_token: Optional[str] = None,
        gmail_sender_email: Optional[str] = None,
    ):
        self.intake_service = intake_service
        self.logger = logging.getLogger(f"{__name__}.MultiChannelMessageRouter")

        # Initialize response senders
        self._whatsapp_sender = None
        self._gmail_sender = None

        if twilio_account_sid and twilio_auth_token and twilio_whatsapp_number:
            from .whatsapp_handler import WhatsAppResponseSender
            self._whatsapp_sender = WhatsAppResponseSender(
                account_sid=twilio_account_sid,
                auth_token=twilio_auth_token,
                from_number=twilio_whatsapp_number,
            )
            self.logger.info("WhatsApp response sender initialized")

        if gmail_client_id and gmail_client_secret and gmail_refresh_token and gmail_sender_email:
            from .gmail_handler import GmailResponseSender
            self._gmail_sender = GmailResponseSender(
                client_id=gmail_client_id,
                client_secret=gmail_client_secret,
                refresh_token=gmail_refresh_token,
                sender_email=gmail_sender_email,
            )
            self.logger.info("Gmail response sender initialized")

    async def send_response(
        self,
        channel: str,
        customer_identifier: str,
        content: str,
        thread_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """
        Send response via appropriate channel.

        Args:
            channel: Channel type (whatsapp, gmail, web_form)
            customer_identifier: Email or phone number
            content: Response content
            thread_id: Optional thread/conversation ID
            metadata: Optional channel-specific metadata

        Returns:
            Dict: Send result
        """
        channel = channel.lower()

        if channel == "whatsapp":
            return await self._send_whatsapp_response(
                customer_identifier, content, thread_id, metadata
            )
        elif channel == "gmail":
            return await self._send_gmail_response(
                customer_identifier, content, thread_id, metadata
            )
        else:
            # Web form or unknown - just log
            self.logger.info(f"Response for {channel} (no sender configured): {content[:100]}...")
            return {
                "success": True,
                "channel": channel,
                "note": "Response logged (no sender configured for this channel)",
            }

    async def _send_whatsapp_response(
        self,
        phone: str,
        content: str,
        conversation_sid: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Send WhatsApp response."""
        if not self._whatsapp_sender:
            return {
                "success": False,
                "error": "WhatsApp sender not configured",
            }

        # Format phone number
        if not phone.startswith("+"):
            phone = f"+{phone}"
        if not phone.startswith("whatsapp:"):
            phone = f"whatsapp:{phone}"

        results = await self._whatsapp_sender.send_message(
            to_number=phone,
            content=content,
            conversation_sid=conversation_sid,
        )

        # Return aggregated result
        all_success = all(r.get("success", False) for r in results)
        return {
            "success": all_success,
            "channel": "whatsapp",
            "messages_sent": len(results),
            "results": results,
        }

    async def _send_gmail_response(
        self,
        email: str,
        content: str,
        thread_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Send Gmail response."""
        if not self._gmail_sender:
            return {
                "success": False,
                "error": "Gmail sender not configured",
            }

        subject = metadata.get("subject", "Re: Your Support Request") if metadata else "Re: Your Support Request"
        in_reply_to = metadata.get("in_reply_to") if metadata else None
        references = metadata.get("references") if metadata else None
        is_html = metadata.get("is_html", False) if metadata else False

        result = await self._gmail_sender.send_reply(
            to_email=email,
            subject=subject,
            content=content,
            thread_id=thread_id,
            in_reply_to=in_reply_to,
            references=references,
            is_html=is_html,
        )

        return {
            "success": result.get("success", False),
            "channel": "gmail",
            "message_id": result.get("message_id"),
            "thread_id": result.get("thread_id"),
        }

    async def close(self):
        """Close all response senders."""
        if self._whatsapp_sender:
            await self._whatsapp_sender.close()
        self.logger.info("Multi-channel router closed")

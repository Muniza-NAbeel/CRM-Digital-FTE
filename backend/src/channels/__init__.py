"""
Channels Module - Multi-Channel Message Intake

Handles incoming messages from:
- Gmail (API + webhook/polling)
- WhatsApp (Twilio webhook)
- Web Form (Next.js frontend)

All messages are normalized to a common format for Kafka processing.

Usage:
    from src.channels import ChannelIntakeService, ChannelType
    
    intake = ChannelIntakeService(twilio_auth_token="xxx")
    
    # Process web form
    normalized = intake.process_web_form(form_data)
    
    # Process WhatsApp
    normalized = intake.process_whatsapp(twilio_data)
    
    # Process Gmail
    normalized = intake.process_gmail(gmail_message)
    
    # Prepare for Kafka
    kafka_payload = intake.prepare_for_kafka(normalized)
"""

from .base import (
    ChannelType,
    NormalizedMessage,
    ChannelHandler,
    ChannelHandlerError,
    ChannelValidationError,
)

from .gmail_handler import GmailHandler, GmailMessage, GmailPollingService, GmailWebhookHandler, GmailResponseSender
from .whatsapp_handler import WhatsAppHandler, WhatsAppMessage, WhatsAppWebhookHandler, WhatsAppResponseSender
from .web_form_handler import WebFormHandler, WebFormMessage, WebFormEndpointHandler
from .intake_service import ChannelIntakeService, IntakeSource, create_intake_service, CustomerIdentificationService, MultiChannelMessageRouter

__all__ = [
    # Base
    "ChannelType",
    "NormalizedMessage",
    "ChannelHandler",
    "ChannelHandlerError",
    "ChannelValidationError",

    # Gmail
    "GmailHandler",
    "GmailMessage",
    "GmailPollingService",
    "GmailWebhookHandler",
    "GmailResponseSender",

    # WhatsApp
    "WhatsAppHandler",
    "WhatsAppMessage",
    "WhatsAppWebhookHandler",
    "WhatsAppResponseSender",

    # Web Form
    "WebFormHandler",
    "WebFormMessage",
    "WebFormEndpointHandler",

    # Unified Service
    "ChannelIntakeService",
    "IntakeSource",
    "create_intake_service",
    "CustomerIdentificationService",
    "MultiChannelMessageRouter",
]

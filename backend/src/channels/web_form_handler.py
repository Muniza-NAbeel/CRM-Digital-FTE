"""
Web Form Channel Handler

Handles customer support form submissions from the Next.js frontend.
Normalizes web form data to the common format for Kafka processing.

Web Form Features:
- Customer information capture
- File attachments (metadata only)
- Session tracking
- CSRF validation ready
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Any, Dict, List
from dataclasses import dataclass
import uuid

from .base import ChannelHandler, ChannelType, NormalizedMessage, ChannelValidationError

logger = logging.getLogger(__name__)


@dataclass
class WebFormMessage:
    """
    Raw web form submission data.

    This represents the form data submitted from the Next.js frontend.
    
    Note: All required fields (no defaults) come first, then optional fields (with defaults).
    """
    # ========================================================================
    # Required fields (NO defaults) - MUST come first
    # ========================================================================
    email: str
    subject: str
    message: str

    # ========================================================================
    # Optional fields (WITH defaults) - MUST come after required fields
    # ========================================================================
    name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None

    # Optional: Customer ID if logged in
    customer_id: Optional[str] = None

    # Session/metadata
    session_id: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    page_url: Optional[str] = None

    # Attachments (metadata only - files handled separately)
    attachments: Optional[List[Dict]] = None

    # Priority (customer-selected)
    priority: Optional[str] = None

    # Raw form data
    raw_data: Optional[Dict] = None


class WebFormHandler(ChannelHandler):
    """
    Handler for web form submissions.
    
    Usage:
        handler = WebFormHandler()
        normalized = handler.process(form_data)
        
        # For Kafka publishing
        kafka_payload = normalized.to_dict()
    """
    
    def __init__(self):
        super().__init__(ChannelType.WEB_FORM)
    
    def normalize(self, raw_message: Any) -> NormalizedMessage:
        """
        Normalize web form submission to common format.
        
        Args:
            raw_message: Form data (dict or WebFormMessage)
            
        Returns:
            NormalizedMessage: Normalized message ready for processing
        """
        # Handle both dict and WebFormMessage
        if isinstance(raw_message, WebFormMessage):
            msg = raw_message
        elif isinstance(raw_message, dict):
            msg = self._parse_form_data(raw_message)
        else:
            raise ChannelValidationError(f"Invalid web form message type: {type(raw_message)}")
        
        # Validate required fields
        if not msg.email:
            raise ChannelValidationError("Email is required for web form submissions")
        
        if not msg.message:
            raise ChannelValidationError("Message content is required")
        
        # Build content (include subject + message)
        content = f"Subject: {msg.subject}\n\n{msg.message}"
        
        # Generate external message ID (web forms don't have external IDs)
        external_message_id = f"web_{uuid.uuid4().hex}"
        
        # Build normalized message
        normalized = NormalizedMessage(
            channel=ChannelType.WEB_FORM,
            content=content,
            content_type="text/plain",
            customer_email=msg.email,
            customer_phone=msg.phone,
            customer_name=msg.name,
            customer_id=msg.customer_id,
            external_message_id=external_message_id,
            external_thread_id=msg.session_id,
            direction="inbound",
            language="en",  # Could be detected from content
            received_at=datetime.now(timezone.utc),
            metadata={
                "subject": msg.subject,
                "company": msg.company,
                "session_id": msg.session_id,
                "user_agent": msg.user_agent,
                "ip_address": msg.ip_address,
                "page_url": msg.page_url,
                "attachments": msg.attachments or [],
                "priority": msg.priority,
                "form_type": "support_form",
            },
        )
        
        return normalized
    
    def _parse_form_data(self, data: dict) -> WebFormMessage:
        """
        Parse form submission data into WebFormMessage.
        """
        # Extract attachments if present
        attachments = []
        if "attachments" in data:
            attachments_data = data["attachments"]
            if isinstance(attachments_data, list):
                for att in attachments_data:
                    if isinstance(att, dict):
                        attachments.append({
                            "filename": att.get("filename", "unknown"),
                            "content_type": att.get("content_type", "application/octet-stream"),
                            "size": att.get("size", 0),
                            "url": att.get("url"),  # If uploaded to storage
                        })
        
        return WebFormMessage(
            email=data.get("email", ""),
            name=data.get("name"),
            phone=data.get("phone"),
            company=data.get("company"),
            subject=data.get("subject", "No Subject"),
            message=data.get("message", ""),
            customer_id=data.get("customer_id"),
            session_id=data.get("session_id"),
            user_agent=data.get("user_agent"),
            ip_address=data.get("ip_address"),
            page_url=data.get("page_url"),
            attachments=attachments if attachments else None,
            priority=data.get("priority"),
            raw_data=data,
        )


# ============================================================================
# FastAPI Web Form Endpoint Handler
# ============================================================================

class WebFormEndpointHandler:
    """
    FastAPI-compatible handler for web form submissions.
    
    Usage in FastAPI:
        web_form_handler = WebFormHandler()
        endpoint_handler = WebFormEndpointHandler(web_form_handler)
        
        @app.post("/api/support")
        async def submit_support_form(request: Request):
            return await endpoint_handler.handle(request)
    """
    
    def __init__(self, handler: WebFormHandler):
        self.handler = handler
        self.logger = logging.getLogger(f"{__name__}.WebFormEndpointHandler")
    
    async def handle(self, request: Any) -> Dict:
        """
        Handle incoming web form submission.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            dict: Response with ticket info
        """
        try:
            # Get JSON data
            data = await request.json()
            
            # Add request metadata
            data["user_agent"] = request.headers.get("user-agent")
            data["ip_address"] = request.client.host if request.client else None
            data["page_url"] = request.headers.get("referer")
            
            # Normalize message
            normalized = self.handler.process(data)
            
            self.logger.info(
                f"Web form submission received: {normalized.external_message_id} "
                f"from {normalized.customer_email}"
            )
            
            # Return acknowledgment
            # Note: Ticket creation happens in Kafka worker, not here
            return {
                "status": "received",
                "message_id": normalized.external_message_id,
                "email": normalized.customer_email,
                "acknowledgment": "Your support request has been received. We'll respond shortly.",
            }
            
        except ChannelValidationError as e:
            self.logger.error(f"Web form validation failed: {e}")
            return {
                "status": "error",
                "error": "validation_failed",
                "message": str(e),
            }
        
        except Exception as e:
            self.logger.error(f"Error processing web form: {e}", exc_info=True)
            return {
                "status": "error",
                "error": "processing_failed",
                "message": "Failed to process your request. Please try again.",
            }


# ============================================================================
# Pydantic Schema for Web Form (for FastAPI)
# ============================================================================

def get_web_form_schema():
    """
    Returns Pydantic schema for web form validation.
    
    This is a factory function to avoid circular imports.
    Call this in your FastAPI routes file.
    """
    from pydantic import BaseModel, Field, EmailStr, validator
    from typing import Optional, List
    
    class AttachmentMeta(BaseModel):
        filename: str
        content_type: str
        size: int
        url: Optional[str] = None
    
    class WebFormSubmitRequest(BaseModel):
        email: EmailStr = Field(..., description="Customer email address")
        name: Optional[str] = Field(None, description="Customer name")
        phone: Optional[str] = Field(None, description="Phone number")
        company: Optional[str] = Field(None, description="Company name")
        subject: str = Field(..., min_length=1, max_length=512, description="Subject")
        message: str = Field(..., min_length=1, max_length=10000, description="Message content")
        customer_id: Optional[str] = Field(None, description="Existing customer ID")
        session_id: Optional[str] = Field(None, description="Session ID")
        priority: Optional[str] = Field(None, description="Priority level")
        attachments: Optional[List[AttachmentMeta]] = Field(None, description="Attachments metadata")
        
        class Config:
            json_schema_extra = {
                "example": {
                    "email": "customer@example.com",
                    "name": "John Doe",
                    "subject": "Unable to access my account",
                    "message": "I've been trying to log in but keep getting an error...",
                }
            }
    
    return WebFormSubmitRequest

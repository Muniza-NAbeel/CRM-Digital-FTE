"""
Base channel handler and common message format.

All channel handlers normalize incoming messages to this common format
for consistent Kafka processing.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ChannelType(str, Enum):
    """
    Supported channel types.
    """
    GMAIL = "gmail"
    WHATSAPP = "whatsapp"
    WEB_FORM = "web_form"


@dataclass
class NormalizedMessage:
    """
    Normalized message format for all channels.

    This is the common format that all channel handlers produce
    and that Kafka workers consume.
    
    Note: All required fields (no defaults) come first, then optional fields (with defaults).
    """

    # ========================================================================
    # Required fields (NO defaults) - MUST come first
    # ========================================================================
    channel: ChannelType
    content: str
    
    # ========================================================================
    # Optional fields (WITH defaults) - MUST come after required fields
    # ========================================================================
    content_type: str = "text/plain"  # text/plain, text/html

    # Customer identification
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_name: Optional[str] = None
    customer_id: Optional[str] = None  # External channel-specific ID

    # Message metadata
    external_message_id: str = ""  # Gmail message ID, WhatsApp SID, etc.
    external_thread_id: Optional[str] = None  # Gmail thread ID, WhatsApp session
    direction: str = "inbound"  # inbound, outbound
    language: str = "en"

    # Timestamps
    received_at: datetime = field(default_factory=datetime.utcnow)

    # Additional metadata from channel
    metadata: dict = field(default_factory=dict)

    # Validation status
    is_valid: bool = True
    validation_errors: list = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """
        Convert to dictionary for JSON serialization (Kafka publishing).
        """
        return {
            "channel": self.channel.value,
            "content": self.content,
            "content_type": self.content_type,
            "customer_email": self.customer_email,
            "customer_phone": self.customer_phone,
            "customer_name": self.customer_name,
            "customer_id": self.customer_id,
            "external_message_id": self.external_message_id,
            "external_thread_id": self.external_thread_id,
            "direction": self.direction,
            "language": self.language,
            "received_at": self.received_at.isoformat(),
            "metadata": self.metadata,
            "is_valid": self.is_valid,
            "validation_errors": self.validation_errors,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "NormalizedMessage":
        """
        Create from dictionary (Kafka consumption).
        """
        return cls(
            channel=ChannelType(data["channel"]),
            content=data["content"],
            content_type=data.get("content_type", "text/plain"),
            customer_email=data.get("customer_email"),
            customer_phone=data.get("customer_phone"),
            customer_name=data.get("customer_name"),
            customer_id=data.get("customer_id"),
            external_message_id=data.get("external_message_id", ""),
            external_thread_id=data.get("external_thread_id"),
            direction=data.get("direction", "inbound"),
            language=data.get("language", "en"),
            received_at=datetime.fromisoformat(data["received_at"]) if data.get("received_at") else datetime.utcnow(),
            metadata=data.get("metadata", {}),
            is_valid=data.get("is_valid", True),
            validation_errors=data.get("validation_errors", []),
        )


class ChannelHandlerError(Exception):
    """
    Base exception for channel handler errors.
    """
    pass


class ChannelValidationError(ChannelHandlerError):
    """
    Raised when message validation fails.
    """
    pass


class ChannelHandler(ABC):
    """
    Abstract base class for channel handlers.
    
    All channel handlers must implement:
    - normalize(): Convert channel-specific message to NormalizedMessage
    - validate(): Validate the normalized message
    """
    
    def __init__(self, channel_type: ChannelType):
        self.channel_type = channel_type
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def normalize(self, raw_message: Any) -> NormalizedMessage:
        """
        Normalize channel-specific message to common format.
        
        Args:
            raw_message: Channel-specific raw message data
            
        Returns:
            NormalizedMessage: Normalized message ready for processing
        """
        pass
    
    def validate(self, message: NormalizedMessage) -> bool:
        """
        Validate a normalized message.
        
        Args:
            message: NormalizedMessage to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        errors = []
        
        # Required fields
        if not message.content or not message.content.strip():
            errors.append("Content is required")
        
        if not message.external_message_id:
            errors.append("External message ID is required")
        
        # Customer identification (at least one)
        if not any([
            message.customer_email,
            message.customer_phone,
            message.customer_id,
        ]):
            errors.append("At least one customer identifier is required")
        
        # Channel must match
        if message.channel != self.channel_type:
            errors.append(f"Channel mismatch: expected {self.channel_type}, got {message.channel}")
        
        message.is_valid = len(errors) == 0
        message.validation_errors = errors
        
        if errors:
            self.logger.warning(f"Validation failed for {message.external_message_id}: {errors}")
        
        return message.is_valid
    
    def process(self, raw_message: Any) -> NormalizedMessage:
        """
        Normalize and validate a message.
        
        Args:
            raw_message: Channel-specific raw message
            
        Returns:
            NormalizedMessage: Validated normalized message
            
        Raises:
            ChannelValidationError: If validation fails
        """
        try:
            normalized = self.normalize(raw_message)
            
            if not self.validate(normalized):
                raise ChannelValidationError(
                    f"Message validation failed: {normalized.validation_errors}"
                )
            
            self.logger.info(
                f"Message normalized: {normalized.external_message_id} "
                f"from {normalized.customer_email or normalized.customer_phone}"
            )
            
            return normalized
            
        except Exception as e:
            self.logger.error(f"Error processing message: {e}", exc_info=True)
            raise

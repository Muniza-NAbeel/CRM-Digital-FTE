"""
Kafka Integration for Customer Success Digital FTE

This module provides Kafka integration for asynchronous message processing.

Features:
- Publish inbound messages to Kafka
- Consume and process messages asynchronously
- Automatic fallback to in-memory queue if Kafka unavailable
- Comprehensive logging of all events

Usage:
    from src.kafka.integration import publish_inbound_message
    await publish_inbound_message(message_data)
"""

import logging
from typing import Dict, Any, Optional
from uuid import uuid4

from src.kafka.kafka_client import get_kafka_client, KafkaClient

logger = logging.getLogger(__name__)


# ============================================================================
# Message Publishing Functions
# ============================================================================

async def publish_inbound_message(
    customer_email: Optional[str] = None,
    customer_phone: Optional[str] = None,
    subject: str = "",
    message: str = "",
    channel: str = "web_form",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Publish inbound customer message to Kafka.

    Args:
        customer_email: Customer's email address (for web_form, gmail)
        customer_phone: Customer's phone number (for whatsapp)
        subject: Message subject
        message: Message content
        channel: Source channel (web_form, gmail, whatsapp)
        metadata: Additional metadata

    Returns:
        Dict with publishing status and message ID
    """
    client = get_kafka_client()

    message_id = str(uuid4())
    
    # Use email or phone as part of the key
    customer_identifier = customer_email or customer_phone or "unknown"
    message_key = f"inbound:{customer_identifier}:{message_id}"

    message_data = {
        "id": message_id,
        "type": "inbound_message",
        "customer_email": customer_email,
        "customer_phone": customer_phone,
        "subject": subject,
        "message": message,
        "channel": channel,
        "metadata": metadata or {},
    }

    success = await client.publish_inbound(message_data, message_key)

    return {
        "success": success,
        "message_id": message_id,
        "topic": client.topic_inbound,
        "mode": "kafka" if client.is_kafka_available else "fallback",
    }


async def publish_outbound_message(
    ticket_id: str,
    customer_email: str,
    response_message: str,
    channel: str = "web_form",
    agent_id: str = "ai_agent",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Publish outbound response message to Kafka.
    
    Args:
        ticket_id: Associated ticket ID
        customer_email: Customer's email address
        response_message: Response content
        channel: Target channel
        agent_id: Agent that generated response
        metadata: Additional metadata
        
    Returns:
        Dict with publishing status and message ID
    """
    client = get_kafka_client()
    
    message_id = str(uuid4())
    message_key = f"outbound:{ticket_id}:{message_id}"
    
    message_data = {
        "id": message_id,
        "type": "outbound_message",
        "ticket_id": ticket_id,
        "customer_email": customer_email,
        "message": response_message,
        "channel": channel,
        "agent_id": agent_id,
        "metadata": metadata or {},
    }
    
    success = await client.publish_outbound(message_data, message_key)
    
    return {
        "success": success,
        "message_id": message_id,
        "topic": client.topic_outbound,
        "mode": "kafka" if client.is_kafka_available else "fallback",
    }


async def publish_agent_event(
    event_type: str,
    ticket_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    event_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Publish AI agent event to Kafka.
    
    Args:
        event_type: Type of event (ticket_created, sentiment_detected, escalated, etc.)
        ticket_id: Associated ticket ID
        customer_id: Associated customer ID
        event_data: Additional event data
        
    Returns:
        Dict with publishing status and event ID
    """
    client = get_kafka_client()
    
    event_id = str(uuid4())
    event_key = f"event:{event_type}:{event_id}"
    
    event_payload = {
        "id": event_id,
        "type": event_type,
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "data": event_data or {},
    }
    
    success = await client.publish_event(event_payload, event_key)
    
    return {
        "success": success,
        "event_id": event_id,
        "topic": client.topic_events,
        "mode": "kafka" if client.is_kafka_available else "fallback",
    }


# ============================================================================
# Message Handlers (Consumers)
# ============================================================================

async def handle_inbound_message(message_data: Dict[str, Any]):
    """
    Handle inbound message from Kafka.
    This is called when a message is consumed from the inbound_messages topic.
    
    Args:
        message_data: Decoded message data
    """
    logger.info(
        f"Processing inbound message: {message_data.get('id')}",
        extra={
            "message_id": message_data.get("id"),
            "customer_email": message_data.get("customer_email"),
            "channel": message_data.get("channel"),
        }
    )
    
    # Here you would integrate with your ticket creation logic
    # For now, just log the event
    logger.info(f"Inbound message processed successfully")


async def handle_outbound_message(message_data: Dict[str, Any]):
    """
    Handle outbound message from Kafka.
    This is called when a message is consumed from the outbound_messages topic.
    
    Args:
        message_data: Decoded message data
    """
    logger.info(
        f"Processing outbound message: {message_data.get('id')}",
        extra={
            "message_id": message_data.get("id"),
            "ticket_id": message_data.get("ticket_id"),
            "channel": message_data.get("channel"),
        }
    )
    
    # Here you would integrate with your channel sending logic
    # For now, just log the event
    logger.info(f"Outbound message processed successfully")


async def handle_agent_event(event_data: Dict[str, Any]):
    """
    Handle agent event from Kafka.
    This is called when an event is consumed from the agent_events topic.
    
    Args:
        event_data: Decoded event data
    """
    logger.info(
        f"Processing agent event: {event_data.get('type')}",
        extra={
            "event_id": event_data.get("id"),
            "event_type": event_data.get("type"),
            "ticket_id": event_data.get("ticket_id"),
        }
    )
    
    # Here you would integrate with your event processing logic
    # For now, just log the event
    logger.info(f"Agent event processed successfully")


# ============================================================================
# Integration Setup
# ============================================================================

async def setup_kafka_integration():
    """
    Setup Kafka integration with message handlers.
    Call this during application startup.
    """
    client = get_kafka_client()
    
    # Register message handlers
    client.subscribe(client.topic_inbound, handle_inbound_message)
    client.subscribe(client.topic_outbound, handle_outbound_message)
    client.subscribe(client.topic_events, handle_agent_event)
    
    logger.info("Kafka integration setup complete")
    
    # Start consuming
    await client.start_consuming()
    
    logger.info("Kafka consumer started")


async def shutdown_kafka_integration():
    """
    Shutdown Kafka integration gracefully.
    Call this during application shutdown.
    """
    client = get_kafka_client()
    await client.stop_consuming()
    await client.disconnect()
    
    logger.info("Kafka integration shutdown complete")


# ============================================================================
# Health Check
# ============================================================================

async def get_kafka_health() -> Dict[str, Any]:
    """
    Get Kafka health status.
    
    Returns:
        Dict with health information
    """
    client = get_kafka_client()
    return await client.health_check()

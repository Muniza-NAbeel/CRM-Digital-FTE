"""
Kafka Producer

Async Kafka producer for sending messages to topics.
"""

import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from ..config import settings
from .topics import KafkaTopics, TopicConfig

logger = logging.getLogger(__name__)

# Global producer instance
_producer: Optional[AIOKafkaProducer] = None


class KafkaProducer:
    """
    Async Kafka producer wrapper.
    
    Provides:
    - Message serialization
    - Headers management
    - Error handling
    - Retry logic
    """
    
    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize Kafka producer.
        
        Args:
            bootstrap_servers: Kafka bootstrap servers
            max_retries: Max retry attempts on failure
            retry_delay: Delay between retries in seconds
        """
        self.bootstrap_servers = bootstrap_servers or settings.kafka_bootstrap_servers
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._producer: Optional[AIOKafkaProducer] = None
        self.logger = logging.getLogger(f"{__name__}.KafkaProducer")
    
    async def start(self) -> None:
        """
        Start the Kafka producer.
        """
        if self._producer is not None:
            self.logger.warning("Producer already started")
            return
        
        self.logger.info(f"Starting Kafka producer: {self.bootstrap_servers}")
        
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            acks="all",  # Wait for all replicas
            retries=5,
            retry_backoff_ms=100,
        )
        
        await self._producer.start()
        self.logger.info("Kafka producer started")
    
    async def stop(self) -> None:
        """
        Stop the Kafka producer gracefully.
        """
        if self._producer is None:
            return
        
        self.logger.info("Stopping Kafka producer...")
        await self._producer.stop()
        self._producer = None
        self.logger.info("Kafka producer stopped")
    
    async def send(
        self,
        topic: str,
        value: Dict[str, Any],
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        max_retries: Optional[int] = None,
    ) -> bool:
        """
        Send a message to a Kafka topic.
        
        Args:
            topic: Topic name
            value: Message value (will be JSON serialized)
            key: Message key (for partitioning)
            headers: Message headers
            max_retries: Override default max retries
            
        Returns:
            bool: True if sent successfully
        """
        if self._producer is None:
            self.logger.error("Producer not started")
            return False
        
        retries = max_retries or self.max_retries
        last_error = None
        
        # Add standard headers
        if headers is None:
            headers = {}
        headers["timestamp"] = datetime.utcnow().isoformat()
        headers["producer_id"] = "digital_fte"
        
        # Convert headers to Kafka format
        kafka_headers = [
            (k.encode("utf-8"), v.encode("utf-8"))
            for k, v in headers.items()
        ]
        
        for attempt in range(1, retries + 1):
            try:
                await self._producer.send_and_wait(
                    topic,
                    value=value,
                    key=key,
                    headers=kafka_headers,
                )
                
                self.logger.debug(
                    f"Message sent to {topic}: key={key}, "
                    f"value_keys={list(value.keys())}"
                )
                
                return True
                
            except KafkaError as e:
                last_error = e
                self.logger.warning(
                    f"Failed to send message (attempt {attempt}/{retries}): {e}"
                )
                
                if attempt < retries:
                    await asyncio.sleep(self.retry_delay * attempt)
                else:
                    self.logger.error(
                        f"Failed to send message after {retries} attempts: {e}"
                    )
        
        return False
    
    async def send_to_dlq(
        self,
        original_topic: str,
        original_message: Dict[str, Any],
        error: str,
        error_type: str = "processing_failed",
    ) -> bool:
        """
        Send failed message to Dead Letter Queue.
        
        Args:
            original_topic: Original topic where message failed
            original_message: Original message that failed
            error: Error message
            error_type: Type of error
            
        Returns:
            bool: True if sent successfully
        """
        dlq_message = {
            "original_topic": original_topic,
            "original_message": original_message,
            "error": error,
            "error_type": error_type,
            "failed_at": datetime.utcnow().isoformat(),
            "retry_count": original_message.get("_retry_count", 0) + 1,
        }
        
        key = original_message.get("external_message_id", "unknown")
        
        return await self.send(
            topic=KafkaTopics.DLQ.name,
            value=dlq_message,
            key=key,
            headers={
                "error_type": error_type,
                "original_topic": original_topic,
            },
        )
    
    async def send_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
    ) -> bool:
        """
        Send an agent event.
        
        Args:
            event_type: Type of event (ticket_created, response_sent, escalated)
            event_data: Event data
            
        Returns:
            bool: True if sent successfully
        """
        event = {
            "event_type": event_type,
            "event_data": event_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        return await self.send(
            topic=KafkaTopics.AGENT_EVENTS.name,
            value=event,
            key=event_data.get("ticket_id"),
        )
    
    async def send_response(
        self,
        ticket_id: str,
        message_id: str,
        customer_id: str,
        channel: str,
        content: str,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """
        Send a customer response message.
        
        Args:
            ticket_id: Ticket UUID
            message_id: Message UUID
            customer_id: Customer UUID
            channel: Channel type
            content: Response content
            metadata: Additional metadata
            
        Returns:
            bool: True if sent successfully
        """
        response = {
            "ticket_id": ticket_id,
            "message_id": message_id,
            "customer_id": customer_id,
            "channel": channel,
            "content": content,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
        }
        
        return await self.send(
            topic=KafkaTopics.TICKETS_OUTGOING.name,
            value=response,
            key=ticket_id,
        )


# Global producer instance for dependency injection
_global_producer: Optional[KafkaProducer] = None


async def create_producer() -> KafkaProducer:
    """
    Create and start a Kafka producer.
    """
    global _global_producer
    
    if _global_producer is None:
        _global_producer = KafkaProducer()
        await _global_producer.start()
    
    return _global_producer


async def get_producer() -> KafkaProducer:
    """
    Get the global Kafka producer.
    """
    if _global_producer is None:
        return await create_producer()
    return _global_producer


async def stop_producer() -> None:
    """
    Stop the global Kafka producer.
    """
    global _global_producer
    
    if _global_producer is not None:
        await _global_producer.stop()
        _global_producer = None

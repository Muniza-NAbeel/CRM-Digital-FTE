"""
Kafka Consumer

Async Kafka consumer for receiving messages from topics.
"""

import logging
import asyncio
from typing import Optional, Callable, Awaitable, Dict, Any, List
from datetime import datetime

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError
from aiokafka.structs import ConsumerRecord

from ..config import settings
from .topics import KafkaTopics

logger = logging.getLogger(__name__)

# Global consumer instance
_consumer: Optional[AIOKafkaConsumer] = None


class KafkaConsumer:
    """
    Async Kafka consumer wrapper.
    
    Provides:
    - Message consumption
    - Offset management
    - Error handling
    - Graceful shutdown
    """
    
    def __init__(
        self,
        topics: Optional[List[str]] = None,
        bootstrap_servers: Optional[str] = None,
        group_id: Optional[str] = None,
        auto_commit: bool = True,
        auto_offset_reset: str = "earliest",
        max_poll_records: int = 100,
        session_timeout_ms: int = 30000,
    ):
        """
        Initialize Kafka consumer.
        
        Args:
            topics: List of topics to subscribe to
            bootstrap_servers: Kafka bootstrap servers
            group_id: Consumer group ID
            auto_commit: Auto-commit offsets
            auto_offset_reset: Where to start when no offset (earliest/latest)
            max_poll_records: Max records per poll
            session_timeout_ms: Session timeout in ms
        """
        self.topics = topics or [KafkaTopics.TICKETS_INCOMING.name]
        self.bootstrap_servers = bootstrap_servers or settings.kafka_bootstrap_servers
        self.group_id = group_id or settings.kafka_consumer_group_id
        self.auto_commit = auto_commit
        self.auto_offset_reset = auto_offset_reset
        self.max_poll_records = max_poll_records
        self.session_timeout_ms = session_timeout_ms
        
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._running = False
        self._logger = logging.getLogger(f"{__name__}.KafkaConsumer")
    
    async def start(self) -> None:
        """
        Start the Kafka consumer.
        """
        if self._consumer is not None:
            self._logger.warning("Consumer already started")
            return
        
        self._logger.info(
            f"Starting Kafka consumer: topics={self.topics}, "
            f"group={self.group_id}"
        )
        
        self._consumer = AIOKafkaConsumer(
            *self.topics,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            auto_offset_reset=self.auto_offset_reset,
            enable_auto_commit=self.auto_commit,
            max_poll_records=self.max_poll_records,
            session_timeout_ms=self.session_timeout_ms,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")) if v else None,
            key_deserializer=lambda k: k.decode("utf-8") if k else None,
        )
        
        await self._consumer.start()
        self._running = True
        self._logger.info("Kafka consumer started")
    
    async def stop(self) -> None:
        """
        Stop the Kafka consumer gracefully.
        """
        if self._consumer is None:
            return
        
        self._logger.info("Stopping Kafka consumer...")
        self._running = False
        
        try:
            await self._consumer.stop()
        except Exception as e:
            self._logger.error(f"Error stopping consumer: {e}")
        
        self._consumer = None
        self._logger.info("Kafka consumer stopped")
    
    async def consume(
        self,
        handler: Callable[[ConsumerRecord], Awaitable[bool]],
        poll_timeout_ms: int = 1000,
    ) -> None:
        """
        Consume messages and process with handler.
        
        Args:
            handler: Async function to process each message
                     Returns True if successful, False otherwise
            poll_timeout_ms: Timeout for polling
        """
        if self._consumer is None:
            raise RuntimeError("Consumer not started")
        
        self._logger.info(f"Starting message consumption from {self.topics}")
        
        try:
            async for message in self._consumer:
                if not self._running:
                    break
                
                try:
                    # Process message
                    success = await handler(message)
                    
                    if success and self.auto_commit:
                        # Commit offset after successful processing
                        self._consumer.commit()
                    elif not success:
                        self._logger.warning(
                            f"Message processing failed: {message.topic} "
                            f"partition={message.partition} offset={message.offset}"
                        )
                
                except Exception as e:
                    self._logger.error(
                        f"Error processing message: {e}",
                        exc_info=True,
                    )
                    # Don't commit offset on error - will be reprocessed
        
        except asyncio.CancelledError:
            self._logger.info("Consumer cancelled")
        except KafkaError as e:
            self._logger.error(f"Kafka error during consumption: {e}")
            raise
        finally:
            self._logger.info("Message consumption ended")
    
    async def get_one(
        self,
        timeout_ms: int = 5000,
    ) -> Optional[ConsumerRecord]:
        """
        Get a single message.
        
        Args:
            timeout_ms: Timeout in milliseconds
            
        Returns:
            ConsumerRecord or None if timeout
        """
        if self._consumer is None:
            raise RuntimeError("Consumer not started")
        
        try:
            record = await asyncio.wait_for(
                self._consumer.getone(),
                timeout=timeout_ms / 1000,
            )
            return record
        except asyncio.TimeoutError:
            return None
    
    def is_running(self) -> bool:
        """Check if consumer is running."""
        return self._running and self._consumer is not None


# Import json for deserializer
import json


# Global consumer instance for dependency injection
_global_consumer: Optional[KafkaConsumer] = None


async def create_consumer(
    topics: Optional[List[str]] = None,
    group_id: Optional[str] = None,
) -> KafkaConsumer:
    """
    Create and start a Kafka consumer.
    
    Args:
        topics: Override default topics
        group_id: Override default group ID
    """
    global _global_consumer
    
    if _global_consumer is None:
        _global_consumer = KafkaConsumer(
            topics=topics,
            group_id=group_id,
        )
        await _global_consumer.start()
    
    return _global_consumer


async def get_consumer() -> KafkaConsumer:
    """
    Get the global Kafka consumer.
    """
    if _global_consumer is None:
        return await create_consumer()
    return _global_consumer


async def stop_consumer() -> None:
    """
    Stop the global Kafka consumer.
    """
    global _global_consumer
    
    if _global_consumer is not None:
        await _global_consumer.stop()
        _global_consumer = None

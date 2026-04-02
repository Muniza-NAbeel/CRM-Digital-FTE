"""
Kafka Client for Customer Success Digital FTE

Features:
- Async Producer (publish messages)
- Async Consumer (subscribe and process)
- Environment variable configuration
- Mock fallback if Kafka not available
- In-memory queue fallback on failure

Topics:
- inbound_messages: Incoming customer messages
- outbound_messages: Outgoing responses
- agent_events: AI agent events and state changes
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime, timezone
from collections import deque
from dataclasses import dataclass, field

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.errors import KafkaError

from src.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class KafkaMessage:
    """
    Standardized Kafka message structure.
    """
    topic: str
    key: str
    value: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "key": self.key,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    def serialize(self) -> bytes:
        return json.dumps(self.to_dict()).encode('utf-8')

    @classmethod
    def deserialize(cls, data: bytes) -> 'KafkaMessage':
        obj = json.loads(data.decode('utf-8'))
        return cls(
            topic=obj["topic"],
            key=obj["key"],
            value=obj["value"],
            timestamp=datetime.fromisoformat(obj["timestamp"]),
            metadata=obj.get("metadata", {}),
        )


# ============================================================================
# In-Memory Queue Fallback
# ============================================================================

class InMemoryQueue:
    """
    Fallback in-memory queue when Kafka is unavailable.
    Thread-safe async queue.
    """

    def __init__(self, max_size: int = 1000):
        self.queue: deque = deque(maxlen=max_size)
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Condition()
        logger.info("In-memory queue initialized (fallback mode)")

    async def put(self, message: KafkaMessage) -> bool:
        """Add message to queue."""
        async with self._lock:
            self.queue.append(message)
            logger.debug(f"Message queued (in-memory fallback): topic={message.topic}, key={message.key}")
        
        async with self._not_empty:
            self._not_empty.notify()
        
        return True

    async def get(self, timeout: Optional[float] = None) -> Optional[KafkaMessage]:
        """Get message from queue."""
        async with self._not_empty:
            try:
                if timeout:
                    await asyncio.wait_for(self._wait_for_message(), timeout=timeout)
                else:
                    await self._wait_for_message()
            except asyncio.TimeoutError:
                return None

        async with self._lock:
            if self.queue:
                message = self.queue.popleft()
                logger.debug(f"Message dequeued (in-memory fallback): topic={message.topic}, key={message.key}")
                return message
            return None

    async def _wait_for_message(self):
        """Wait until a message is available."""
        while not self.queue:
            await self._not_empty.wait()

    def size(self) -> int:
        return len(self.queue)


# ============================================================================
# Kafka Client
# ============================================================================

class KafkaClient:
    """
    Async Kafka client with automatic fallback to in-memory queue.
    """

    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.in_memory_queue = InMemoryQueue()
        self.is_kafka_available = False
        self._running = False
        self._consumer_tasks: List[asyncio.Task] = []
        self._message_handlers: Dict[str, Callable] = {}

        # Configuration from environment
        self.bootstrap_servers = settings.kafka_bootstrap_servers
        self.topic_inbound = settings.kafka_topic_inbound
        self.topic_outbound = settings.kafka_topic_outbound
        self.topic_events = settings.kafka_topic_events
        self.consumer_group_id = settings.kafka_consumer_group_id

        logger.info(f"Kafka client initialized (bootstrap: {self.bootstrap_servers})")

    async def connect(self) -> bool:
        """
        Establish connection to Kafka broker.
        Returns True if successful, False if fallback mode activated.
        
        Note: Uses compatible parameters for aiokafka 0.9.x
        """
        try:
            logger.info("Connecting to Kafka broker...")

            # Create producer with aiokafka 0.9.x compatible parameters
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',  # Wait for all replicas to acknowledge
                request_timeout_ms=30000,
                retry_backoff_ms=100,
                # Use compression for better performance
                compression_type="gzip",
            )
            await self.producer.start()

            # Test producer connection
            await self.producer.send_and_wait(self.topic_inbound, {"test": "connection"}, key="test")
            logger.info("✓ Kafka producer connected successfully")

            # Create consumer with aiokafka 0.9.x compatible parameters
            self.consumer = AIOKafkaConsumer(
                self.topic_inbound, self.topic_outbound, self.topic_events,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.consumer_group_id,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                auto_commit_interval_ms=1000,
                session_timeout_ms=30000,
                max_poll_interval_ms=300000,
            )
            await self.consumer.start()
            logger.info("✓ Kafka consumer connected successfully")

            self.is_kafka_available = True
            logger.info("✓ Kafka connection established - operating in KAFKA MODE")
            return True

        except Exception as e:
            logger.warning(f"✗ Kafka connection failed: {e}")
            logger.warning("⚠ Activating FALLBACK MODE - using in-memory queue")
            await self.disconnect()
            self.is_kafka_available = False
            return False

    async def disconnect(self):
        """Close Kafka connections gracefully."""
        self._running = False

        # Cancel consumer tasks
        for task in self._consumer_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Close producer
        if self.producer:
            await self.producer.stop()
            self.producer = None
            logger.info("Kafka producer disconnected")

        # Close consumer
        if self.consumer:
            await self.consumer.stop()
            self.consumer = None
            logger.info("Kafka consumer disconnected")

        logger.info("Kafka client disconnected")

    # ========================================================================
    # Producer Methods
    # ========================================================================

    async def publish(self, topic: str, message: KafkaMessage) -> bool:
        """
        Publish message to Kafka topic.
        Falls back to in-memory queue if Kafka unavailable.
        """
        try:
            if self.is_kafka_available and self.producer:
                await self.producer.send_and_wait(
                    topic=topic,
                    value=message.value,
                    key=message.key,
                )
                logger.info(
                    f"✓ Message published to Kafka: topic={topic}, key={message.key}",
                    extra={
                        "kafka_topic": topic,
                        "message_key": message.key,
                        "message_size": len(json.dumps(message.value)),
                    }
                )
                return True
            else:
                # Fallback to in-memory queue
                await self.in_memory_queue.put(message)
                logger.info(
                    f"✓ Message queued (fallback): topic={topic}, key={message.key}",
                    extra={
                        "kafka_topic": topic,
                        "message_key": message.key,
                        "fallback_mode": True,
                    }
                )
                return True

        except KafkaError as e:
            logger.error(f"✗ Kafka publish error: {e}")
            logger.warning("⚠ Switching to fallback mode")
            self.is_kafka_available = False
            await self.in_memory_queue.put(message)
            return True  # Still return True as fallback succeeded

        except Exception as e:
            logger.error(f"✗ Unexpected publish error: {e}", exc_info=True)
            await self.in_memory_queue.put(message)
            return True

    async def publish_inbound(self, message_data: Dict[str, Any], key: str) -> bool:
        """Publish message to inbound_messages topic."""
        message = KafkaMessage(
            topic=self.topic_inbound,
            key=key,
            value=message_data,
            metadata={"direction": "inbound"},
        )
        return await self.publish(self.topic_inbound, message)

    async def publish_outbound(self, message_data: Dict[str, Any], key: str) -> bool:
        """Publish message to outbound_messages topic."""
        message = KafkaMessage(
            topic=self.topic_outbound,
            key=key,
            value=message_data,
            metadata={"direction": "outbound"},
        )
        return await self.publish(self.topic_outbound, message)

    async def publish_event(self, event_data: Dict[str, Any], key: str) -> bool:
        """Publish event to agent_events topic."""
        message = KafkaMessage(
            topic=self.topic_events,
            key=key,
            value=event_data,
            metadata={"event_type": event_data.get("type", "unknown")},
        )
        return await self.publish(self.topic_events, message)

    # ========================================================================
    # Consumer Methods
    # ========================================================================

    def subscribe(self, topic: str, handler: Callable):
        """
        Register a message handler for a topic.
        Handler will be called when messages are consumed.
        """
        self._message_handlers[topic] = handler
        logger.info(f"Subscribed handler for topic: {topic}")

    async def start_consuming(self):
        """
        Start consuming messages from Kafka topics.
        Runs in background until stopped.
        """
        self._running = True
        logger.info("Starting Kafka consumer...")

        # Start Kafka consumer task
        if self.is_kafka_available and self.consumer:
            task = asyncio.create_task(self._consume_kafka_messages())
            self._consumer_tasks.append(task)
            logger.info("Kafka consumer started")

        # Start fallback consumer task (always runs)
        task = asyncio.create_task(self._consume_fallback_messages())
        self._consumer_tasks.append(task)
        logger.info("Fallback consumer started")

    async def _consume_kafka_messages(self):
        """Consume messages from Kafka."""
        try:
            async for msg in self.consumer:
                if not self._running:
                    break

                topic = msg.topic
                key = msg.key
                value = msg.value

                logger.info(
                    f"← Message consumed from Kafka: topic={topic}, key={key}",
                    extra={
                        "kafka_topic": topic,
                        "message_key": key,
                        "offset": msg.offset,
                    }
                )

                # Call registered handler
                handler = self._message_handlers.get(topic)
                if handler:
                    try:
                        await handler(value)
                    except Exception as e:
                        logger.error(f"Handler error for topic {topic}: {e}", exc_info=True)
                else:
                    logger.warning(f"No handler registered for topic: {topic}")

        except asyncio.CancelledError:
            logger.info("Kafka consumer task cancelled")
        except Exception as e:
            logger.error(f"Kafka consumer error: {e}", exc_info=True)
            self.is_kafka_available = False

    async def _consume_fallback_messages(self):
        """Consume messages from in-memory queue."""
        while self._running:
            try:
                message = await self.in_memory_queue.get(timeout=1.0)
                if message:
                    logger.info(
                        f"← Message consumed from fallback queue: topic={message.topic}, key={message.key}",
                        extra={
                            "kafka_topic": message.topic,
                            "message_key": message.key,
                            "fallback_mode": True,
                        }
                    )

                    # Call registered handler
                    handler = self._message_handlers.get(message.topic)
                    if handler:
                        try:
                            await handler(message.value)
                        except Exception as e:
                            logger.error(f"Handler error for topic {message.topic}: {e}", exc_info=True)
                    else:
                        logger.warning(f"No handler registered for topic: {message.topic}")

            except asyncio.CancelledError:
                logger.info("Fallback consumer task cancelled")
                break
            except Exception as e:
                logger.error(f"Fallback consumer error: {e}", exc_info=True)

    async def stop_consuming(self):
        """Stop consuming messages."""
        self._running = False
        logger.info("Stopping Kafka consumer...")

        for task in self._consumer_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._consumer_tasks.clear()
        logger.info("Kafka consumer stopped")

    # ========================================================================
    # Status & Health
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get Kafka client status."""
        return {
            "kafka_available": self.is_kafka_available,
            "bootstrap_servers": self.bootstrap_servers,
            "topics": {
                "inbound": self.topic_inbound,
                "outbound": self.topic_outbound,
                "events": self.topic_events,
            },
            "consumer_group": self.consumer_group_id,
            "fallback_queue_size": self.in_memory_queue.size(),
            "running": self._running,
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        status = "healthy" if self.is_kafka_available else "fallback"

        return {
            "status": status,
            "kafka_connected": self.is_kafka_available,
            "fallback_active": True,
            "fallback_queue_size": self.in_memory_queue.size(),
            "consumer_running": self._running,
        }


# ============================================================================
# Global Instance
# ============================================================================

_kafka_client: Optional[KafkaClient] = None


def get_kafka_client() -> KafkaClient:
    """Get or create global Kafka client instance."""
    global _kafka_client
    if _kafka_client is None:
        _kafka_client = KafkaClient()
    return _kafka_client


async def init_kafka() -> bool:
    """Initialize global Kafka client."""
    client = get_kafka_client()
    return await client.connect()


async def close_kafka():
    """Close global Kafka client."""
    global _kafka_client
    if _kafka_client:
        await _kafka_client.disconnect()
        _kafka_client = None

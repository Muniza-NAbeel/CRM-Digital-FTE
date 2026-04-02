"""
Kafka module for Customer Success Digital FTE.
"""

from .kafka_client import (
    KafkaClient,
    KafkaMessage,
    InMemoryQueue,
    get_kafka_client,
    init_kafka,
    close_kafka,
)

from .integration import (
    publish_inbound_message,
    publish_outbound_message,
    publish_agent_event,
    setup_kafka_integration,
    shutdown_kafka_integration,
    get_kafka_health,
    handle_inbound_message,
    handle_outbound_message,
    handle_agent_event,
)

__all__ = [
    # Client
    "KafkaClient",
    "KafkaMessage",
    "InMemoryQueue",
    "get_kafka_client",
    "init_kafka",
    "close_kafka",
    # Integration
    "publish_inbound_message",
    "publish_outbound_message",
    "publish_agent_event",
    "setup_kafka_integration",
    "shutdown_kafka_integration",
    "get_kafka_health",
    "handle_inbound_message",
    "handle_outbound_message",
    "handle_agent_event",
]

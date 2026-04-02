"""
Kafka Topic Configuration

Defines all topics used by the Customer Success Digital FTE.
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class TopicType(str, Enum):
    """
    Topic types for categorization.
    """
    INCOMING = "incoming"
    OUTGOING = "outgoing"
    EVENTS = "events"
    DEAD_LETTER = "dead_letter"


@dataclass
class TopicConfig:
    """
    Configuration for a Kafka topic.
    """
    name: str
    partitions: int = 3
    replication_factor: int = 1
    retention_ms: int = 604800000  # 7 days
    max_message_bytes: int = 1048576  # 1MB
    
    @property
    def type(self) -> TopicType:
        """Determine topic type from name."""
        if "incoming" in self.name:
            return TopicType.INCOMING
        elif "outgoing" in self.name:
            return TopicType.OUTGOING
        elif "events" in self.name:
            return TopicType.EVENTS
        elif "dlq" in self.name or "dead" in self.name:
            return TopicType.DEAD_LETTER
        return TopicType.EVENTS


class KafkaTopics:
    """
    Kafka topic definitions.
    
    All topics used by the Digital FTE system.
    """
    
    # Main processing topics
    TICKETS_INCOMING = TopicConfig(
        name="fte.tickets.incoming",
        partitions=6,
        replication_factor=1,
        description="Incoming support requests from all channels",
    )
    
    TICKETS_OUTGOING = TopicConfig(
        name="fte.tickets.outgoing",
        partitions=6,
        replication_factor=1,
        description="Outgoing responses to customers",
    )
    
    AGENT_EVENTS = TopicConfig(
        name="fte.agent.events",
        partitions=3,
        replication_factor=1,
        description="Agent processing events (created, responded, escalated)",
    )
    
    # Dead Letter Queue
    DLQ = TopicConfig(
        name="fte.dlq",
        partitions=3,
        replication_factor=1,
        retention_ms=2592000000,  # 30 days
        description="Failed messages for manual review",
    )
    
    # Metrics
    METRICS = TopicConfig(
        name="fte.metrics",
        partitions=3,
        replication_factor=1,
        description="Metrics events for aggregation",
    )
    
    @classmethod
    def all_topics(cls) -> list:
        """Get all topic configurations."""
        return [
            cls.TICKETS_INCOMING,
            cls.TICKETS_OUTGOING,
            cls.AGENT_EVENTS,
            cls.DLQ,
            cls.METRICS,
        ]
    
    @classmethod
    def get_topic_names(cls) -> list:
        """Get all topic names as strings."""
        return [t.name for t in cls.all_topics()]

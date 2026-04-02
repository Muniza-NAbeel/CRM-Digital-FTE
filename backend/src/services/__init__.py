"""
Services Module - Business Logic Layer

Core business logic for Customer Success Digital FTE.
"""

from .lifecycle import (
    TicketLifecycleManager,
    TicketState,
    EscalationReason,
    EscalationLevel,
    EscalationConfig,
    EscalationTriggers,
    StateTransition,
)

from .scheduler import LifecycleScheduler, run_scheduler

from .metrics_collector import (
    MetricsCollector,
    MetricType,
    ChannelType,
    ResponseTimeMetric,
    TokenUsageMetric,
    SuccessRateMetric,
    EscalationMetric,
)

__all__ = [
    # Lifecycle
    "TicketLifecycleManager",
    "TicketState",
    "EscalationReason",
    "EscalationLevel",
    "EscalationConfig",
    "EscalationTriggers",
    "StateTransition",
    "LifecycleScheduler",
    "run_scheduler",
    
    # Metrics
    "MetricsCollector",
    "MetricType",
    "ChannelType",
    "ResponseTimeMetric",
    "TokenUsageMetric",
    "SuccessRateMetric",
    "EscalationMetric",
]

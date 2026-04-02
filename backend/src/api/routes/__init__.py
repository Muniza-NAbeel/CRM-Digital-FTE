"""
API Routes module.
"""

from .health import router as health
from .customers import router as customers
from .tickets import router as tickets
from .conversations import router as conversations
from .knowledge_base import router as knowledge_base
from .webhooks import router as webhooks
from .metrics import router as metrics
from .kafka_status import router as kafka_status
from .messages import router as messages
from .metrics_dashboard import router as metrics_dashboard
from .worker_status import router as worker_status

__all__ = [
    "health",
    "customers",
    "tickets",
    "conversations",
    "knowledge_base",
    "webhooks",
    "metrics",
    "kafka_status",
    "messages",
    "metrics_dashboard",
    "worker_status",
]

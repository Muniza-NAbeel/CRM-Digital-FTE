"""
Kafka Status API Routes

Endpoints for monitoring Kafka integration.
"""

import logging

from fastapi import APIRouter

from src.kafka import get_kafka_health

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/status")
async def kafka_status():
    """
    Get Kafka connection status and health.
    
    Returns detailed information about:
    - Kafka connectivity
    - Fallback queue status
    - Consumer state
    """
    health = await get_kafka_health()
    
    return {
        "kafka": health,
    }


@router.get("/queue/stats")
async def queue_stats():
    """
    Get in-memory queue statistics.
    
    Returns:
    - Queue size
    - Mode (kafka/fallback)
    - Processing status
    """
    from src.kafka import get_kafka_client
    
    client = get_kafka_client()
    status = client.get_status()
    
    return {
        "mode": "kafka" if status["kafka_available"] else "fallback",
        "fallback_queue_size": status["fallback_queue_size"],
        "consumer_running": status["running"],
        "topics": status["topics"],
    }

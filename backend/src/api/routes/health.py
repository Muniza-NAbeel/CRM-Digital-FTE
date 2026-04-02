"""
Health Check Routes

Endpoints:
- GET /health/live - Liveness probe (is the app running?)
- GET /health/ready - Readiness probe (is the app ready to serve?)
- GET /health - Detailed health status
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter

from src.database import health_check as db_health_check
from src.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/live")
async def liveness_check():
    """
    Liveness probe - checks if the application is running.

    Kubernetes uses this to determine if the pod should be restarted.
    """
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": settings.app_name,
    }


@router.get("/ready")
async def readiness_check():
    """
    Readiness probe - checks if the application is ready to serve requests.

    Verifies:
    - Database connectivity
    - Required services available

    Kubernetes uses this to determine if traffic should be routed to the pod.
    """
    try:
        # Use the health_check function which already tests database
        db_health = await db_health_check()
        
        if db_health["status"] != "healthy":
            return {
                "status": "not_ready",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "checks": {
                    "database": "failed",
                },
                "error": db_health.get("error", "Unknown database error"),
            }
        
        return {
            "status": "ready",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {
                "database": "ok",
            },
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {
            "status": "not_ready",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {
                "database": "failed",
            },
            "error": str(e),
        }


@router.get("/")
async def detailed_health_check():
    """
    Detailed health check with all service statuses.

    Returns comprehensive health information for monitoring dashboards.
    """
    db_health = await db_health_check()
    
    # Get Kafka health
    from src.kafka import get_kafka_health
    kafka_health = await get_kafka_health()

    # Determine overall health
    is_healthy = db_health["status"] == "healthy"

    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "environment": settings.app_env,
        "services": {
            "database": db_health,
            "kafka": kafka_health,
        },
        "features": {
            "sentiment_analysis": settings.enable_sentiment_analysis,
            "auto_escalation": settings.enable_auto_escalation,
            "knowledge_base_learning": settings.enable_knowledge_base_learning,
            "metrics_collection": settings.enable_metrics_collection,
        },
    }

"""
Worker Monitoring API Routes

Endpoints for monitoring background worker health and performance.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from asyncpg import Connection

from src.database import get_db_connection
from src.workers import get_worker_stats

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Worker Monitoring"])


@router.get("/status")
async def get_worker_status():
    """
    Get background worker status and statistics.
    """
    stats = get_worker_stats()
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "worker": {
            "running": stats.get("running", False),
            "processed_count": stats.get("processed_count", 0),
            "error_count": stats.get("error_count", 0),
            "last_poll": stats.get("last_poll"),
            "uptime_status": "healthy" if stats.get("running") else "stopped",
        },
    }


@router.get("/queue-stats")
async def get_queue_stats(
    db: Connection = Depends(get_db_connection),
):
    """
    Get detailed message queue statistics.
    """
    # Overall stats
    overall = await db.fetchrow("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'pending') as pending,
            COUNT(*) FILTER (WHERE status = 'processing') as processing,
            COUNT(*) FILTER (WHERE status = 'completed') as completed,
            COUNT(*) FILTER (WHERE status = 'failed') as failed,
            COUNT(*) FILTER (WHERE status = 'retry') as retry,
            COUNT(*) FILTER (WHERE retry_count > 0) as with_retries,
            AVG(CASE WHEN status = 'completed' THEN 
                EXTRACT(EPOCH FROM (completed_at - created_at)) * 1000 
            END) as avg_processing_time_ms
        FROM message_queue
    """)
    
    # Last hour stats
    last_hour = await db.fetchrow("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'completed') as completed,
            COUNT(*) FILTER (WHERE status = 'failed') as failed
        FROM message_queue
        WHERE created_at >= NOW() - INTERVAL '1 hour'
    """)
    
    # Oldest pending message
    oldest_pending = await db.fetchrow("""
        SELECT
            request_id,
            created_at,
            EXTRACT(EPOCH FROM (NOW() - created_at)) as age_seconds
        FROM message_queue
        WHERE status = 'pending'
        ORDER BY created_at ASC
        LIMIT 1
    """)
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall": {
            "total": overall["total"] or 0,
            "pending": overall["pending"] or 0,
            "processing": overall["processing"] or 0,
            "completed": overall["completed"] or 0,
            "failed": overall["failed"] or 0,
            "retry": overall["retry"] or 0,
            "with_retries": overall["with_retries"] or 0,
            "avg_processing_time_ms": round(overall["avg_processing_time_ms"] or 0, 2),
        },
        "last_hour": {
            "total": last_hour["total"] or 0,
            "completed": last_hour["completed"] or 0,
            "failed": last_hour["failed"] or 0,
        },
        "oldest_pending": {
            "request_id": oldest_pending["request_id"] if oldest_pending else None,
            "age_seconds": round(oldest_pending["age_seconds"] or 0, 2) if oldest_pending else 0,
        },
        "alerts": {
            "high_queue_size": (overall["pending"] or 0) > 100,
            "old_pending_message": (oldest_pending["age_seconds"] or 0) > 300 if oldest_pending else False,
        },
    }


@router.get("/performance")
async def get_worker_performance(
    db: Connection = Depends(get_db_connection),
):
    """
    Get worker performance metrics.
    """
    # Processing rate (messages per minute)
    rate = await db.fetchrow("""
        SELECT
            COUNT(*) FILTER (WHERE status = 'completed' AND completed_at >= NOW() - INTERVAL '5 minutes') as last_5_min,
            COUNT(*) FILTER (WHERE status = 'completed' AND completed_at >= NOW() - INTERVAL '15 minutes') as last_15_min,
            COUNT(*) FILTER (WHERE status = 'completed' AND completed_at >= NOW() - INTERVAL '1 hour') as last_hour
        FROM message_queue
    """)
    
    # Calculate rates
    rate_5min = (rate["last_5_min"] or 0) / 5  # per minute
    rate_15min = (rate["last_15_min"] or 0) / 15  # per minute
    rate_hour = (rate["last_hour"] or 0) / 60  # per minute
    
    # Error rate
    error_rate = await db.fetchrow("""
        SELECT
            COUNT(*) FILTER (WHERE status = 'failed' AND created_at >= NOW() - INTERVAL '1 hour') as failures,
            COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '1 hour') as total
        FROM message_queue
    """)
    
    total = error_rate["total"] or 1
    failures = error_rate["failures"] or 0
    error_pct = (failures / total) * 100
    
    # Retry success rate
    retry_stats = await db.fetchrow("""
        SELECT
            COUNT(*) FILTER (WHERE retry_count > 0 AND status = 'completed') as retry_success,
            COUNT(*) FILTER (WHERE retry_count > 0 AND status = 'failed') as retry_fail,
            COUNT(*) FILTER (WHERE retry_count > 0) as total_retry
        FROM message_queue
    """)
    
    total_retry = retry_stats["total_retry"] or 1
    retry_success = retry_stats["retry_success"] or 0
    retry_success_pct = (retry_success / total_retry) * 100
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "processing_rate": {
            "last_5_min_per_minute": round(rate_5min, 2),
            "last_15_min_per_minute": round(rate_15min, 2),
            "last_hour_per_minute": round(rate_hour, 2),
        },
        "error_rate": {
            "last_hour_failures": failures,
            "last_hour_total": total,
            "error_percentage": round(error_pct, 2),
        },
        "retry_effectiveness": {
            "total_retries": total_retry,
            "retry_success": retry_success,
            "retry_fail": retry_stats["retry_fail"] or 0,
            "retry_success_percentage": round(retry_success_pct, 2),
        },
        "health_indicator": "healthy" if error_pct < 5 and rate_5min > 0 else "degraded" if error_pct < 20 else "unhealthy",
    }


@router.get("/alerts")
async def get_worker_alerts(
    db: Connection = Depends(get_db_connection),
):
    """
    Get active alerts and warnings for worker system.
    """
    alerts = []
    warnings = []
    
    # Check queue size
    queue_size = await db.fetchval("SELECT COUNT(*) FROM message_queue WHERE status = 'pending'")
    if queue_size and queue_size > 500:
        alerts.append({
            "type": "critical",
            "code": "HIGH_QUEUE_SIZE",
            "message": f"Queue size critical: {queue_size} pending messages",
            "threshold": 500,
            "current": queue_size,
        })
    elif queue_size and queue_size > 100:
        warnings.append({
            "type": "warning",
            "code": "ELEVATED_QUEUE_SIZE",
            "message": f"Queue size elevated: {queue_size} pending messages",
            "threshold": 100,
            "current": queue_size,
        })
    
    # Check old pending messages
    old_pending = await db.fetchval("""
        SELECT COUNT(*) FROM message_queue 
        WHERE status = 'pending' AND created_at < NOW() - INTERVAL '5 minutes'
    """)
    if old_pending and old_pending > 0:
        warnings.append({
            "type": "warning",
            "code": "STALE_MESSAGES",
            "message": f"{old_pending} messages pending for > 5 minutes",
            "threshold": 0,
            "current": old_pending,
        })
    
    # Check DLQ
    dlq_new = await db.fetchval("SELECT COUNT(*) FROM dead_letter_queue WHERE dlq_status = 'new'")
    if dlq_new and dlq_new > 10:
        warnings.append({
            "type": "warning",
            "code": "DLQ_BACKLOG",
            "message": f"{dlq_new} items in DLQ pending review",
            "threshold": 10,
            "current": dlq_new,
        })
    
    # Check error rate
    error_rate = await db.fetchrow("""
        SELECT
            COUNT(*) FILTER (WHERE status = 'failed' AND created_at >= NOW() - INTERVAL '1 hour') as failures,
            COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '1 hour') as total
        FROM message_queue
    """)
    
    total = error_rate["total"] or 1
    failures = error_rate["failures"] or 0
    error_pct = (failures / total) * 100
    
    if error_pct > 20:
        alerts.append({
            "type": "critical",
            "code": "HIGH_ERROR_RATE",
            "message": f"Error rate critical: {error_pct:.1f}%",
            "threshold": 20,
            "current": round(error_pct, 2),
        })
    elif error_pct > 5:
        warnings.append({
            "type": "warning",
            "code": "ELEVATED_ERROR_RATE",
            "message": f"Error rate elevated: {error_pct:.1f}%",
            "threshold": 5,
            "current": round(error_pct, 2),
        })
    
    # Check worker status
    worker_stats = get_worker_stats()
    if not worker_stats.get("running"):
        alerts.append({
            "type": "critical",
            "code": "WORKER_STOPPED",
            "message": "Background worker is not running",
            "threshold": "running",
            "current": "stopped",
        })
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "critical" if alerts else "warning" if warnings else "healthy",
        "alerts": alerts,
        "warnings": warnings,
        "summary": {
            "critical_count": len(alerts),
            "warning_count": len(warnings),
        },
    }

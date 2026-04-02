"""
Platinum Metrics Dashboard API

Comprehensive monitoring and metrics endpoints for production observability.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from collections import defaultdict

from fastapi import APIRouter, HTTPException, status, Request
from sqlalchemy import text

from src.workers import get_worker_stats
from src.kafka import get_kafka_health
from src.security import get_metrics_cache

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Metrics Dashboard"])


# ============================================================================
# Real-time Metrics Cache (imported from security module)
# ============================================================================


# ============================================================================
# Main Dashboard Endpoint
# ============================================================================

@router.get("/dashboard")
async def get_dashboard(
    request: Request,
):
    """
    Comprehensive metrics dashboard.

    Returns all key metrics for monitoring system health.
    """
    from src.database import get_db_session
    
    now = datetime.now(timezone.utc)
    today = now.date()
    yesterday = today - timedelta(days=1)
    last_7_days = today - timedelta(days=7)
    last_30_days = today - timedelta(days=30)

    # Get worker stats
    worker_stats = get_worker_stats()

    # Get Kafka health
    kafka_health = await get_kafka_health()

    async with get_db_session() as db:
        # ===== Queue Metrics =====
        queue_result = await db.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE status = 'pending') as pending_count,
                COUNT(*) FILTER (WHERE status = 'processing') as processing_count,
                COUNT(*) FILTER (WHERE status = 'completed') as completed_count,
                COUNT(*) FILTER (WHERE status = 'failed') as failed_count,
                COUNT(*) FILTER (WHERE retry_count > 0) as retry_count,
                AVG(CASE WHEN status = 'completed' THEN
                    EXTRACT(EPOCH FROM (completed_at - created_at)) * 1000
                END) as avg_processing_time_ms
            FROM message_queue
        """))
        queue_stats = queue_result.fetchone()

        # ===== Today's Metrics =====
        today_result = await db.execute(text("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE status = 'failed') as failed,
                COUNT(*) FILTER (WHERE is_escalated = TRUE) as escalated,
                AVG(CASE WHEN status = 'completed' THEN
                    EXTRACT(EPOCH FROM (completed_at - created_at)) * 1000
                END) as avg_processing_time_ms
            FROM message_queue
            WHERE DATE(created_at) = :today
        """), {"today": today})
        today_metrics = today_result.fetchone()

        # ===== 7-Day Trend =====
        trend_result = await db.execute(text("""
            SELECT
                DATE(created_at) as date,
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE status = 'failed') as failed,
                COUNT(*) FILTER (WHERE is_escalated = TRUE) as escalated
            FROM message_queue
            WHERE created_at >= :last_7_days
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """), {"last_7_days": last_7_days})
        seven_day_trend = trend_result.fetchall()

        # ===== Sentiment Distribution =====
        sentiment_result = await db.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE sentiment = 'positive') as positive,
                COUNT(*) FILTER (WHERE sentiment = 'neutral') as neutral,
                COUNT(*) FILTER (WHERE sentiment = 'negative') as negative,
                COUNT(*) as total
            FROM message_queue
            WHERE sentiment IS NOT NULL AND created_at >= :last_30_days
        """), {"last_30_days": last_30_days})
        sentiment_stats = sentiment_result.fetchone()

        # ===== Channel Distribution =====
        channel_result = await db.execute(text("""
            SELECT
                channel,
                COUNT(*) as count,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE status = 'failed') as failed,
                AVG(CASE WHEN status = 'completed' THEN
                    EXTRACT(EPOCH FROM (completed_at - created_at)) * 1000
                END) as avg_time_ms
            FROM message_queue
            WHERE created_at >= :last_30_days
            GROUP BY channel
            ORDER BY count DESC
        """), {"last_30_days": last_30_days})
        channel_stats = channel_result.fetchall()

        # ===== Channel Details with Phone/Email =====
        channel_detail_result = await db.execute(text("""
            SELECT
                channel,
                COUNT(*) as count,
                COUNT(DISTINCT customer_email) as unique_emails,
                COUNT(DISTINCT COALESCE(metadata->>'customer_phone', '')) FILTER (WHERE metadata->>'customer_phone' IS NOT NULL) as unique_phones
            FROM message_queue
            WHERE created_at >= :last_30_days
            GROUP BY channel
            ORDER BY count DESC
        """), {"last_30_days": last_30_days})
        channel_details = channel_detail_result.fetchall()

        # ===== DLQ Stats =====
        dlq_result = await db.execute(text("""
            SELECT
                COUNT(*) as total_dlq,
                COUNT(*) FILTER (WHERE dlq_status = 'new') as new_count,
                COUNT(*) FILTER (WHERE dlq_priority = 'high') as high_priority,
                COUNT(*) FILTER (WHERE dlq_status = 'resolved') as resolved_count
            FROM dead_letter_queue
        """))
        dlq_stats = dlq_result.fetchone()

        # ===== Retry Stats =====
        retry_result = await db.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE retry_count = 1) as retry_1,
                COUNT(*) FILTER (WHERE retry_count = 2) as retry_2,
                COUNT(*) FILTER (WHERE retry_count >= 3) as retry_3_plus
            FROM message_queue
            WHERE retry_count > 0
        """))
        retry_stats = retry_result.fetchone()

        # Calculate rates
        total_completed = today_metrics.completed or 0
        total_failed = today_metrics.failed or 0
        total_today = today_metrics.total or 1  # Avoid division by zero

        success_rate = (total_completed / total_today * 100) if total_today > 0 else 0
        failure_rate = (total_failed / total_today * 100) if total_today > 0 else 0
        escalation_rate = ((today_metrics.escalated or 0) / total_today * 100) if total_today > 0 else 0

        avg_processing_time = today_metrics.avg_processing_time_ms or 0

        # Calculate from cache
        cache = get_metrics_cache()
        cache_total = cache["total_requests"] or 1
        cache_success_rate = (cache["successful_requests"] / cache_total * 100) if cache_total > 0 else 0
        cache_avg_time = (cache["total_processing_time_ms"] / cache_total) if cache_total > 0 else 0

        # Build channel breakdown with details
        channel_breakdown = []
        total_channel_messages = sum(row.count for row in channel_stats)
        for row in channel_stats:
            detail = next((d for d in channel_details if d.channel == row.channel), None)
            channel_breakdown.append({
                "channel": row.channel,
                "name": row.channel.replace("_", " ").title(),
                "count": row.count,
                "percentage": round(row.count / total_channel_messages * 100, 2) if total_channel_messages > 0 else 0,
                "completed": row.completed or 0,
                "failed": row.failed or 0,
                "avg_time_ms": round(row.avg_time_ms or 0, 2),
                "unique_emails": detail.unique_emails if detail else 0,
                "unique_phones": detail.unique_phones if detail else 0,
            })

        return {
            "timestamp": now.isoformat(),
            "overview": {
                "total_requests_session": cache["total_requests"],
                "success_rate_session": round(cache_success_rate, 2),
                "avg_processing_time_session_ms": round(cache_avg_time, 2),
                "total_requests_today": total_today,
                "success_rate_today": round(success_rate, 2),
                "failure_rate_today": round(failure_rate, 2),
                "escalation_rate_today": round(escalation_rate, 2),
            },
            "queue_status": {
                "pending": queue_stats.pending_count or 0,
                "processing": queue_stats.processing_count or 0,
                "completed": queue_stats.completed_count or 0,
                "failed": queue_stats.failed_count or 0,
                "with_retries": queue_stats.retry_count or 0,
                "avg_processing_time_ms": round(queue_stats.avg_processing_time_ms or 0, 2),
            },
            "worker": {
                "running": worker_stats.get("running", False),
                "processed_count": worker_stats.get("processed_count", 0),
                "error_count": worker_stats.get("error_count", 0),
                "last_poll": worker_stats.get("last_poll"),
            },
            "kafka": kafka_health,
            "sentiment": {
                "positive": sentiment_stats.positive or 0,
                "neutral": sentiment_stats.neutral or 0,
                "negative": sentiment_stats.negative or 0,
                "total": sentiment_stats.total or 0,
            },
            "channels": {
                "total_channels": len(channel_breakdown),
                "breakdown": channel_breakdown,
                "summary": {
                    "web_form": next((c for c in channel_breakdown if c["channel"] == "web_form"), None),
                    "whatsapp": next((c for c in channel_breakdown if c["channel"] == "whatsapp"), None),
                    "gmail": next((c for c in channel_breakdown if c["channel"] == "gmail"), None),
                }
            },
            "retries": {
                "retry_1": retry_stats.retry_1 or 0,
                "retry_2": retry_stats.retry_2 or 0,
                "retry_3_plus": retry_stats.retry_3_plus or 0,
            },
            "dead_letter_queue": {
                "total": dlq_stats.total_dlq or 0,
                "new": dlq_stats.new_count or 0,
                "high_priority": dlq_stats.high_priority or 0,
                "resolved": dlq_stats.resolved_count or 0,
            },
            "trend_7_days": [
                {
                    "date": row.date.isoformat(),
                    "total": row.total,
                    "completed": row.completed,
                    "failed": row.failed,
                    "escalated": row.escalated,
                }
                for row in seven_day_trend
            ],
        }


@router.get("/realtime")
async def get_realtime_metrics():
    """
    Real-time metrics for live monitoring.
    Refreshes every few seconds.
    """
    from src.database import get_db_session
    
    # Get worker stats
    worker_stats = get_worker_stats()

    # Get Kafka health
    kafka_health = await get_kafka_health()

    async with get_db_session() as db:
        # Get current queue size
        queue_result = await db.execute(text("""
            SELECT COUNT(*) FROM message_queue WHERE status = 'pending'
        """))
        queue_size = queue_result.scalar()

        # Get active processing count
        processing_result = await db.execute(text("""
            SELECT COUNT(*) FROM message_queue WHERE status = 'processing'
        """))
        processing_count = processing_result.scalar()

        # Get messages in last minute
        last_minute_result = await db.execute(text("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'completed') as completed
            FROM message_queue
            WHERE created_at >= NOW() - INTERVAL '1 minute'
        """))
        last_minute = last_minute_result.fetchone()

        # Get DLQ new items
        dlq_result = await db.execute(text("""
            SELECT COUNT(*) FROM dead_letter_queue WHERE dlq_status = 'new'
        """))
        dlq_new = dlq_result.scalar()

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "queue_size": queue_size or 0,
        "processing_count": processing_count or 0,
        "last_minute": {
            "total": last_minute.total or 0,
            "completed": last_minute.completed or 0,
        },
        "worker": {
            "running": worker_stats.get("running", False),
            "processed_count": worker_stats.get("processed_count", 0),
            "error_count": worker_stats.get("error_count", 0),
        },
        "kafka": {
            "connected": kafka_health.get("kafka_connected", False),
            "fallback_active": kafka_health.get("fallback_active", True),
            "fallback_queue_size": kafka_health.get("fallback_queue_size", 0),
        },
        "dlq_new_count": dlq_new or 0,
        "system_health": "healthy" if (
            worker_stats.get("running", False) and
            queue_size is not None and
            queue_size < 1000
        ) else "degraded",
    }


@router.get("/queue-size")
async def get_queue_size():
    """
    Get current queue size and alert if threshold exceeded.
    """
    from src.database import get_db_session
    
    thresholds = {
        "warning": 100,
        "critical": 500,
    }

    async with get_db_session() as db:
        queue_result = await db.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE status = 'pending') as pending,
                COUNT(*) FILTER (WHERE status = 'processing') as processing,
                COUNT(*) FILTER (WHERE status = 'retry') as retry
            FROM message_queue
        """))
        queue_stats = queue_result.fetchone()

    pending = queue_stats.pending or 0
    processing = queue_stats.processing or 0
    retry = queue_stats.retry or 0
    total = pending + processing + retry

    # Determine alert level
    if pending >= thresholds["critical"]:
        alert_level = "critical"
        alert_message = f"Queue size ({pending}) exceeds critical threshold ({thresholds['critical']})"
    elif pending >= thresholds["warning"]:
        alert_level = "warning"
        alert_message = f"Queue size ({pending}) exceeds warning threshold ({thresholds['warning']})"
    else:
        alert_level = "normal"
        alert_message = "Queue size within normal limits"
    
    if alert_level in ["warning", "critical"]:
        logger.warning(f"QUEUE ALERT: {alert_message}")
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "queue_size": {
            "pending": pending,
            "processing": processing,
            "retry": retry,
            "total": total,
        },
        "thresholds": thresholds,
        "alert": {
            "level": alert_level,
            "message": alert_message,
        },
    }


@router.get("/performance")
async def get_performance_metrics(
    days: int = 7,
):
    """
    Performance metrics over time.
    """
    from src.database import get_db_session
    
    start_date = date.today() - timedelta(days=days)

    async with get_db_session() as db:
        # Daily performance
        daily_perf_result = await db.execute(text("""
            SELECT
                DATE(created_at) as date,
                COUNT(*) as total_requests,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE status = 'failed') as failed,
                AVG(CASE WHEN status = 'completed' THEN
                    EXTRACT(EPOCH FROM (completed_at - created_at)) * 1000
                END) as avg_processing_time_ms,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY
                    CASE WHEN status = 'completed' THEN
                        EXTRACT(EPOCH FROM (completed_at - created_at)) * 1000
                    END
                ) as p95_processing_time_ms,
                COUNT(*) FILTER (WHERE retry_count > 0) as retries,
                COUNT(*) FILTER (WHERE is_escalated = TRUE) as escalations
            FROM message_queue
            WHERE created_at >= :start_date
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """), {"start_date": start_date})
        daily_perf = daily_perf_result.fetchall()

    # Calculate aggregates
    total = sum(row.total_requests or 0 for row in daily_perf)
    completed = sum(row.completed or 0 for row in daily_perf)
    failed = sum(row.failed or 0 for row in daily_perf)

    return {
        "period": {
            "days": days,
            "start": start_date.isoformat(),
            "end": date.today().isoformat(),
        },
        "summary": {
            "total_requests": total,
            "completed": completed,
            "failed": failed,
            "success_rate": round(completed / total * 100, 2) if total > 0 else 0,
        },
        "daily": [
            {
                "date": row.date.isoformat(),
                "total_requests": row.total_requests,
                "completed": row.completed,
                "failed": row.failed,
                "avg_processing_time_ms": round(row.avg_processing_time_ms or 0, 2),
                "p95_processing_time_ms": round(row.p95_processing_time_ms or 0, 2),
                "retries": row.retries or 0,
                "escalations": row.escalations or 0,
            }
            for row in daily_perf
        ],
    }


@router.get("/dlq")
async def get_dlq_metrics(
    days: int = 7,
):
    """
    Dead Letter Queue metrics and analytics.
    """
    from src.database import get_db_session
    
    start_date = date.today() - timedelta(days=days)

    async with get_db_session() as db:
        # DLQ summary
        dlq_summary_result = await db.execute(text("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE dlq_status = 'new') as new_count,
                COUNT(*) FILTER (WHERE dlq_status = 'reviewing') as reviewing_count,
                COUNT(*) FILTER (WHERE dlq_status = 'resolved') as resolved_count,
                COUNT(*) FILTER (WHERE dlq_status = 'archived') as archived_count,
                COUNT(*) FILTER (WHERE dlq_priority = 'critical') as critical_count,
                COUNT(*) FILTER (WHERE dlq_priority = 'high') as high_count,
                AVG(retry_count) as avg_retries
            FROM dead_letter_queue
            WHERE created_at >= :start_date
        """), {"start_date": start_date})
        dlq_summary = dlq_summary_result.fetchone()

        # Category breakdown
        category_result = await db.execute(text("""
            SELECT
                dlq_category,
                COUNT(*) as count,
                COUNT(*) FILTER (WHERE dlq_status = 'resolved') as resolved
            FROM dead_letter_queue
            WHERE created_at >= :start_date
            GROUP BY dlq_category
            ORDER BY count DESC
        """), {"start_date": start_date})
        category_breakdown = category_result.fetchall()

        # Recent DLQ items
        recent_result = await db.execute(text("""
            SELECT
                original_request_id,
                customer_email,
                subject,
                failure_reason,
                dlq_category,
                dlq_priority,
                retry_count,
                created_at
            FROM dead_letter_queue
            WHERE created_at >= :start_date
            ORDER BY created_at DESC
            LIMIT 20
        """), {"start_date": start_date})
        recent_items = recent_result.fetchall()

    return {
        "period": {
            "days": days,
            "start": start_date.isoformat(),
            "end": date.today().isoformat(),
        },
        "summary": {
            "total": dlq_summary.total or 0,
            "new": dlq_summary.new_count or 0,
            "reviewing": dlq_summary.reviewing_count or 0,
            "resolved": dlq_summary.resolved_count or 0,
            "archived": dlq_summary.archived_count or 0,
            "critical": dlq_summary.critical_count or 0,
            "high_priority": dlq_summary.high_count or 0,
            "avg_retries": round(dlq_summary.avg_retries or 0, 2),
        },
        "by_category": [
            {
                "category": row.dlq_category,
                "count": row.count,
                "resolved": row.resolved,
            }
            for row in category_breakdown
        ],
        "recent_items": [
            {
                "request_id": row.original_request_id,
                "customer_email": row.customer_email,
                "subject": row.subject,
                "category": row.dlq_category,
                "priority": row.dlq_priority,
                "retries": row.retry_count,
                "created_at": row.created_at.isoformat(),
            }
            for row in recent_items
        ],
    }


@router.get("/health")
async def get_health_metrics():
    """
    System health check with detailed component status.
    """
    from src.database import get_db_session
    
    issues = []
    warnings = []

    # Check worker
    worker_stats = get_worker_stats()
    if not worker_stats.get("running"):
        issues.append("Worker is not running")

    async with get_db_session() as db:
        # Check queue size
        queue_result = await db.execute(text("SELECT COUNT(*) FROM message_queue WHERE status = 'pending'"))
        queue_size = queue_result.scalar()
        if queue_size and queue_size > 500:
            issues.append(f"Queue size critical: {queue_size} pending messages")
        elif queue_size and queue_size > 100:
            warnings.append(f"Queue size elevated: {queue_size} pending messages")

        # Check DLQ
        dlq_result = await db.execute(text("SELECT COUNT(*) FROM dead_letter_queue WHERE dlq_status = 'new'"))
        dlq_new = dlq_result.scalar()
        if dlq_new and dlq_new > 10:
            warnings.append(f"DLQ backlog: {dlq_new} items pending review")

    # Check Kafka
    kafka_health = await get_kafka_health()
    if not kafka_health.get("kafka_connected"):
        warnings.append("Kafka not connected - using fallback mode")

    # Determine overall health
    if issues:
        overall_status = "unhealthy"
    elif warnings:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": overall_status,
        "components": {
            "worker": {
                "status": "healthy" if worker_stats.get("running") else "unhealthy",
                "processed_count": worker_stats.get("processed_count", 0),
                "error_count": worker_stats.get("error_count", 0),
            },
            "queue": {
                "status": "critical" if (queue_size and queue_size > 500) else "warning" if (queue_size and queue_size > 100) else "healthy",
                "pending": queue_size or 0,
            },
            "kafka": {
                "status": "healthy" if kafka_health.get("kafka_connected") else "fallback",
                "fallback_queue_size": kafka_health.get("fallback_queue_size", 0),
            },
            "dlq": {
                "status": "warning" if (dlq_new and dlq_new > 10) else "healthy",
                "new_items": dlq_new or 0,
            },
            "database": {
                "status": "healthy",  # If we got here, DB is working
            },
        },
        "issues": issues,
        "warnings": warnings,
    }

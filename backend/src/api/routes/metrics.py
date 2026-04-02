"""
Metrics API Routes

Endpoints for retrieving system metrics and analytics.
"""

import logging
from typing import Optional
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query, HTTPException
from asyncpg import Connection

from src.database import get_db_connection
from src.services import MetricsCollector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("/summary")
async def get_metrics_summary(
    days: int = Query(7, ge=1, le=90, description="Number of days to summarize"),
    db: Connection = Depends(get_db_connection),
):
    """
    Get aggregated metrics summary.
    
    Returns totals and averages for the specified period.
    """
    collector = MetricsCollector(db)
    
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    summary = await collector.get_summary(start_date, end_date)
    
    return {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "days": days,
        },
        "metrics": summary,
    }


@router.get("/channel/{channel}")
async def get_channel_metrics(
    channel: str,
    metric_date: Optional[date] = Query(None, description="Specific date (default: today)"),
    db: Connection = Depends(get_db_connection),
):
    """
    Get metrics for a specific channel.
    
    Channels: web_form, gmail, whatsapp
    """
    valid_channels = ["web_form", "gmail", "whatsapp"]
    if channel not in valid_channels:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid channel. Must be one of: {valid_channels}",
        )
    
    metric_date = metric_date or date.today()
    
    metrics = await db.fetchrow(
        """
        SELECT 
            tickets_created,
            tickets_resolved,
            tickets_escalated,
            tickets_sla_breached,
            total_ai_calls,
            total_ai_tokens_input,
            total_ai_tokens_output,
            avg_ai_latency_ms,
            avg_first_response_time,
            avg_resolution_time,
            avg_satisfaction_score,
            sentiment_negative_count,
            sentiment_neutral_count,
            sentiment_positive_count,
            escalations_to_human
        FROM agent_metrics
        WHERE metric_date = $1 AND channel = $2
        ORDER BY metric_hour DESC
        LIMIT 24
        """,
        metric_date,
        channel,
    )
    
    if not metrics:
        return {
            "channel": channel,
            "date": metric_date.isoformat(),
            "data": [],
            "message": "No metrics found for this date",
        }
    
    return {
        "channel": channel,
        "date": metric_date.isoformat(),
        "hourly_data": [dict(metrics)],
        "totals": {
            "tickets_created": metrics["tickets_created"] or 0,
            "tickets_resolved": metrics["tickets_resolved"] or 0,
            "tickets_escalated": metrics["tickets_escalated"] or 0,
            "total_ai_calls": metrics["total_ai_calls"] or 0,
            "total_tokens": (metrics["total_ai_tokens_input"] or 0) + (metrics["total_ai_tokens_output"] or 0),
        },
        "averages": {
            "ai_latency_ms": metrics["avg_ai_latency_ms"] or 0,
            "first_response_time_sec": metrics["avg_first_response_time"] or 0,
            "satisfaction_score": float(metrics["avg_satisfaction_score"]) if metrics["avg_satisfaction_score"] else None,
        },
    }


@router.get("/tokens")
async def get_token_usage(
    days: int = Query(7, ge=1, le=90),
    db: Connection = Depends(get_db_connection),
):
    """
    Get AI token usage over time.
    """
    start_date = date.today() - timedelta(days=days)
    
    usage = await db.fetch(
        """
        SELECT 
            metric_date,
            SUM(total_ai_calls) as total_calls,
            SUM(total_ai_tokens_input) as input_tokens,
            SUM(total_ai_tokens_output) as output_tokens,
            SUM(total_ai_tokens_input + total_ai_tokens_output) as total_tokens
        FROM agent_metrics
        WHERE metric_date >= $1
        GROUP BY metric_date
        ORDER BY metric_date DESC
        """,
        start_date,
    )
    
    return {
        "period_days": days,
        "data": [dict(row) for row in usage],
        "totals": {
            "total_calls": sum(r["total_calls"] or 0 for r in usage),
            "input_tokens": sum(r["input_tokens"] or 0 for r in usage),
            "output_tokens": sum(r["output_tokens"] or 0 for r in usage),
            "total_tokens": sum(r["total_tokens"] or 0 for r in usage),
        },
    }


@router.get("/response-times")
async def get_response_times(
    days: int = Query(7, ge=1, le=90),
    channel: Optional[str] = Query(None),
    db: Connection = Depends(get_db_connection),
):
    """
    Get response time metrics.
    """
    start_date = date.today() - timedelta(days=days)
    
    params = [start_date]
    channel_filter = ""
    
    if channel:
        channel_filter = " AND channel = $2"
        params.append(channel)
    
    response_times = await db.fetch(
        f"""
        SELECT 
            metric_date,
            channel,
            avg_first_response_time,
            avg_resolution_time
        FROM agent_metrics
        WHERE metric_date >= $1{channel_filter}
        ORDER BY metric_date DESC, channel
        """,
        *params,
    )
    
    return {
        "period_days": days,
        "channel": channel or "all",
        "data": [dict(row) for row in response_times],
    }


@router.get("/escalations")
async def get_escalation_metrics(
    days: int = Query(7, ge=1, le=90),
    db: Connection = Depends(get_db_connection),
):
    """
    Get escalation metrics and reasons.
    """
    start_date = date.today() - timedelta(days=days)
    
    escalations = await db.fetch(
        """
        SELECT 
            metric_date,
            channel,
            tickets_escalated,
            escalations_to_human
        FROM agent_metrics
        WHERE metric_date >= $1
          AND tickets_escalated > 0
        ORDER BY metric_date DESC
        """,
        start_date,
    )
    
    # Get escalation reasons from tickets
    reasons = await db.fetch(
        """
        SELECT 
            escalation_reason,
            COUNT(*) as count
        FROM tickets
        WHERE escalated_at >= $1
          AND escalation_reason IS NOT NULL
        GROUP BY escalation_reason
        ORDER BY count DESC
        """,
        start_date,
    )
    
    return {
        "period_days": days,
        "data": [dict(row) for row in escalations],
        "reasons": [dict(row) for row in reasons],
        "totals": {
            "total_escalations": sum(r["tickets_escalated"] or 0 for r in escalations),
            "to_human": sum(r["escalations_to_human"] or 0 for r in escalations),
        },
    }


@router.get("/satisfaction")
async def get_satisfaction_metrics(
    days: int = Query(30, ge=1, le=365),
    db: Connection = Depends(get_db_connection),
):
    """
    Get customer satisfaction metrics.
    """
    start_date = date.today() - timedelta(days=days)
    
    # Overall satisfaction trend
    trend = await db.fetch(
        """
        SELECT 
            metric_date,
            AVG(avg_satisfaction_score) as avg_score,
            SUM(COALESCE(satisfaction_promoters, 0)) as promoters,
            SUM(COALESCE(satisfaction_passives, 0)) as passives,
            SUM(COALESCE(satisfaction_detractors, 0)) as detractors
        FROM agent_metrics
        WHERE metric_date >= $1
          AND avg_satisfaction_score IS NOT NULL
        GROUP BY metric_date
        ORDER BY metric_date DESC
        """,
        start_date,
    )
    
    # Current average
    current = await db.fetchrow(
        """
        SELECT 
            AVG(satisfaction_score) as avg_score,
            COUNT(*) as total_responses,
            COUNT(*) FILTER (WHERE satisfaction_score >= 4) as promoters,
            COUNT(*) FILTER (WHERE satisfaction_score = 3) as passives,
            COUNT(*) FILTER (WHERE satisfaction_score <= 2) as detractors
        FROM tickets
        WHERE resolved_at >= $1
          AND satisfaction_score IS NOT NULL
        """,
        start_date,
    )
    
    # Calculate NPS
    total = current["total_responses"] or 0
    if total > 0:
        nps = (
            ((current["promoters"] or 0) / total - (current["detractors"] or 0) / total) * 100
        )
    else:
        nps = 0
    
    return {
        "period_days": days,
        "current": {
            "avg_score": float(current["avg_score"]) if current["avg_score"] else None,
            "total_responses": total,
            "promoters": current["promoters"] or 0,
            "passives": current["passives"] or 0,
            "detractors": current["detractors"] or 0,
            "nps": int(nps),
        },
        "trend": [dict(row) for row in trend],
    }

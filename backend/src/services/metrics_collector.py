"""
Metrics Collector for Customer Success Digital FTE

Tracks and aggregates:
- Response times
- Token usage
- Success rates
- Escalation rates
- Channel usage
- Error rates
- Customer satisfaction

All metrics are stored in agent_metrics table and can be
exported to Kafka for real-time monitoring.
"""

import logging
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from dataclasses import dataclass, field
from enum import Enum
import asyncio

from asyncpg import Connection

logger = logging.getLogger(__name__)


# ============================================================================
# Metric Types
# ============================================================================

class MetricType(str, Enum):
    """
    Types of metrics tracked.
    """
    RESPONSE_TIME = "response_time"
    TOKEN_USAGE = "token_usage"
    SUCCESS_RATE = "success_rate"
    ESCALATION_RATE = "escalation_rate"
    CHANNEL_USAGE = "channel_usage"
    ERROR_RATE = "error_rate"
    SATISFACTION_SCORE = "satisfaction_score"
    SLA_BREACH = "sla_breach"
    FIRST_RESPONSE_TIME = "first_response_time"
    RESOLUTION_TIME = "resolution_time"


class ChannelType(str, Enum):
    """
    Support channels.
    """
    WEB_FORM = "web_form"
    GMAIL = "gmail"
    WHATSAPP = "whatsapp"


# ============================================================================
# Metric Records
# ============================================================================

@dataclass
class ResponseTimeMetric:
    """
    Response time measurement.
    """
    ticket_id: str
    channel: str
    response_time_ms: int
    is_first_response: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticket_id": self.ticket_id,
            "channel": self.channel,
            "response_time_ms": self.response_time_ms,
            "is_first_response": self.is_first_response,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class TokenUsageMetric:
    """
    AI token usage measurement.
    """
    ticket_id: str
    channel: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str = "gpt-4"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticket_id": self.ticket_id,
            "channel": self.channel,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "model": self.model,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class SuccessRateMetric:
    """
    Success/failure measurement.
    """
    channel: str
    success: bool
    error_type: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel": self.channel,
            "success": self.success,
            "error_type": self.error_type,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class EscalationMetric:
    """
    Escalation tracking.
    """
    ticket_id: str
    channel: str
    reason: str
    level: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticket_id": self.ticket_id,
            "channel": self.channel,
            "reason": self.reason,
            "level": self.level,
            "timestamp": self.timestamp.isoformat(),
        }


# ============================================================================
# Metrics Collector
# ============================================================================

class MetricsCollector:
    """
    Collects and stores metrics for the Digital FTE system.
    
    Usage:
        collector = MetricsCollector(db_connection)
        
        # Record response time
        await collector.record_response_time(ticket_id, channel, 1500)
        
        # Record token usage
        await collector.record_token_usage(ticket_id, channel, 100, 50)
        
        # Record success/failure
        await collector.record_success(channel, True)
        
        # Record escalation
        await collector.record_escalation(ticket_id, channel, "negative_sentiment", "level_2")
    """
    
    def __init__(self, db_connection: Connection):
        """
        Initialize metrics collector.
        
        Args:
            db_connection: Async PostgreSQL connection
        """
        self.db = db_connection
        self.logger = logging.getLogger(f"{__name__}.MetricsCollector")
        
        # In-memory buffers for batch inserts
        self._response_times: List[ResponseTimeMetric] = []
        self._token_usages: List[TokenUsageMetric] = []
        self._success_rates: List[SuccessRateMetric] = []
        self._escalations: List[EscalationMetric] = []
        
        # Buffer flush thresholds
        self._flush_threshold = 100
    
    async def record_response_time(
        self,
        ticket_id: str,
        channel: str,
        response_time_ms: int,
        is_first_response: bool = False,
    ) -> None:
        """
        Record a response time measurement.
        
        Args:
            ticket_id: Ticket UUID
            channel: Channel type
            response_time_ms: Response time in milliseconds
            is_first_response: Whether this is the first response
        """
        metric = ResponseTimeMetric(
            ticket_id=ticket_id,
            channel=channel,
            response_time_ms=response_time_ms,
            is_first_response=is_first_response,
        )
        
        self._response_times.append(metric)
        
        # Update ticket directly
        if is_first_response:
            await self.db.execute(
                """
                UPDATE tickets
                SET first_response_at = CURRENT_TIMESTAMP
                WHERE id = $1 AND first_response_at IS NULL
                """,
                ticket_id,
            )
        
        # Flush if buffer is full
        if len(self._response_times) >= self._flush_threshold:
            await self._flush_response_times()
        
        self.logger.debug(
            f"Response time recorded: {ticket_id} = {response_time_ms}ms "
            f"(first={is_first_response})"
        )
    
    async def record_token_usage(
        self,
        ticket_id: str,
        channel: str,
        prompt_tokens: int,
        completion_tokens: int,
        model: str = "gpt-4",
    ) -> None:
        """
        Record AI token usage.
        
        Args:
            ticket_id: Ticket UUID
            channel: Channel type
            prompt_tokens: Input tokens
            completion_tokens: Output tokens
            model: AI model used
        """
        metric = TokenUsageMetric(
            ticket_id=ticket_id,
            channel=channel,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            model=model,
        )
        
        self._token_usages.append(metric)
        
        # Update ticket totals
        await self.db.execute(
            """
            UPDATE tickets
            SET 
                total_ai_tokens = total_ai_tokens + $1,
                total_ai_latency_ms = total_ai_latency_ms + $2,
                ai_model_used = $3
            WHERE id = $4
            """,
            prompt_tokens + completion_tokens,
            0,  # Latency tracked separately
            model,
            ticket_id,
        )
        
        # Flush if buffer is full
        if len(self._token_usages) >= self._flush_threshold:
            await self._flush_token_usages()
        
        self.logger.debug(
            f"Token usage recorded: {ticket_id} = {prompt_tokens + completion_tokens} tokens"
        )
    
    async def record_success(
        self,
        channel: str,
        success: bool,
        error_type: Optional[str] = None,
    ) -> None:
        """
        Record success/failure metric.
        
        Args:
            channel: Channel type
            success: Whether operation succeeded
            error_type: Type of error if failed
        """
        metric = SuccessRateMetric(
            channel=channel,
            success=success,
            error_type=error_type,
        )
        
        self._success_rates.append(metric)
        
        # Flush if buffer is full
        if len(self._success_rates) >= self._flush_threshold:
            await self._flush_success_rates()
        
        if not success:
            self.logger.warning(f"Failure recorded: channel={channel}, error={error_type}")
    
    async def record_escalation(
        self,
        ticket_id: str,
        channel: str,
        reason: str,
        level: str = "level_1",
    ) -> None:
        """
        Record an escalation event.
        
        Args:
            ticket_id: Ticket UUID
            channel: Channel type
            reason: Escalation reason
            level: Escalation level
        """
        metric = EscalationMetric(
            ticket_id=ticket_id,
            channel=channel,
            reason=reason,
            level=level,
        )
        
        self._escalations.append(metric)
        
        # Flush if buffer is full
        if len(self._escalations) >= self._flush_threshold:
            await self._flush_escalations()
        
        self.logger.info(
            f"Escalation recorded: {ticket_id} reason={reason} level={level}"
        )
    
    async def record_satisfaction(
        self,
        ticket_id: str,
        score: int,
        feedback: Optional[str] = None,
    ) -> None:
        """
        Record customer satisfaction score.
        
        Args:
            ticket_id: Ticket UUID
            score: Score 1-5
            feedback: Optional feedback text
        """
        await self.db.execute(
            """
            UPDATE tickets
            SET 
                satisfaction_score = $1,
                satisfaction_feedback = $2
            WHERE id = $3
            """,
            score,
            feedback,
            ticket_id,
        )
        
        # Update customer average
        await self.db.execute(
            """
            UPDATE customers
            SET avg_satisfaction_score = (
                SELECT AVG(satisfaction_score)
                FROM tickets
                WHERE customer_id = (
                    SELECT customer_id FROM tickets WHERE id = $1
                )
                AND satisfaction_score IS NOT NULL
            )
            WHERE id = (
                SELECT customer_id FROM tickets WHERE id = $1
            )
            """,
            ticket_id,
        )
        
        self.logger.info(f"Satisfaction recorded: {ticket_id} = {score}/5")
    
    async def flush_all(self) -> None:
        """
        Flush all buffered metrics to database.
        """
        await asyncio.gather(
            self._flush_response_times(),
            self._flush_token_usages(),
            self._flush_success_rates(),
            self._flush_escalations(),
            return_exceptions=True,
        )
    
    async def _flush_response_times(self) -> None:
        """Flush response time buffer."""
        if not self._response_times:
            return
        
        # Aggregate by channel for hourly metrics
        now = datetime.utcnow()
        metric_date = now.date()
        metric_hour = now.hour
        
        for channel in [ChannelType.WEB_FORM.value, ChannelType.GMAIL.value, ChannelType.WHATSAPP.value]:
            channel_metrics = [m for m in self._response_times if m.channel == channel]
            if not channel_metrics:
                continue
            
            avg_time = sum(m.response_time_ms for m in channel_metrics) / len(channel_metrics)
            first_responses = [m for m in channel_metrics if m.is_first_response]
            
            if first_responses:
                await self.db.execute(
                    """
                    INSERT INTO agent_metrics (
                        metric_date, metric_hour, channel,
                        avg_first_response_time
                    )
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (metric_date, metric_hour, channel)
                    DO UPDATE SET
                        avg_first_response_time = 
                            CASE 
                                WHEN agent_metrics.avg_first_response_time IS NULL THEN $4
                                ELSE (agent_metrics.avg_first_response_time + $4) / 2
                            END
                    """,
                    metric_date,
                    metric_hour,
                    channel,
                    int(avg_time),
                )
        
        self._response_times.clear()
    
    async def _flush_token_usages(self) -> None:
        """Flush token usage buffer."""
        if not self._token_usages:
            return
        
        now = datetime.utcnow()
        metric_date = now.date()
        metric_hour = now.hour
        
        for channel in [ChannelType.WEB_FORM.value, ChannelType.GMAIL.value, ChannelType.WHATSAPP.value]:
            channel_metrics = [m for m in self._token_usages if m.channel == channel]
            if not channel_metrics:
                continue
            
            total_input = sum(m.prompt_tokens for m in channel_metrics)
            total_output = sum(m.completion_tokens for m in channel_metrics)
            total_calls = len(channel_metrics)
            
            await self.db.execute(
                """
                INSERT INTO agent_metrics (
                    metric_date, metric_hour, channel,
                    total_ai_calls, total_ai_tokens_input, total_ai_tokens_output
                )
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (metric_date, metric_hour, channel)
                DO UPDATE SET
                    total_ai_calls = agent_metrics.total_ai_calls + $4,
                    total_ai_tokens_input = agent_metrics.total_ai_tokens_input + $5,
                    total_ai_tokens_output = agent_metrics.total_ai_tokens_output + $6
                """,
                metric_date,
                metric_hour,
                channel,
                total_calls,
                total_input,
                total_output,
            )
        
        self._token_usages.clear()
    
    async def _flush_success_rates(self) -> None:
        """Flush success rate buffer."""
        if not self._success_rates:
            return
        
        now = datetime.utcnow()
        metric_date = now.date()
        metric_hour = now.hour
        
        for channel in [ChannelType.WEB_FORM.value, ChannelType.GMAIL.value, ChannelType.WHATSAPP.value]:
            channel_metrics = [m for m in self._success_rates if m.channel == channel]
            if not channel_metrics:
                continue
            
            successes = sum(1 for m in channel_metrics if m.success)
            failures = len(channel_metrics) - successes
            
            # Update tickets created/resolved based on success
            await self.db.execute(
                """
                INSERT INTO agent_metrics (
                    metric_date, metric_hour, channel,
                    tickets_created
                )
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (metric_date, metric_hour, channel)
                DO UPDATE SET
                    tickets_created = agent_metrics.tickets_created + $4
                """,
                metric_date,
                metric_hour,
                channel,
                len(channel_metrics),
            )
        
        self._success_rates.clear()
    
    async def _flush_escalations(self) -> None:
        """Flush escalation buffer."""
        if not self._escalations:
            return
        
        now = datetime.utcnow()
        metric_date = now.date()
        metric_hour = now.hour
        
        for channel in [ChannelType.WEB_FORM.value, ChannelType.GMAIL.value, ChannelType.WHATSAPP.value]:
            channel_metrics = [m for m in self._escalations if m.channel == channel]
            if not channel_metrics:
                continue
            
            await self.db.execute(
                """
                INSERT INTO agent_metrics (
                    metric_date, metric_hour, channel,
                    tickets_escalated, escalations_to_human
                )
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (metric_date, metric_hour, channel)
                DO UPDATE SET
                    tickets_escalated = agent_metrics.tickets_escalated + $4,
                    escalations_to_human = agent_metrics.escalations_to_human + $5
                """,
                metric_date,
                metric_hour,
                channel,
                len(channel_metrics),
                len(channel_metrics),
            )
        
        self._escalations.clear()
    
    async def get_summary(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Get metrics summary for date range.
        
        Args:
            start_date: Start date (default: 7 days ago)
            end_date: End date (default: today)
            
        Returns:
            Dict with aggregated metrics
        """
        if start_date is None:
            start_date = datetime.utcnow().date() - timedelta(days=7)
        if end_date is None:
            end_date = datetime.utcnow().date()
        
        result = await self.db.fetchrow(
            """
            SELECT 
                SUM(tickets_created) as total_tickets,
                SUM(tickets_resolved) as total_resolved,
                SUM(tickets_escalated) as total_escalated,
                SUM(total_ai_calls) as total_ai_calls,
                SUM(total_ai_tokens_input) as total_input_tokens,
                SUM(total_ai_tokens_output) as total_output_tokens,
                AVG(avg_first_response_time) as avg_response_time,
                AVG(avg_satisfaction_score) as avg_satisfaction
            FROM agent_metrics
            WHERE metric_date BETWEEN $1 AND $2
            """,
            start_date,
            end_date,
        )
        
        if not result:
            return {}
        
        return {
            "total_tickets": int(result["total_tickets"] or 0),
            "total_resolved": int(result["total_resolved"] or 0),
            "total_escalated": int(result["total_escalated"] or 0),
            "total_ai_calls": int(result["total_ai_calls"] or 0),
            "total_input_tokens": int(result["total_input_tokens"] or 0),
            "total_output_tokens": int(result["total_output_tokens"] or 0),
            "avg_response_time_ms": int(result["avg_response_time"] or 0),
            "avg_satisfaction": float(result["avg_satisfaction"]) if result["avg_satisfaction"] else None,
            "resolution_rate": (
                result["total_resolved"] / result["total_tickets"] * 100
                if result["total_tickets"] else 0
            ),
            "escalation_rate": (
                result["total_escalated"] / result["total_tickets"] * 100
                if result["total_tickets"] else 0
            ),
        }


# Import timedelta
from datetime import timedelta

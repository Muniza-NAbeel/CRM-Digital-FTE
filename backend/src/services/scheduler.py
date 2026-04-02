"""
Lifecycle Scheduler

Periodic tasks for ticket lifecycle management:
- SLA breach checks
- Auto-close resolved tickets
- Escalation reminders
- Metrics aggregation
"""

import asyncio
import logging
from typing import Optional, Callable, Awaitable
from datetime import datetime, timedelta

from ..config import settings
from ..database import get_connection

logger = logging.getLogger(__name__)


class LifecycleScheduler:
    """
    Scheduler for periodic lifecycle tasks.
    
    Runs background tasks at configured intervals:
    - SLA breach detection (every 5 minutes)
    - Auto-close resolved tickets (every hour)
    - Escalation reminders (every 15 minutes)
    - Metrics aggregation (every 10 minutes)
    
    Usage:
        scheduler = LifecycleScheduler(db_pool, kafka_producer)
        await scheduler.start()
        # ... running ...
        await scheduler.stop()
    """
    
    def __init__(
        self,
        db_pool=None,
        kafka_producer=None,
    ):
        """
        Initialize scheduler.
        
        Args:
            db_pool: Database connection pool
            kafka_producer: Kafka producer for events
        """
        self.db_pool = db_pool
        self.producer = kafka_producer
        
        self._running = False
        self._tasks: list = []
        
        # Task intervals (seconds)
        self.sla_check_interval = 300  # 5 minutes
        self.auto_close_interval = 3600  # 1 hour
        self.escalation_reminder_interval = 900  # 15 minutes
        self.metrics_interval = 600  # 10 minutes
        
        self.logger = logging.getLogger(f"{__name__}.LifecycleScheduler")
    
    async def start(self) -> None:
        """
        Start all scheduled tasks.
        """
        self.logger.info("Starting lifecycle scheduler...")
        self._running = True
        
        # Start background tasks
        self._tasks = [
            asyncio.create_task(self._run_periodic(
                self._sla_breach_check,
                self.sla_check_interval,
                "SLA breach check",
            )),
            asyncio.create_task(self._run_periodic(
                self._auto_close_tickets,
                self.auto_close_interval,
                "Auto-close tickets",
            )),
            asyncio.create_task(self._run_periodic(
                self._escalation_reminder,
                self.escalation_reminder_interval,
                "Escalation reminder",
            )),
            asyncio.create_task(self._run_periodic(
                self._aggregate_metrics,
                self.metrics_interval,
                "Metrics aggregation",
            )),
        ]
        
        self.logger.info(
            f"Lifecycle scheduler started with {len(self._tasks)} tasks"
        )
    
    async def stop(self) -> None:
        """
        Stop all scheduled tasks gracefully.
        """
        self.logger.info("Stopping lifecycle scheduler...")
        self._running = False
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self._tasks = []
        self.logger.info("Lifecycle scheduler stopped")
    
    async def _run_periodic(
        self,
        task_func: Callable[[], Awaitable[None]],
        interval: int,
        task_name: str,
    ) -> None:
        """
        Run a task periodically.
        
        Args:
            task_func: Async function to run
            interval: Interval in seconds
            task_name: Name for logging
        """
        self.logger.info(f"{task_name} scheduler started (interval={interval}s)")
        
        try:
            while self._running:
                try:
                    await task_func()
                except Exception as e:
                    self.logger.error(
                        f"{task_name} failed: {e}",
                        exc_info=True,
                    )
                
                # Wait for next interval
                await asyncio.sleep(interval)
        
        except asyncio.CancelledError:
            self.logger.info(f"{task_name} scheduler cancelled")
    
    async def _sla_breach_check(self) -> None:
        """
        Check for SLA breaches and send alerts.
        """
        from ..services import TicketLifecycleManager
        
        async with get_connection() as conn:
            lifecycle = TicketLifecycleManager(conn, self.producer)
            
            breached_tickets = await lifecycle.check_sla_breaches()
            
            if breached_tickets:
                self.logger.warning(
                    f"SLA breach detected for {len(breached_tickets)} tickets"
                )
                
                # Send alerts for breached tickets
                for ticket_id in breached_tickets:
                    if self.producer:
                        await self.producer.send_event(
                            event_type="sla_breach_alert",
                            event_data={
                                "ticket_id": ticket_id,
                                "alert_type": "first_response_overdue",
                                "timestamp": datetime.utcnow().isoformat(),
                            },
                        )
    
    async def _auto_close_tickets(self) -> None:
        """
        Auto-close tickets that have been resolved for 7+ days.
        """
        from ..services import TicketLifecycleManager
        
        async with get_connection() as conn:
            lifecycle = TicketLifecycleManager(conn, self.producer)
            
            closed_count = await lifecycle.auto_close_resolved_tickets(
                days_after_resolution=7,
            )
            
            if closed_count > 0:
                self.logger.info(f"Auto-closed {closed_count} tickets")
    
    async def _escalation_reminder(self) -> None:
        """
        Send reminders for pending escalations.
        """
        async with get_connection() as conn:
            # Find escalations pending for more than 1 hour
            pending = await conn.fetch(
                """
                SELECT id, ticket_number, escalated_at, assigned_to,
                       escalation_reason, escalation_level
                FROM tickets
                WHERE status = 'escalated'
                  AND escalated_at < NOW() - INTERVAL '1 hour'
                  AND assigned_to IS NOT NULL
                ORDER BY escalated_at ASC
                LIMIT 50
                """,
            )
            
            for ticket in pending:
                self.logger.info(
                    f"Escalation reminder: {ticket['ticket_number']} "
                    f"assigned to {ticket['assigned_to']}"
                )
                
                if self.producer:
                    await self.producer.send_event(
                        event_type="escalation_reminder",
                        event_data={
                            "ticket_id": str(ticket["id"]),
                            "ticket_number": ticket["ticket_number"],
                            "assigned_to": ticket["assigned_to"],
                            "escalation_level": ticket["escalation_level"],
                            "pending_since": ticket["escalated_at"].isoformat(),
                        },
                    )
    
    async def _aggregate_metrics(self) -> None:
        """
        Aggregate hourly metrics.
        """
        try:
            async with get_connection() as conn:
                # Get current hour
                now = datetime.utcnow()
                metric_date = now.date()
                metric_hour = now.hour
                
                # Aggregate by channel
                for channel in ["web_form", "gmail", "whatsapp"]:
                    # Count tickets created this hour
                    tickets_created = await conn.fetchval(
                        """
                        SELECT COUNT(*) FROM tickets
                        WHERE channel = $1
                          AND created_at >= date_trunc('hour', NOW())
                        """,
                        channel,
                    )
                    
                    # Count tickets resolved this hour
                    tickets_resolved = await conn.fetchval(
                        """
                        SELECT COUNT(*) FROM tickets
                        WHERE channel = $1
                          AND resolved_at >= date_trunc('hour', NOW())
                        """,
                        channel,
                    )
                    
                    # Count escalations this hour
                    tickets_escalated = await conn.fetchval(
                        """
                        SELECT COUNT(*) FROM tickets
                        WHERE channel = $1
                          AND escalated_at >= date_trunc('hour', NOW())
                        """,
                        channel,
                    )
                    
                    # Average response time (in seconds)
                    avg_response_time = await conn.fetchval(
                        """
                        SELECT EXTRACT(EPOCH FROM AVG(first_response_at - created_at))
                        FROM tickets
                        WHERE channel = $1
                          AND first_response_at >= date_trunc('hour', NOW())
                        """,
                        channel,
                    )
                    
                    # Upsert metrics record
                    await conn.execute(
                        """
                        INSERT INTO agent_metrics (
                            metric_date, metric_hour, channel,
                            tickets_created, tickets_resolved, tickets_escalated,
                            avg_first_response_time
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT (metric_date, metric_hour, channel)
                        DO UPDATE SET
                            tickets_created = agent_metrics.tickets_created + $4,
                            tickets_resolved = agent_metrics.tickets_resolved + $5,
                            tickets_escalated = agent_metrics.tickets_escalated + $6,
                            avg_first_response_time = 
                                CASE 
                                    WHEN $7 IS NULL THEN agent_metrics.avg_first_response_time
                                    WHEN agent_metrics.avg_first_response_time IS NULL THEN $7
                                    ELSE (agent_metrics.avg_first_response_time + $7) / 2
                                END
                        """,
                        metric_date,
                        metric_hour,
                        channel,
                        int(tickets_created or 0),
                        int(tickets_resolved or 0),
                        int(tickets_escalated or 0),
                        int(avg_response_time or 0),
                    )
                
                self.logger.debug(
                    f"Metrics aggregated for {metric_date} hour {metric_hour}"
                )
                
        except Exception as e:
            self.logger.error(f"Metrics aggregation failed: {e}", exc_info=True)


async def run_scheduler() -> None:
    """
    Run the lifecycle scheduler.
    
    Main entry point for standalone scheduler process.
    """
    from ..database import init_database, close_database
    from ..kafka import create_producer, stop_producer
    
    scheduler = LifecycleScheduler()
    
    try:
        # Initialize connections
        await init_database()
        scheduler.db_pool = "initialized"  # Marker that DB is ready
        scheduler.producer = await create_producer()
        
        await scheduler.start()
        
        # Keep running until interrupted
        while scheduler._running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Scheduler interrupted")
    except Exception as e:
        logger.error(f"Scheduler error: {e}", exc_info=True)
        raise
    finally:
        await scheduler.stop()
        await close_database()
        await stop_producer()

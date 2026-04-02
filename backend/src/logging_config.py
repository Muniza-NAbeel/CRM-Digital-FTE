"""
Logging Configuration for Customer Success Digital FTE

Provides:
- Structured JSON logging
- Log levels by environment
- Request/response logging
- Error tracking with context
- Performance logging
"""

import logging
import sys
import json
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path

# Use absolute import instead of relative
from src.config import settings


# ============================================================================
# Custom Formatters
# ============================================================================

class StructuredFormatter(logging.Formatter):
    """
    JSON structured formatter for production logging.
    
    Outputs logs as JSON for easy parsing by log aggregators
    (ELK, Datadog, Splunk, etc.)
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in [
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "exc_info", "exc_text", "thread", "threadName",
                "message", "asctime",
            ]:
                try:
                    json.dumps(value)  # Check if serializable
                    log_data[key] = value
                except (TypeError, ValueError):
                    log_data[key] = str(value)
        
        return json.dumps(log_data)


class TextFormatter(logging.Formatter):
    """
    Human-readable text formatter for development.
    
    Colored output with timestamp and context.
    """
    
    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as colored text.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        level = record.levelname
        color = self.COLORS.get(level, self.RESET)
        
        # Build base message
        message = f"{timestamp} | {color}{level}{self.RESET} | {record.name} | {record.getMessage()}"
        
        # Add extra context
        extra_context = []
        for key, value in record.__dict__.items():
            if key not in [
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "exc_info", "exc_text", "thread", "threadName",
                "message", "asctime",
            ]:
                extra_context.append(f"{key}={value}")
        
        if extra_context:
            message += f" | {' '.join(extra_context)}"
        
        # Add exception info
        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)
        
        return message


# ============================================================================
# Error Tracker
# ============================================================================

class ErrorTracker:
    """
    Tracks and logs errors with context.
    
    Usage:
        error_tracker = ErrorTracker(logger)
        error_tracker.record_error(exc, context={"ticket_id": "xxx"})
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._error_counts: Dict[str, int] = {}
    
    def record_error(
        self,
        exc: Exception,
        context: Optional[Dict[str, Any]] = None,
        level: int = logging.ERROR,
    ) -> None:
        """
        Record an error with context.
        
        Args:
            exc: Exception instance
            context: Additional context dict
            level: Log level
        """
        error_type = type(exc).__name__
        error_key = f"{error_type}:{str(exc)[:50]}"
        
        # Track error count
        self._error_counts[error_key] = self._error_counts.get(error_key, 0) + 1
        count = self._error_counts[error_key]
        
        # Build log context
        log_context = {
            "error_type": error_type,
            "error_message": str(exc),
            "occurrence_count": count,
        }
        
        if context:
            log_context.update(context)
        
        self.logger.log(level, f"Error: {exc}", extra=log_context, exc_info=True)
    
    def get_error_summary(self) -> Dict[str, int]:
        """
        Get summary of error counts.
        """
        return self._error_counts.copy()
    
    def reset_counts(self) -> None:
        """
        Reset error counts.
        """
        self._error_counts.clear()


# ============================================================================
# Performance Logger
# ============================================================================

class PerformanceLogger:
    """
    Logs performance metrics for operations.
    
    Usage:
        perf = PerformanceLogger(logger)
        with perf.track("process_message", {"ticket_id": "xxx"}):
            # ... operation ...
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._start_time: Optional[float] = None
        self._operation: Optional[str] = None
        self._context: Dict[str, Any] = {}
    
    def track(
        self,
        operation: str,
        context: Optional[Dict[str, Any]] = None,
        threshold_ms: int = 1000,
    ) -> "PerformanceLogger":
        """
        Start tracking an operation.
        
        Args:
            operation: Operation name
            context: Additional context
            threshold_ms: Log warning if operation exceeds this
            
        Returns:
            self for context manager usage
        """
        self._operation = operation
        self._context = context or {}
        self._threshold_ms = threshold_ms
        return self
    
    def __enter__(self) -> "PerformanceLogger":
        """Start timing."""
        import time
        self._start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """End timing and log result."""
        import time
        
        duration_ms = int((time.time() - self._start_time) * 1000)
        
        log_context = {
            "operation": self._operation,
            "duration_ms": duration_ms,
            **self._context,
        }
        
        if exc_type:
            log_context["error"] = str(exc_val)
            self.logger.error(
                f"Operation failed: {self._operation}",
                extra=log_context,
            )
        elif duration_ms > self._threshold_ms:
            self.logger.warning(
                f"Slow operation: {self._operation} ({duration_ms}ms)",
                extra=log_context,
            )
        else:
            self.logger.debug(
                f"Operation completed: {self._operation} ({duration_ms}ms)",
                extra=log_context,
            )


# ============================================================================
# Setup Functions
# ============================================================================

def setup_logging(
    level: Optional[str] = None,
    log_format: Optional[str] = None,
    log_file: Optional[str] = None,
) -> None:
    """
    Configure application logging.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_format: Format type (json, text)
        log_file: Optional file path for log output
    """
    level = level or settings.log_level
    log_format = log_format or settings.log_format
    
    # Determine formatter
    if log_format.lower() == "json":
        formatter = StructuredFormatter()
    else:
        formatter = TextFormatter()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(StructuredFormatter())  # Always JSON for files
        root_logger.addHandler(file_handler)
    
    # Set levels for noisy libraries
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("aiokafka").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    # Suppress SQLAlchemy query logging (development optimization)
    # Set to ERROR to only show actual errors, not queries
    logging.getLogger("sqlalchemy.engine").setLevel(logging.ERROR)
    logging.getLogger("sqlalchemy.dialects").setLevel(logging.ERROR)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.ERROR)
    
    # Suppress uvicorn.access for cleaner terminal (show only warnings/errors)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    # Suppress alembic (database migrations)
    logging.getLogger("alembic").setLevel(logging.WARNING)
    
    # Log startup info
    logging.getLogger(__name__).info(
        f"Logging configured: level={level}, format={log_format}"
    )


def get_logger(
    name: str,
    with_error_tracker: bool = False,
    with_perf_logger: bool = False,
) -> logging.Logger:
    """
    Get a logger with optional extensions.
    
    Args:
        name: Logger name (usually __name__)
        with_error_tracker: Include error tracker
        with_perf_logger: Include performance logger
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    
    # Attach extensions as attributes
    if with_error_tracker:
        logger.error_tracker = ErrorTracker(logger)  # type: ignore
    
    if with_perf_logger:
        logger.perf = PerformanceLogger(logger)  # type: ignore
    
    return logger


# ============================================================================
# Context Manager for Logging
# ============================================================================

class logging_context:
    """
    Context manager for adding temporary context to logs.
    
    Usage:
        with logging_context(request_id="xxx", user_id="yyy"):
            logger.info("Processing request")
    """
    
    def __init__(self, **context):
        self.context = context
        self.old_context = {}
    
    def __enter__(self):
        # Store current context
        import logging
        current = getattr(logging, "_context", {})
        self.old_context = current.copy()
        
        # Add new context
        logging._context = {**current, **self.context}  # type: ignore
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore previous context
        import logging
        logging._context = self.old_context  # type: ignore


# ============================================================================
# Health Check Logging
# ============================================================================

def log_health_check(
    component: str,
    status: str,
    latency_ms: Optional[int] = None,
    error: Optional[str] = None,
) -> None:
    """
    Log a health check result.
    
    Args:
        component: Component name (database, kafka, etc.)
        status: Status (healthy, unhealthy, degraded)
        latency_ms: Optional latency
        error: Optional error message
    """
    logger = logging.getLogger("health")
    
    extra = {
        "component": component,
        "status": status,
        "health_check": True,
    }
    
    if latency_ms is not None:
        extra["latency_ms"] = latency_ms
    
    if error:
        extra["error"] = error
    
    if status == "healthy":
        logger.info(f"Health check: {component} is {status}", extra=extra)
    else:
        logger.warning(f"Health check: {component} is {status}", extra=extra)

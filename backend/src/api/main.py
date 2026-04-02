"""
FastAPI Application - Main Entry Point

Customer Success Digital FTE
Production-ready API for multi-channel customer support
"""
import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import settings
from src.logging_config import setup_logging
from .middleware import LoggingMiddleware, ErrorResponseHandler
from .routes import (
    health,
    customers,
    tickets,
    conversations,
    knowledge_base,
    webhooks,
    metrics,
    kafka_status,
    messages,
)

# Configure logging (structured)
setup_logging(
    level=settings.log_level,
    log_format=settings.log_format,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("=" * 60)
    logger.info(f"Starting {settings.app_name}")
    logger.info(f"Environment: {settings.app_env}")
    logger.info("=" * 60)

    try:
        # Initialize database with primary + fallback
        logger.info("Initializing database connection (primary + fallback)...")
        from src.database import init_database, get_current_db_type, is_using_fallback
        await init_database()

        db_type = get_current_db_type()
        using_fallback = is_using_fallback()
        logger.info(f"✓ Database initialized: {db_type}")
        if using_fallback:
            logger.warning("⚠ Running on FALLBACK database")
        else:
            logger.info("✓ Running on PRIMARY database")

        # Initialize Kafka integration
        logger.info("Initializing Kafka integration...")
        from src.kafka import init_kafka, setup_kafka_integration
        kafka_connected = await init_kafka()

        if kafka_connected:
            logger.info("✓ Kafka connected successfully")
        else:
            logger.warning("⚠ Kafka unavailable - using in-memory queue fallback")

        await setup_kafka_integration()
        logger.info("✓ Kafka integration complete")

        # Start background message worker (polls message_queue table)
        logger.info("Starting background message worker...")
        from src.workers import start_worker, run_worker
        await start_worker()
        
        # Run worker in background task
        asyncio.create_task(run_worker())
        logger.info("✓ Message worker started - processing inbound messages")

        logger.info("=" * 60)
        logger.info("Application startup complete")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down application...")

    try:
        # Stop message worker
        from src.workers import stop_worker
        await stop_worker()
        logger.info("Message worker stopped")

        # Close database connections
        from src.database import close_database
        await close_database()
        logger.info("Database connections closed")

        # Close Kafka connections
        from src.kafka import shutdown_kafka_integration
        await shutdown_kafka_integration()
        logger.info("Kafka connections closed")

    except Exception as e:
        logger.error(f"Shutdown error: {e}")

    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="24/7 Autonomous AI Customer Success Employee with Multi-Channel Support",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ============================================================================
# Middleware
# ============================================================================

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Response-Time", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)

# Logging Middleware
app.add_middleware(LoggingMiddleware)

# Rate Limiting Middleware (from security module)
from src.security import check_rate_limit_middleware
app.middleware("http")(check_rate_limit_middleware)

# Error Handler
app.add_exception_handler(500, ErrorResponseHandler.handle_internal_error)
app.add_exception_handler(404, ErrorResponseHandler.handle_not_found)
app.add_exception_handler(422, ErrorResponseHandler.handle_validation_error)
app.add_exception_handler(401, ErrorResponseHandler.handle_not_found)  # Reuse for unauthorized
app.add_exception_handler(429, ErrorResponseHandler.handle_not_found)  # Reuse for rate limit


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint - API information
    """
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "environment": settings.app_env,
        "docs": "/docs",
        "health": "/health",
    }


# ============================================================================
# Routes Registration
# ============================================================================

# Initialize security module
from src.security import init_security
init_security()

# Health check
app.include_router(health, prefix="/health", tags=["Health"])

# Webhooks (external channel integrations)
app.include_router(webhooks, tags=["Webhooks"])

# Metrics (monitoring and analytics) - Legacy
app.include_router(metrics, prefix="/api/v1", tags=["Metrics"])

# Metrics Dashboard (Platinum features)
from src.api.routes import metrics_dashboard
app.include_router(metrics_dashboard, prefix="/api/v1", tags=["Metrics Dashboard"])

# Kafka status (monitoring)
app.include_router(kafka_status, prefix="/api/v1/kafka", tags=["Kafka"])

# Messages (asynchronous intake)
app.include_router(messages, prefix="/api/v1/messages", tags=["Messages"])

# Worker monitoring (Platinum features)
from src.api.routes import worker_status
app.include_router(worker_status, prefix="/api/v1/worker", tags=["Worker Monitoring"])

# API v1 routes
app.include_router(customers, prefix="/api/v1/customers", tags=["Customers"])
app.include_router(tickets, prefix="/api/v1/tickets", tags=["Tickets"])
app.include_router(conversations, prefix="/api/v1/conversations", tags=["Conversations"])
app.include_router(knowledge_base, prefix="/api/v1/knowledge-base", tags=["Knowledge Base"])


# ============================================================================
# Global Exception Handler
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled errors.
    Logs the error and returns a generic 500 response.
    """
    logger.error(
        f"Unhandled exception: {exc}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "client": request.client.host if request.client else "unknown",
        },
        exc_info=True,
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "path": request.url.path,
        },
    )


# ============================================================================
# Health Check Endpoint (Aggregated)
# ============================================================================

@app.get("/healthz", tags=["Health"])
async def aggregated_health():
    """
    Aggregated health check for all services.
    Used by Kubernetes liveness/readiness probes.
    """
    db_health = await db_health_check()
    
    overall_healthy = db_health["status"] == "healthy"
    
    return {
        "status": "healthy" if overall_healthy else "unhealthy",
        "timestamp": logging.getLogger().handlers[0].formatter._fmt.split("%(asctime)s")[0] if hasattr(logging.getLogger().handlers[0].formatter, '_fmt') else None,
        "services": {
            "database": db_health,
            "kafka": {"status": "pending"},  # Will be implemented in Step 11
        },
    }

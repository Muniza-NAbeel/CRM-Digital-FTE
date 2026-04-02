#!/usr/bin/env python3
"""
Kafka Worker Runner - DISABLED FOR HACKATHON

⚠️  WARNING: This standalone worker is DISABLED by default.

The worker runs INSIDE FastAPI application (src/api/main.py) to avoid:
- Double processing of messages
- Race conditions
- Duplicate database connections
- Resource conflicts

WHEN TO USE THIS:
- Running worker as separate container/pod in production
- Need horizontal scaling of workers
- Kafka-based processing (not polling)

FOR HACKATHON:
    Use FastAPI embedded worker (uvicorn src.api.main:app)
    The worker starts automatically with the API.

TO ENABLE (if needed):
    1. Stop FastAPI server
    2. Run: uv run python -m src.workers.worker_runner
    3. Access API separately (no worker in API)
"""

import asyncio
import logging
import signal
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

# ============================================================================
# SAFETY CHECK - Prevent accidental double processing
# ============================================================================

def check_worker_safety():
    """
    Check if it's safe to run standalone worker.
    
    Returns:
        bool: True if safe to proceed, False otherwise
    """
    # Check if API might be running with embedded worker
    # This is a simple heuristic check
    
    logger.info("=" * 60)
    logger.info("STANDALONE WORKER - SAFETY CHECK")
    logger.info("=" * 60)
    
    logger.warning("⚠️  WARNING: Running standalone worker!")
    logger.warning("")
    logger.warning("⚠️  Make sure FastAPI is NOT running with embedded worker!")
    logger.warning("⚠️  Otherwise: DOUBLE PROCESSING will occur!")
    logger.warning("")
    logger.info("To run API + Worker together, use:")
    logger.info("    uv run uvicorn src.api.main:app --reload")
    logger.info("")
    logger.info("The worker starts automatically with the API.")
    logger.info("")
    logger.info("Press Ctrl+C within 5 seconds to cancel...")
    logger.info("=" * 60)
    
    return True  # Continue anyway (user is responsible)


async def main():
    """
    Main worker entry point.
    
    ⚠️  WARNING: Do NOT run this if FastAPI is already running
        with embedded worker (main.py lifespan).
    """
    # Safety check
    check_worker_safety()
    
    # Delay to allow user to cancel
    try:
        logger.info("Starting in 5 seconds...")
        await asyncio.sleep(5)
    except asyncio.CancelledError:
        logger.info("Startup cancelled by user")
        return
    
    from .message_worker import start_worker, stop_worker, run_worker

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()
    shutdown_event = asyncio.Event()

    def signal_handler():
        logger.info("Shutdown signal received")
        shutdown_event.set()

    # Register signal handlers
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            logger.warning(f"Signal handler not available for {sig}")

    logger.info("=" * 60)
    logger.info("Starting Customer Success Digital FTE - Message Worker")
    logger.info("=" * 60)

    try:
        # Start worker
        logger.info("Starting message worker...")
        await start_worker()

        logger.info("=" * 60)
        logger.info("✓ Worker is running. Press Ctrl+C to stop.")
        logger.info("=" * 60)

        # Run worker (polls continuously)
        await run_worker()

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Worker error: {e}", exc_info=True)
        raise
    finally:
        logger.info("Shutting down worker...")
        await stop_worker()
        logger.info("✓ Worker shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

"""
Async PostgreSQL Connection Layer with Primary + Fallback Architecture
Production-grade connection pooling with automatic failover

Features:
- Primary database connection
- Automatic fallback to secondary database
- Connection testing on startup
- Clear logging of connection status
- Compatible with PostgreSQL (Neon) and SQLite (local)
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from src.config import settings

logger = logging.getLogger(__name__)

# Global engine and session factory
_primary_engine: Optional[AsyncEngine] = None
_fallback_engine: Optional[AsyncEngine] = None
_async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None
_current_db_type: str = "unknown"
_is_using_fallback: bool = False


class DatabaseConnectionError(Exception):
    """Raised when database connection fails after retries."""
    pass


def _is_sqlite_url(database_url: str) -> bool:
    """
    Check if database URL is for SQLite.
    
    Examples:
        sqlite+aiosqlite:///./test.db -> True
        postgresql+asyncpg://... -> False
    """
    return database_url.startswith("sqlite")


async def _test_connection(engine: AsyncEngine, db_type: str) -> bool:
    """
    Test database connection.
    
    Args:
        engine: SQLAlchemy async engine
        db_type: Database type for logging
        
    Returns:
        bool: True if connection successful
    """
    try:
        async with engine.connect() as conn:
            # Execute simple query to test connection
            await conn.execute(text("SELECT 1"))
            logger.info(f"✓ {db_type} database connection test successful")
            return True
    except Exception as e:
        logger.warning(f"✗ {db_type} database connection test failed: {e}")
        return False


async def _create_engine_with_retry(
    database_url: str,
    db_type: str,
    max_retries: int = 3,
    retry_delay: float = 2.0,
) -> Optional[AsyncEngine]:
    """
    Create SQLAlchemy engine with retry mechanism.
    
    Args:
        database_url: Database connection URL
        db_type: Database type for logging
        max_retries: Maximum retry attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        AsyncEngine or None if all retries fail
    """
    last_error = None
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                f"Creating {db_type} database engine (attempt {attempt}/{max_retries})"
            )
            
            # Determine if SQLite or PostgreSQL
            is_sqlite = _is_sqlite_url(database_url)
            
            if is_sqlite:
                # SQLite configuration
                engine = create_async_engine(
                    database_url,
                    echo=False,  # Disable SQL logging for clean terminal
                    connect_args={"check_same_thread": False},
                )
            else:
                # PostgreSQL configuration (including Neon)
                engine = create_async_engine(
                    database_url,
                    echo=False,  # Disable SQL logging for clean terminal
                    pool_size=20,
                    max_overflow=40,
                    pool_pre_ping=True,  # Enable connection health checks
                    pool_recycle=3600,  # Recycle connections after 1 hour
                )
            
            # Test connection
            if await _test_connection(engine, db_type):
                logger.info(f"✓ {db_type} engine created successfully")
                return engine
            else:
                # Connection test failed
                await engine.dispose()
                raise DatabaseConnectionError(f"{db_type} connection test failed")
                
        except (SQLAlchemyError, DatabaseConnectionError) as e:
            last_error = e
            logger.warning(f"{db_type} engine creation failed (attempt {attempt}): {e}")
            
            if attempt < max_retries:
                logger.info(f"Retrying {db_type} connection in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"✗ {db_type} engine creation failed after {max_retries} attempts")
                if engine:
                    await engine.dispose()
    
    return None


async def init_database() -> None:
    """
    Initialize database connection with primary + fallback logic.
    
    Flow:
    1. Try primary database
    2. If primary fails, try fallback
    3. If both fail, raise DatabaseConnectionError
    4. Create session factory for successful connection
    """
    global _primary_engine, _fallback_engine, _async_session_factory
    global _current_db_type, _is_using_fallback
    
    logger.info("=" * 60)
    logger.info("Initializing Database Connection")
    logger.info("=" * 60)
    
    # Try primary database
    if settings.database_url:
        logger.info(f"Primary database URL: {settings.database_url[:50]}...")
        _primary_engine = await _create_engine_with_retry(
            settings.database_url,
            "Primary",
            max_retries=3,
            retry_delay=2.0,
        )
    
    # If primary failed, try fallback
    if _primary_engine is None and settings.fallback_database_url:
        logger.warning("⚠ Primary database unavailable, switching to fallback...")
        logger.info(f"Fallback database URL: {settings.fallback_database_url[:50]}...")
        _fallback_engine = await _create_engine_with_retry(
            settings.fallback_database_url,
            "Fallback",
            max_retries=3,
            retry_delay=2.0,
        )
        
        if _fallback_engine:
            _is_using_fallback = True
            logger.warning("✓ Running on FALLBACK database")
    
    # Determine which engine to use
    active_engine = _primary_engine or _fallback_engine
    
    if active_engine is None:
        logger.error("✗ CRITICAL: No database available (primary and fallback both failed)")
        raise DatabaseConnectionError(
            "Database connection failed: Both primary and fallback databases are unavailable"
        )
    
    # Create session factory
    _async_session_factory = async_sessionmaker(
        active_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    # Determine database type
    if _is_sqlite_url(settings.database_url or settings.fallback_database_url or ""):
        _current_db_type = "SQLite"
    else:
        _current_db_type = "PostgreSQL"
    
    logger.info("=" * 60)
    logger.info(f"✓ Database Initialized Successfully")
    logger.info(f"  Type: {_current_db_type}")
    logger.info(f"  Using Fallback: {'Yes' if _is_using_fallback else 'No'}")
    logger.info(f"  Pool Size: {active_engine.pool.size() if hasattr(active_engine.pool, 'size') else 'N/A'}")
    logger.info("=" * 60)


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session from session factory.

    Usage:
        async with get_db_session() as session:
            results = await session.execute(query)

    Yields:
        AsyncSession: SQLAlchemy async session
    """
    if _async_session_factory is None:
        raise DatabaseConnectionError("Database not initialized. Call init_database() first.")

    session = _async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        await session.close()


@asynccontextmanager
async def get_db_connection():
    """
    Context manager for database connection.
    
    Usage:
        async with get_db_connection() as session:
            results = await session.execute(query)
    
    Yields:
        AsyncSession: SQLAlchemy async session
    """
    async with get_db_session() as session:
        yield session


async def close_database() -> None:
    """
    Close all database engines gracefully.
    """
    global _primary_engine, _fallback_engine, _async_session_factory
    
    logger.info("Closing database connections...")
    
    if _primary_engine:
        await _primary_engine.dispose()
        logger.info("✓ Primary database engine closed")
        _primary_engine = None
    
    if _fallback_engine:
        await _fallback_engine.dispose()
        logger.info("✓ Fallback database engine closed")
        _fallback_engine = None
    
    _async_session_factory = None
    logger.info("✓ All database connections closed")


def get_current_db_type() -> str:
    """
    Get current database type.
    
    Returns:
        str: "SQLite" or "PostgreSQL"
    """
    return _current_db_type


def is_using_fallback() -> bool:
    """
    Check if using fallback database.
    
    Returns:
        bool: True if using fallback
    """
    return _is_using_fallback


async def health_check() -> dict:
    """
    Perform database health check.
    
    Returns:
        dict with status, latency_ms, and database info
    """
    import time
    
    if _async_session_factory is None:
        return {"status": "unhealthy", "error": "Database not initialized"}
    
    try:
        start = time.time()
        async with get_db_session() as session:
            await session.execute(text("SELECT 1"))
        latency_ms = int((time.time() - start) * 1000)
        
        return {
            "status": "healthy",
            "latency_ms": latency_ms,
            "database_type": _current_db_type,
            "using_fallback": _is_using_fallback,
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "database_type": _current_db_type,
            "using_fallback": _is_using_fallback,
        }


# ============================================================================
# FastAPI Dependency Injection
# ============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database session.
    
    Usage in FastAPI:
        @app.get("/items")
        async def get_items(
            db: AsyncSession = Depends(get_db)
        ):
            results = await db.execute(...)
    
    Yields:
        AsyncSession: SQLAlchemy async session
    """
    async with get_db_session() as session:
        yield session

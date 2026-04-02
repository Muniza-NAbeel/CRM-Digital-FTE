"""
Dependency Injection for FastAPI application.

Provides reusable dependencies for:
- Database connections
- Configuration access
- Authentication (future)
- Pagination
"""

from typing import AsyncGenerator, Optional
from functools import lru_cache

from fastapi import Depends, Header, Query

from src.database import get_db, get_connection
from src.config import Settings, get_settings


# ============================================================================
# Database Dependencies
# ============================================================================

async def get_db_connection() -> AsyncGenerator:
    """
    Get database connection for request scope.
    
    Usage:
        @app.get("/items")
        async def get_items(db = Depends(get_db_connection)):
            async with db as session:
                result = await session.execute(...)
    """
    async with get_connection() as conn:
        yield conn


async def get_db_pool_dependency():
    """
    Get database session factory (for background tasks, workers).
    
    Usage:
        async def background_task(db = Depends(get_db_pool_dependency)):
            async with get_db_connection() as conn:
                ...
    """
    # Return a marker that database is initialized
    # Actual connections use get_db_connection()
    return "initialized"


# ============================================================================
# Configuration Dependencies
# ============================================================================

def get_config() -> Settings:
    """
    Get application configuration.
    
    Usage:
        @app.get("/config")
        async def get_config_info(config: Settings = Depends(get_config)):
            return {"app_name": config.app_name}
    """
    return get_settings()


# ============================================================================
# Pagination Dependencies
# ============================================================================

class PaginationParams:
    """
    Standard pagination parameters.
    """
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    ):
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size


async def get_pagination(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginationParams:
    """
    Get pagination parameters.
    
    Usage:
        @app.get("/items")
        async def get_items(pagination: PaginationParams = Depends(get_pagination)):
            offset = pagination.offset
            limit = pagination.page_size
    """
    return PaginationParams(page=page, page_size=page_size)


# ============================================================================
# Request ID Dependency
# ============================================================================

async def get_request_id(
    x_request_id: Optional[str] = Header(None),
) -> str:
    """
    Get or generate request ID from headers.
    
    Usage:
        @app.get("/items")
        async def get_items(request_id: str = Depends(get_request_id)):
            logger.info(f"Processing request {request_id}")
    """
    import uuid
    return x_request_id or str(uuid.uuid4())


# ============================================================================
# Channel Validation Dependency
# ============================================================================

from typing import Literal

ChannelType = Literal["web_form", "gmail", "whatsapp"]

async def validate_channel(
    channel: ChannelType = Query(..., description="Channel type"),
) -> ChannelType:
    """
    Validate channel type parameter.
    
    Usage:
        @app.post("/messages")
        async def create_message(channel: ChannelType = Depends(validate_channel)):
            ...
    """
    return channel

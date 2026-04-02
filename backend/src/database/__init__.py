"""
Database module for Customer Success Digital FTE.
SQLAlchemy async with primary + fallback architecture.

Note: For backward compatibility, old asyncpg-based functions are still available
but will be deprecated in future versions. Migrate to SQLAlchemy AsyncSession.
"""

from .connection import (
    init_database,
    get_db_session,
    get_db_connection,
    close_database,
    health_check,
    get_db,
    get_current_db_type,
    is_using_fallback,
    DatabaseConnectionError,
)

# Backward compatibility aliases
get_connection = get_db_connection  # Alias for backward compatibility

# Deprecated but still available for backward compatibility
# These will be removed in future versions
get_db_pool = init_database  # Deprecated: use init_database instead
close_db_pool = close_database  # Deprecated: use close_database instead

__all__ = [
    # New SQLAlchemy-based functions
    "init_database",
    "get_db_session",
    "get_db_connection",
    "get_connection",  # Alias for backward compatibility
    "close_database",
    "health_check",
    "get_db",
    "get_current_db_type",
    "is_using_fallback",
    "DatabaseConnectionError",
    # Deprecated asyncpg-based functions (for backward compatibility)
    "get_db_pool",
    "close_db_pool",
]

"""
Security Module - Authentication and Rate Limiting

Features:
- API Key authentication
- JWT token authentication (optional)
- Rate limiting per API key
- Request signing
"""

import hashlib
import hmac
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple, Any
from functools import wraps

from fastapi import Request, HTTPException, status, Depends
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from src.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# API Key Configuration
# ============================================================================

# In production, these should be stored in a database
# For now, using environment variable with multiple keys support
API_KEYS_HEADER = "X-API-Key"

# Pre-configured API keys (in production, load from database)
# Format: {api_key: {"name": str, "tier": str, "rate_limit": int}}
CONFIGURED_API_KEYS = {}


def load_api_keys():
    """Load API keys from environment variable."""
    global CONFIGURED_API_KEYS
    
    # Parse APP_API_KEYS environment variable
    # Format: "key1:name1:tier1:limit1,key2:name2:tier2:limit2"
    api_keys_str = settings.api_keys if hasattr(settings, 'api_keys') else ""
    
    if not api_keys_str:
        # Default development key
        CONFIGURED_API_KEYS = {
            "dev-api-key-12345": {
                "name": "Development Key",
                "tier": "standard",
                "rate_limit": 100,
                "created_at": datetime.now(timezone.utc),
            }
        }
        logger.info("Using default development API key")
        return
    
    keys = api_keys_str.split(",")
    for key_data in keys:
        parts = key_data.strip().split(":")
        if len(parts) >= 4:
            key, name, tier, limit = parts[0], parts[1], parts[2], int(parts[3])
            CONFIGURED_API_KEYS[key] = {
                "name": name,
                "tier": tier,
                "rate_limit": limit,
                "created_at": datetime.now(timezone.utc),
            }
    
    logger.info(f"Loaded {len(CONFIGURED_API_KEYS)} API keys")


# Rate limiting storage (in production, use Redis)
# Format: {api_key: [(timestamp, count)]}
_rate_limit_store: Dict[str, list] = defaultdict(list)


# ============================================================================
# Authentication Dependencies
# ============================================================================

api_key_header = APIKeyHeader(name=API_KEYS_HEADER, auto_error=False)
http_bearer = HTTPBearer(auto_error=False)


class APIKeyInfo(BaseModel):
    """API Key information."""
    key: str
    name: str
    tier: str
    rate_limit: int
    authenticated: bool = True


class AuthenticationError(Exception):
    """Authentication failed."""
    pass


class RateLimitExceeded(Exception):
    """Rate limit exceeded."""
    pass


def verify_api_key(api_key: str) -> Optional[APIKeyInfo]:
    """
    Verify API key and return key info.
    
    Args:
        api_key: API key from request header
        
    Returns:
        APIKeyInfo if valid, None otherwise
    """
    if not api_key:
        return None
    
    key_info = CONFIGURED_API_KEYS.get(api_key)
    if not key_info:
        return None
    
    return APIKeyInfo(
        key=api_key,
        name=key_info["name"],
        tier=key_info["tier"],
        rate_limit=key_info["rate_limit"],
    )


def check_rate_limit(api_key: str, limit: int, window_seconds: int = 60) -> Tuple[bool, Dict]:
    """
    Check if request is within rate limit.
    
    Uses sliding window algorithm.
    
    Args:
        api_key: API key making the request
        limit: Maximum requests per window
        window_seconds: Time window in seconds (default: 60)
        
    Returns:
        Tuple of (allowed: bool, info: dict)
    """
    now = time.time()
    window_start = now - window_seconds
    
    # Clean old entries
    _rate_limit_store[api_key] = [
        ts for ts in _rate_limit_store[api_key]
        if ts > window_start
    ]
    
    current_count = len(_rate_limit_store[api_key])
    
    info = {
        "current_count": current_count,
        "limit": limit,
        "window_seconds": window_seconds,
        "remaining": max(0, limit - current_count),
        "reset_at": datetime.fromtimestamp(
            _rate_limit_store[api_key][0] + window_seconds if _rate_limit_store[api_key] else now + window_seconds,
            tz=timezone.utc
        ).isoformat() if _rate_limit_store[api_key] else None,
    }
    
    if current_count >= limit:
        return False, info
    
    # Record this request
    _rate_limit_store[api_key].append(now)
    info["remaining"] = limit - current_count - 1
    
    return True, info


async def authenticate_request(
    request: Request,
    api_key: Optional[str] = Depends(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
) -> APIKeyInfo:
    """
    Authenticate incoming request.
    
    Supports:
    - API Key via X-API-Key header
    - Bearer token (JWT) via Authorization header
    
    Args:
        request: FastAPI request object
        api_key: API key from header
        bearer: Bearer token credentials
        
    Returns:
        APIKeyInfo if authenticated
        
    Raises:
        HTTPException: If authentication fails
    """
    # Try API Key authentication first
    if api_key:
        key_info = verify_api_key(api_key)
        if key_info:
            logger.info(
                f"Authenticated via API Key: {key_info.name}",
                extra={
                    "api_key_name": key_info.name,
                    "api_key_tier": key_info.tier,
                    "client": request.client.host if request.client else "unknown",
                }
            )
            request.state.api_key = key_info.key
            request.state.auth_tier = key_info.tier
            return key_info
    
    # Try Bearer token authentication
    if bearer and bearer.credentials:
        token = bearer.credentials
        # For now, treat bearer token as API key (can be extended to JWT)
        key_info = verify_api_key(token)
        if key_info:
            logger.info(
                f"Authenticated via Bearer token: {key_info.name}",
                extra={
                    "api_key_name": key_info.name,
                    "client": request.client.host if request.client else "unknown",
                }
            )
            request.state.api_key = key_info.key
            request.state.auth_tier = key_info.tier
            return key_info
    
    # Authentication failed
    logger.warning(
        f"Authentication failed from {request.client.host if request.client else 'unknown'}",
        extra={
            "path": request.url.path,
            "method": request.method,
        }
    )
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "error": "unauthorized",
            "message": "Valid API key or Bearer token required",
            "hint": f"Include header: {API_KEYS_HEADER}: your-api-key",
        },
        headers={"WWW-Authenticate": "ApiKey or Bearer"},
    )


async def check_rate_limit_middleware(
    request: Request,
    call_next,
):
    """
    Rate limiting middleware.
    
    Applies rate limiting based on API key tier.
    """
    # Skip rate limiting for non-authenticated endpoints
    if not hasattr(request.state, 'api_key'):
        return await call_next(request)
    
    api_key = request.state.api_key
    key_info = CONFIGURED_API_KEYS.get(api_key)
    
    if not key_info:
        return await call_next(request)
    
    # Get rate limit based on tier
    tier_limits = {
        "free": 30,  # 30 requests per minute
        "standard": 100,  # 100 requests per minute
        "premium": 500,  # 500 requests per minute
        "enterprise": 2000,  # 2000 requests per minute
    }
    
    limit = tier_limits.get(key_info["tier"], key_info["rate_limit"])
    
    allowed, rate_info = check_rate_limit(api_key, limit)
    
    # Add rate limit headers to response
    request.state.rate_limit_info = rate_info
    
    if not allowed:
        logger.warning(
            f"Rate limit exceeded for API key: {key_info['name']}",
            extra={
                "api_key_name": key_info["name"],
                "current_count": rate_info["current_count"],
                "limit": limit,
            }
        )
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "message": f"Rate limit of {limit} requests per minute exceeded",
                "retry_after": rate_info["reset_at"],
            },
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": rate_info["reset_at"] or "",
                "Retry-After": str(int(float(rate_info["reset_at"]) - time.time()) if rate_info["reset_at"] else 60),
            },
        )
    
    response = await call_next(request)
    
    # Add rate limit headers to response
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
    if rate_info["reset_at"]:
        response.headers["X-RateLimit-Reset"] = rate_info["reset_at"]
    
    return response


# ============================================================================
# Optional Authentication Decorator
# ============================================================================

def optional_auth():
    """
    Decorator for endpoints with optional authentication.
    
    If API key is provided, it will be validated and rate limited.
    If no API key, request proceeds without authentication.
    """
    async def dependency(
        request: Request,
        api_key: Optional[str] = Depends(api_key_header),
    ) -> Optional[APIKeyInfo]:
        if api_key:
            key_info = verify_api_key(api_key)
            if key_info:
                request.state.api_key = key_info.key
                request.state.auth_tier = key_info.tier
                
                # Apply rate limiting
                allowed, rate_info = check_rate_limit(api_key, key_info.rate_limit)
                request.state.rate_limit_info = rate_info
                
                if not allowed:
                    raise HTTPException(
                        status_code=429,
                        detail={
                            "error": "rate_limit_exceeded",
                            "message": f"Rate limit exceeded",
                        },
                    )
                
                return key_info
        return None
    
    return Depends(dependency)


# ============================================================================
# Request Signing (for webhook verification)
# ============================================================================

def sign_request(payload: str, secret: str) -> str:
    """Sign request payload with HMAC-SHA256."""
    return hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def verify_signature(payload: str, signature: str, secret: str) -> bool:
    """Verify request signature."""
    expected = sign_request(payload, secret)
    return hmac.compare_digest(expected, signature)


# ============================================================================
# Initialize Security
# ============================================================================

def init_security():
    """Initialize security module."""
    load_api_keys()
    logger.info("Security module initialized")

    if settings.app_env == "development":
        logger.warning("⚠ Running in development mode with default API key")
        logger.warning("⚠ Change APP_API_KEYS in production!")


# ============================================================================
# Metrics Recording (for dashboard)
# ============================================================================

_metrics_cache: Dict[str, Any] = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "total_processing_time_ms": 0,
    "last_updated": None,
}


def record_request_metrics(duration_ms: float, success: bool):
    """Record request metrics for dashboard."""
    _metrics_cache["total_requests"] += 1
    if success:
        _metrics_cache["successful_requests"] += 1
    else:
        _metrics_cache["failed_requests"] += 1
    _metrics_cache["total_processing_time_ms"] += duration_ms
    _metrics_cache["last_updated"] = datetime.now(timezone.utc).isoformat()


def get_metrics_cache() -> Dict[str, Any]:
    """Get current metrics cache."""
    return _metrics_cache.copy()

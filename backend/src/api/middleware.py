"""
Middleware for FastAPI application.

Provides:
- Request/Response logging
- Error handling
- Request timing
- Request ID tracking
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

import logging

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging all HTTP requests and responses.
    
    Logs:
    - Request method, path, headers
    - Response status, time taken
    - Client IP
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start timing
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query": request.url.query,
                "client": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown"),
            },
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Add headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms}ms"
            
            # Log response
            logger.info(
                f"Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
            
            return response
            
        except Exception as e:
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log error
            logger.error(
                f"Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise


class ErrorResponseHandler:
    """
    Centralized error response handler.
    """
    
    @staticmethod
    async def handle_internal_error(request: Request, exc: Exception) -> JSONResponse:
        """
        Handle 500 Internal Server Error.
        """
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        
        logger.error(
            f"Internal server error",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "error": str(exc),
            },
            exc_info=True,
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": "An internal error occurred",
                "request_id": request_id,
            },
        )
    
    @staticmethod
    async def handle_not_found(request: Request, exc: Exception) -> JSONResponse:
        """
        Handle 404 Not Found.
        """
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        
        return JSONResponse(
            status_code=404,
            content={
                "error": "not_found",
                "message": "The requested resource was not found",
                "request_id": request_id,
            },
        )
    
    @staticmethod
    async def handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
        """
        Handle 422 Validation Error.
        """
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": "Request validation failed",
                "request_id": request_id,
                "details": str(exc),
            },
        )

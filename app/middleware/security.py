"""
Simplified security middleware for ImaniPay Blockchain Service.

This module provides basic security middleware without authentication,
focusing on rate limiting, request validation, and security headers.
"""

import logging
import time
import json
from datetime import datetime
from typing import Dict, Any, Optional
from collections import defaultdict, deque
from ipaddress import ip_address
import re

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SimplifiedSecurityMiddleware(BaseHTTPMiddleware):
    """Simplified security middleware without authentication."""
    
    def __init__(self, app):
        super().__init__(app)
        self.logger = logger
        
        # Basic rate limiting configuration
        self.rate_limits = {
            "default": {"requests": 1000, "window": 60},    # 1000 requests per minute
            "api": {"requests": 500, "window": 60},         # 500 API requests per minute
            "contracts": {"requests": 100, "window": 60}    # 100 contract requests per minute
        }
        
        # In-memory rate limiting storage
        self.rate_limit_storage = defaultdict(lambda: defaultdict(deque))
        
        # Security configuration
        self.blocked_ips = set()
        self.max_request_size = 10 * 1024 * 1024  # 10MB
        
        # Basic suspicious patterns
        self.suspicious_patterns = [
            r'<script[^>]*>.*?</script>',  # XSS
            r'union\s+select',             # SQL injection
            r'drop\s+table',               # SQL injection
            r'\.\./',                      # Path traversal
        ]
        
        # Security headers
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "SAMEORIGIN",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        }
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Main middleware dispatch method."""
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        
        try:
            # Basic security checks
            await self._check_ip_blocking(client_ip)
            await self._check_request_size(request)
            await self._check_suspicious_patterns(request)
            await self._check_rate_limiting(request, client_ip)
            
            # Process request
            response = await call_next(request)
            
            # Add security headers
            self._add_security_headers(response)
            
            # Log request (simplified)
            self._log_request(request, response, start_time, client_ip)
            
            return response
            
        except HTTPException as e:
            # Log security event
            self.logger.warning(f"Security event from {client_ip}: {e.detail}")
            
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": e.detail, 
                    "timestamp": datetime.utcnow().isoformat(),
                    "request_id": getattr(request.state, "request_id", None)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Security middleware error: {e}")
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error", 
                    "timestamp": datetime.utcnow().isoformat(),
                    "request_id": getattr(request.state, "request_id", None)
                }
            )
    
    # ========================================================================
    # Security Checks
    # ========================================================================
    
    async def _check_ip_blocking(self, client_ip: str) -> None:
        """Check if IP is blocked."""
        if client_ip in self.blocked_ips:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="IP address is blocked"
            )
    
    async def _check_request_size(self, request: Request) -> None:
        """Check request size limits."""
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Request too large"
            )
    
    async def _check_suspicious_patterns(self, request: Request) -> None:
        """Check for suspicious patterns in request."""
        # Check URL path
        path = str(request.url.path).lower()
        query = str(request.url.query).lower() if request.url.query else ""
        
        for pattern in self.suspicious_patterns:
            if re.search(pattern, path + query, re.IGNORECASE):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Suspicious request pattern detected"
                )
    
    async def _check_rate_limiting(self, request: Request, client_ip: str) -> None:
        """Check rate limiting."""
        # Determine rate limit category
        path = request.url.path
        if path.startswith("/api/v1/contracts"):
            category = "contracts"
        elif path.startswith("/api/"):
            category = "api"
        else:
            category = "default"
        
        limit_config = self.rate_limits[category]
        current_time = time.time()
        window_start = current_time - limit_config["window"]
        
        # Clean old requests
        requests = self.rate_limit_storage[client_ip][category]
        while requests and requests[0] < window_start:
            requests.popleft()
        
        # Check limit
        if len(requests) >= limit_config["requests"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: {limit_config['requests']} requests per {limit_config['window']} seconds"
            )
        
        # Add current request
        requests.append(current_time)
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        # Check for forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to client host
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _add_security_headers(self, response: Response) -> None:
        """Add security headers to response."""
        for header, value in self.security_headers.items():
            response.headers[header] = value
    
    def _log_request(
        self, 
        request: Request, 
        response: Response, 
        start_time: float, 
        client_ip: str
    ) -> None:
        """Log request (simplified)."""
        process_time = time.time() - start_time
        
        self.logger.info(
            f"{request.method} {request.url.path} "
            f"from {client_ip} -> {response.status_code} "
            f"in {process_time:.3f}s"
        )
    
    # ========================================================================
    # Admin Methods (for blocking IPs)
    # ========================================================================
    
    def block_ip(self, ip: str) -> None:
        """Block an IP address."""
        self.blocked_ips.add(ip)
        self.logger.warning(f"IP {ip} has been blocked")
    
    def unblock_ip(self, ip: str) -> None:
        """Unblock an IP address."""
        self.blocked_ips.discard(ip)
        self.logger.info(f"IP {ip} has been unblocked")
    
    def get_rate_limit_stats(self, client_ip: str) -> Dict[str, Any]:
        """Get rate limit statistics for an IP."""
        stats = {}
        current_time = time.time()
        
        for category, config in self.rate_limits.items():
            window_start = current_time - config["window"]
            requests = self.rate_limit_storage[client_ip][category]
            
            # Count requests in current window
            current_requests = sum(1 for req_time in requests if req_time >= window_start)
            
            stats[category] = {
                "current_requests": current_requests,
                "limit": config["requests"],
                "window_seconds": config["window"],
                "remaining": max(0, config["requests"] - current_requests)
            }
        
        return stats


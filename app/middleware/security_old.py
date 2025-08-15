"""
Security middleware for ImaniPay Blockchain Service.

This module provides comprehensive security middleware including rate limiting,
request validation, security headers, and threat detection.
"""

import logging
import time
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from collections import defaultdict, deque
from ipaddress import ip_address, ip_network
import re

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint
import redis.asyncio as redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware."""
    
    def __init__(self, app, redis_client: Optional[redis.Redis] = None):
        super().__init__(app)
        self.logger = logger
        self.redis_client = redis_client
        
        # Rate limiting configuration
        self.rate_limits = {
            "default": {"requests": 100, "window": 60},  # 100 requests per minute
            "auth": {"requests": 5, "window": 60},       # 5 auth requests per minute
            "api": {"requests": 1000, "window": 60},     # 1000 API requests per minute
            "payment": {"requests": 10, "window": 60}    # 10 payment requests per minute
        }
        
        # In-memory rate limiting (fallback)
        self.rate_limit_storage = defaultdict(lambda: defaultdict(deque))
        
        # Security configuration
        self.blocked_ips = set()
        self.allowed_origins = settings.security.allowed_origins
        self.max_request_size = 10 * 1024 * 1024  # 10MB
        self.suspicious_patterns = [
            r'<script[^>]*>.*?</script>',  # XSS
            r'union\s+select',             # SQL injection
            r'drop\s+table',               # SQL injection
            r'exec\s*\(',                  # Code injection
            r'eval\s*\(',                  # Code injection
            r'\.\./',                      # Path traversal
            r'<iframe[^>]*>',              # Iframe injection
        ]
        
        # Threat detection
        self.threat_scores = defaultdict(int)
        self.threat_threshold = 100
        
        # Security headers
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
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
            # Security checks
            await self._check_ip_blocking(client_ip)
            await self._check_request_size(request)
            await self._check_suspicious_patterns(request)
            await self._check_rate_limiting(request, client_ip)
            
            # Process request
            response = await call_next(request)
            
            # Add security headers
            self._add_security_headers(response)
            
            # Log request
            await self._log_request(request, response, start_time, client_ip)
            
            return response
            
        except HTTPException as e:
            # Log security event
            await self._log_security_event(request, client_ip, str(e.detail))
            
            # Increase threat score
            await self._increase_threat_score(client_ip, 10)
            
            return JSONResponse(
                status_code=e.status_code,
                content={"error": e.detail, "timestamp": datetime.utcnow().isoformat()}
            )
            
        except Exception as e:
            self.logger.error(f"Security middleware error: {e}")
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Internal server error", "timestamp": datetime.utcnow().isoformat()}
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
        
        # Check Redis for blocked IPs
        if self.redis_client:
            is_blocked = await self.redis_client.get(f"blocked_ip:{client_ip}")
            if is_blocked:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="IP address is temporarily blocked"
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
        # Check URL
        url_str = str(request.url)
        for pattern in self.suspicious_patterns:
            if re.search(pattern, url_str, re.IGNORECASE):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Suspicious request pattern detected"
                )
        
        # Check headers
        for header_name, header_value in request.headers.items():
            for pattern in self.suspicious_patterns:
                if re.search(pattern, header_value, re.IGNORECASE):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Suspicious header pattern detected"
                    )
        
        # Check query parameters
        for param_name, param_value in request.query_params.items():
            for pattern in self.suspicious_patterns:
                if re.search(pattern, param_value, re.IGNORECASE):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Suspicious query parameter detected"
                    )
    
    async def _check_rate_limiting(self, request: Request, client_ip: str) -> None:
        """Check rate limiting."""
        # Determine rate limit category
        path = request.url.path
        category = self._get_rate_limit_category(path)
        
        # Check rate limit
        if not await self._is_rate_limit_ok(client_ip, category):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
    
    # ========================================================================
    # Rate Limiting
    # ========================================================================
    
    def _get_rate_limit_category(self, path: str) -> str:
        """Determine rate limit category based on path."""
        if "/auth/" in path or "/login" in path or "/register" in path:
            return "auth"
        elif "/api/" in path:
            return "api"
        elif "/payment" in path or "/transaction" in path:
            return "payment"
        else:
            return "default"
    
    async def _is_rate_limit_ok(self, client_ip: str, category: str) -> bool:
        """Check if request is within rate limits."""
        rate_config = self.rate_limits.get(category, self.rate_limits["default"])
        max_requests = rate_config["requests"]
        window_seconds = rate_config["window"]
        
        if self.redis_client:
            return await self._check_redis_rate_limit(
                client_ip, category, max_requests, window_seconds
            )
        else:
            return self._check_memory_rate_limit(
                client_ip, category, max_requests, window_seconds
            )
    
    async def _check_redis_rate_limit(
        self, 
        client_ip: str, 
        category: str, 
        max_requests: int, 
        window_seconds: int
    ) -> bool:
        """Check rate limit using Redis."""
        key = f"rate_limit:{client_ip}:{category}"
        current_time = int(time.time())
        window_start = current_time - window_seconds
        
        # Use Redis sorted set for sliding window
        if self.redis_client is not None:
            pipe = self.redis_client.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiration
            pipe.expire(key, window_seconds)
            
            results = await pipe.execute()
            current_requests = results[1]
            
            return current_requests < max_requests
        else:
            # Fallback to memory-based rate limiting
            return self._check_memory_rate_limit(client_ip, category, max_requests, window_seconds)
    
    def _check_memory_rate_limit(
        self, 
        client_ip: str, 
        category: str, 
        max_requests: int, 
        window_seconds: int
    ) -> bool:
        """Check rate limit using in-memory storage."""
        current_time = time.time()
        window_start = current_time - window_seconds
        
        # Get request queue for this IP and category
        request_queue = self.rate_limit_storage[client_ip][category]
        
        # Remove old requests
        while request_queue and request_queue[0] < window_start:
            request_queue.popleft()
        
        # Check if under limit
        if len(request_queue) >= max_requests:
            return False
        
        # Add current request
        request_queue.append(current_time)
        
        return True
    
    # ========================================================================
    # Threat Detection
    # ========================================================================
    
    async def _increase_threat_score(self, client_ip: str, points: int) -> None:
        """Increase threat score for IP."""
        if self.redis_client:
            key = f"threat_score:{client_ip}"
            current_score = await self.redis_client.get(key)
            current_score = int(current_score) if current_score else 0
            
            new_score = current_score + points
            await self.redis_client.setex(key, 3600, new_score)  # 1 hour expiry
            
            # Block IP if threshold exceeded
            if new_score >= self.threat_threshold:
                await self._block_ip_temporarily(client_ip, 3600)  # Block for 1 hour
        else:
            self.threat_scores[client_ip] += points
            
            # Block IP if threshold exceeded
            if self.threat_scores[client_ip] >= self.threat_threshold:
                self.blocked_ips.add(client_ip)
    
    async def _block_ip_temporarily(self, client_ip: str, duration_seconds: int) -> None:
        """Block IP temporarily."""
        if self.redis_client:
            await self.redis_client.setex(f"blocked_ip:{client_ip}", duration_seconds, "1")
        else:
            self.blocked_ips.add(client_ip)
        
        self.logger.warning(f"IP {client_ip} blocked temporarily for {duration_seconds} seconds")
    
    # ========================================================================
    # Logging and Monitoring
    # ========================================================================
    
    async def _log_request(
        self, 
        request: Request, 
        response: Response, 
        start_time: float, 
        client_ip: str
    ) -> None:
        """Log request details."""
        duration = time.time() - start_time
        
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "client_ip": client_ip,
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
            "user_agent": request.headers.get("user-agent", ""),
            "referer": request.headers.get("referer", ""),
            "content_length": request.headers.get("content-length", "0")
        }
        
        # Log to Redis if available
        if self.redis_client:
            await self.redis_client.lpush(
                "request_logs", 
                json.dumps(log_data)
            )
            await self.redis_client.ltrim("request_logs", 0, 9999)  # Keep last 10k logs
        
        # Log suspicious requests
        if response.status_code >= 400:
            self.logger.warning(f"Suspicious request: {log_data}")
    
    async def _log_security_event(
        self, 
        request: Request, 
        client_ip: str, 
        event_detail: str
    ) -> None:
        """Log security event."""
        event_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "security_violation",
            "client_ip": client_ip,
            "method": request.method,
            "path": request.url.path,
            "detail": event_detail,
            "user_agent": request.headers.get("user-agent", ""),
            "headers": dict(request.headers)
        }
        
        # Log to Redis if available
        if self.redis_client:
            await self.redis_client.lpush(
                "security_events", 
                json.dumps(event_data)
            )
            await self.redis_client.ltrim("security_events", 0, 9999)  # Keep last 10k events
        
        self.logger.error(f"Security event: {event_data}")
    
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
        return request.client.host if request.client else "unknown"
    
    def _add_security_headers(self, response: Response) -> None:
        """Add security headers to response."""
        for header_name, header_value in self.security_headers.items():
            response.headers[header_name] = header_value
    
    # ========================================================================
    # Admin Methods
    # ========================================================================
    
    async def block_ip(self, ip_address: str, duration_seconds: int = 3600) -> None:
        """Block IP address."""
        await self._block_ip_temporarily(ip_address, duration_seconds)
    
    async def unblock_ip(self, ip_address: str) -> None:
        """Unblock IP address."""
        if self.redis_client:
            await self.redis_client.delete(f"blocked_ip:{ip_address}")
        
        if ip_address in self.blocked_ips:
            self.blocked_ips.remove(ip_address)
        
        self.logger.info(f"IP {ip_address} unblocked")
    
    async def get_rate_limit_status(self, client_ip: str) -> Dict[str, Any]:
        """Get rate limit status for IP."""
        status = {}
        
        for category, config in self.rate_limits.items():
            if self.redis_client:
                key = f"rate_limit:{client_ip}:{category}"
                current_requests = await self.redis_client.zcard(key)
            else:
                request_queue = self.rate_limit_storage[client_ip][category]
                current_time = time.time()
                window_start = current_time - config["window"]
                
                # Count valid requests
                current_requests = sum(
                    1 for req_time in request_queue 
                    if req_time >= window_start
                )
            
            status[category] = {
                "current_requests": current_requests,
                "max_requests": config["requests"],
                "window_seconds": config["window"],
                "remaining": max(0, config["requests"] - current_requests)
            }
        
        return status
    
    async def get_threat_score(self, client_ip: str) -> int:
        """Get threat score for IP."""
        if self.redis_client:
            score = await self.redis_client.get(f"threat_score:{client_ip}")
            return int(score) if score else 0
        else:
            return self.threat_scores.get(client_ip, 0)
    
    async def reset_threat_score(self, client_ip: str) -> None:
        """Reset threat score for IP."""
        if self.redis_client:
            await self.redis_client.delete(f"threat_score:{client_ip}")
        
        if client_ip in self.threat_scores:
            del self.threat_scores[client_ip]
        
        self.logger.info(f"Threat score reset for IP: {client_ip}")


class CORSSecurityMiddleware(BaseHTTPMiddleware):
    """CORS security middleware with enhanced validation."""
    
    def __init__(self, app):
        super().__init__(app)
        self.allowed_origins = settings.security.allowed_origins
        self.allowed_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
        self.allowed_headers = [
            "accept", "accept-language", "content-language", "content-type",
            "authorization", "x-api-key", "x-request-id", "x-forwarded-for"
        ]
        self.max_age = 86400  # 24 hours
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Handle CORS with security validation."""
        origin = request.headers.get("origin")
        
        # Handle preflight requests
        if request.method == "OPTIONS":
            return self._handle_preflight(request, origin)
        
        # Process request
        response = await call_next(request)
        
        # Add CORS headers
        self._add_cors_headers(response, origin)
        
        return response
    
    def _handle_preflight(self, request: Request, origin: Optional[str]) -> Response:
        """Handle CORS preflight requests."""
        if not self._is_origin_allowed(origin):
            return Response(status_code=403)
        
        requested_method = request.headers.get("access-control-request-method")
        if requested_method not in self.allowed_methods:
            return Response(status_code=405)
        
        requested_headers = request.headers.get("access-control-request-headers", "")
        requested_headers_list = [h.strip().lower() for h in requested_headers.split(",") if h.strip()]
        
        if not all(header in self.allowed_headers for header in requested_headers_list):
            return Response(status_code=400)
        
        response = Response(status_code=200)
        self._add_cors_headers(response, origin)
        response.headers["access-control-allow-methods"] = ", ".join(self.allowed_methods)
        response.headers["access-control-allow-headers"] = ", ".join(self.allowed_headers)
        response.headers["access-control-max-age"] = str(self.max_age)
        
        return response
    
    def _add_cors_headers(self, response: Response, origin: Optional[str]) -> None:
        """Add CORS headers to response."""
        if self._is_origin_allowed(origin):
            response.headers["access-control-allow-origin"] = origin
            response.headers["access-control-allow-credentials"] = "true"
        
        response.headers["vary"] = "Origin"
    
    def _is_origin_allowed(self, origin: Optional[str]) -> bool:
        """Check if origin is allowed."""
        if not origin:
            return False
        
        if "*" in self.allowed_origins:
            return True
        
        return origin in self.allowed_origins


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Request validation middleware."""
    
    def __init__(self, app):
        super().__init__(app)
        self.max_header_size = 8192  # 8KB
        self.max_headers_count = 100
        self.blocked_user_agents = [
            "sqlmap", "nikto", "nmap", "masscan", "zap", "burp"
        ]
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Validate request structure and content."""
        # Validate headers
        await self._validate_headers(request)
        
        # Validate user agent
        await self._validate_user_agent(request)
        
        # Validate content type
        await self._validate_content_type(request)
        
        return await call_next(request)
    
    async def _validate_headers(self, request: Request) -> None:
        """Validate request headers."""
        # Check header count
        if len(request.headers) > self.max_headers_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Too many headers"
            )
        
        # Check header sizes
        for name, value in request.headers.items():
            if len(name) + len(value) > self.max_header_size:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Header too large"
                )
    
    async def _validate_user_agent(self, request: Request) -> None:
        """Validate user agent."""
        user_agent = request.headers.get("user-agent", "").lower()
        
        for blocked_agent in self.blocked_user_agents:
            if blocked_agent in user_agent:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Blocked user agent"
                )
    
    async def _validate_content_type(self, request: Request) -> None:
        """Validate content type for POST/PUT requests."""
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            
            # Allow common content types
            allowed_types = [
                "application/json",
                "application/x-www-form-urlencoded",
                "multipart/form-data",
                "text/plain"
            ]
            
            if not any(allowed_type in content_type for allowed_type in allowed_types):
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="Unsupported content type"
                )


"""
Authentication dependencies for ImaniPay Blockchain Service.

This module provides FastAPI dependencies for OAuth2 authentication,
authorization, and security validation.
"""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.services.auth import AuthService
from app.models import User

logger = logging.getLogger(__name__)

# Security schemes
security = HTTPBearer()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Global auth service instance
auth_service = AuthService()


class AuthenticationError(Exception):
    """Authentication error exception."""
    pass


class AuthorizationError(Exception):
    """Authorization error exception."""
    pass


# ========================================================================
# Authentication Dependencies
# ========================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_async_session)
) -> Dict[str, Any]:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP authorization credentials
        session: Database session
        
    Returns:
        Dict[str, Any]: Current user information
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        token_data = await auth_service.verify_token(credentials, session)
        return token_data
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
) -> User:
    """
    Get current active user object.
    
    Args:
        current_user: Current user token data
        session: Database session
        
    Returns:
        User: Current user object
        
    Raises:
        HTTPException: If user is not active
    """
    try:
        from sqlalchemy import select
        
        user_result = await session.execute(
            select(User).where(User.id == current_user["user_id"])
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get active user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate user"
        )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_async_session)
) -> Optional[Dict[str, Any]]:
    """
    Get current user if authenticated, otherwise return None.
    
    Args:
        credentials: HTTP authorization credentials (optional)
        session: Database session
        
    Returns:
        Optional[Dict[str, Any]]: Current user information or None
    """
    if not credentials:
        return None
    
    try:
        return await auth_service.verify_token(credentials, session)
    except Exception:
        return None


# ========================================================================
# API Key Authentication
# ========================================================================

async def get_api_key_user(
    api_key: Optional[str] = Depends(api_key_header),
    session: AsyncSession = Depends(get_async_session)
) -> Optional[Dict[str, Any]]:
    """
    Get user from API key authentication.
    
    Args:
        api_key: API key from header
        session: Database session
        
    Returns:
        Optional[Dict[str, Any]]: API key user information or None
    """
    if not api_key:
        return None
    
    try:
        return await auth_service.verify_api_key(api_key, session=session)
    except Exception as e:
        logger.error(f"API key authentication failed: {e}")
        return None


async def require_api_key(
    api_key_data: Optional[Dict[str, Any]] = Depends(get_api_key_user)
) -> Dict[str, Any]:
    """
    Require valid API key authentication.
    
    Args:
        api_key_data: API key user data
        
    Returns:
        Dict[str, Any]: API key user information
        
    Raises:
        HTTPException: If API key is invalid
    """
    if not api_key_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return api_key_data


# ========================================================================
# Authorization Dependencies
# ========================================================================

def require_scopes(required_scopes: List[str]):
    """
    Create dependency that requires specific scopes.
    
    Args:
        required_scopes: List of required scopes
        
    Returns:
        Dependency function
    """
    async def check_scopes(
        current_user: Dict[str, Any] = Depends(get_current_user)
    ) -> Dict[str, Any]:
        user_scopes = current_user.get("scopes", [])
        
        if not all(scope in user_scopes for scope in required_scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        return current_user
    
    return check_scopes


def require_api_scopes(required_scopes: List[str]):
    """
    Create dependency that requires specific API key scopes.
    
    Args:
        required_scopes: List of required scopes
        
    Returns:
        Dependency function
    """
    async def check_api_scopes(
        api_key_data: Dict[str, Any] = Depends(require_api_key)
    ) -> Dict[str, Any]:
        api_scopes = api_key_data.get("scopes", [])
        
        if not all(scope in api_scopes for scope in required_scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient API key permissions"
            )
        
        return api_key_data
    
    return check_api_scopes


async def require_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Require admin user.
    
    Args:
        current_user: Current user
        
    Returns:
        User: Admin user
        
    Raises:
        HTTPException: If user is not admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user


async def get_current_verified_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current verified user (email and phone verified).
    
    Args:
        current_user: Current user
        
    Returns:
        User: Verified user
        
    Raises:
        HTTPException: If user is not verified
    """
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )
    
    if not current_user.phone_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Phone verification required"
        )
    
    return current_user


async def require_verified_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Require verified user (email and phone verified).
    
    Args:
        current_user: Current user
        
    Returns:
        User: Verified user
        
    Raises:
        HTTPException: If user is not verified
    """
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )
    
    if not current_user.phone_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Phone verification required"
        )
    
    return current_user


# ========================================================================
# Multi-Authentication Dependencies
# ========================================================================

async def get_authenticated_user(
    jwt_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
    api_key_user: Optional[Dict[str, Any]] = Depends(get_api_key_user),
    session: AsyncSession = Depends(get_async_session)
) -> Dict[str, Any]:
    """
    Get authenticated user from either JWT or API key.
    
    Args:
        jwt_user: JWT authenticated user
        api_key_user: API key authenticated user
        session: Database session
        
    Returns:
        Dict[str, Any]: Authenticated user information
        
    Raises:
        HTTPException: If no valid authentication provided
    """
    if jwt_user:
        return jwt_user
    elif api_key_user:
        return {
            "user_id": api_key_user["user_id"],
            "auth_type": "api_key",
            "scopes": api_key_user["scopes"],
            "key_id": api_key_user["key_id"]
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ========================================================================
# Rate Limiting Dependencies
# ========================================================================

async def check_rate_limit(
    request: Request,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> None:
    """
    Check rate limiting for authenticated users.
    
    Args:
        request: FastAPI request
        current_user: Current user (optional)
        
    Raises:
        HTTPException: If rate limit exceeded
    """
    # Rate limiting is handled by SecurityMiddleware
    # This dependency can be used for additional user-specific rate limiting
    pass


# ========================================================================
# Security Context Dependencies
# ========================================================================

async def get_security_context(
    request: Request,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Get security context for request.
    
    Args:
        request: FastAPI request
        current_user: Current user (optional)
        
    Returns:
        Dict[str, Any]: Security context
    """
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    
    return {
        "client_ip": client_ip,
        "user_agent": user_agent,
        "user_id": current_user.get("user_id") if current_user else None,
        "auth_type": current_user.get("auth_type", "none") if current_user else "none",
        "timestamp": request.state.__dict__.get("start_time"),
        "request_id": request.headers.get("x-request-id"),
        "path": request.url.path,
        "method": request.method
    }


# ========================================================================
# Wallet Access Dependencies
# ========================================================================

async def require_wallet_access(
    wallet_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
) -> User:
    """
    Require access to specific wallet.
    
    Args:
        wallet_id: Wallet ID
        current_user: Current user
        session: Database session
        
    Returns:
        User: User with wallet access
        
    Raises:
        HTTPException: If user doesn't have wallet access
    """
    from sqlalchemy import select
    from app.models import Wallet
    
    try:
        # Check if user owns the wallet
        wallet_result = await session.execute(
            select(Wallet).where(
                Wallet.id == wallet_id,
                Wallet.user_id == current_user.id
            )
        )
        
        wallet = wallet_result.scalar_one_or_none()
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Wallet access denied"
            )
        
        return current_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Wallet access check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify wallet access"
        )


# ========================================================================
# Transaction Authorization Dependencies
# ========================================================================

async def require_transaction_authorization(
    amount: float,
    current_user: User = Depends(get_current_verified_user),
    session: AsyncSession = Depends(get_async_session)
) -> User:
    """
    Require authorization for transaction based on amount.
    
    Args:
        amount: Transaction amount
        current_user: Current verified user
        session: Database session
        
    Returns:
        User: Authorized user
        
    Raises:
        HTTPException: If transaction not authorized
    """
    # Check transaction limits based on user verification level
    if amount > 1000 and not current_user.kyc_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="KYC verification required for large transactions"
        )
    
    if amount > 10000 and not current_user.enhanced_verification:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Enhanced verification required for high-value transactions"
        )
    
    return current_user


# ========================================================================
# Development Dependencies
# ========================================================================

async def get_development_user() -> Dict[str, Any]:
    """
    Get development user (for testing only).
    
    Returns:
        Dict[str, Any]: Development user data
    """
    from app.core.config import get_settings
    settings = get_settings()
    
    if settings.app.environment != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Development endpoint not available"
        )
    
    return {
        "user_id": UUID("00000000-0000-0000-0000-000000000000"),
        "email": "dev@imanipay.com",
        "scopes": ["admin", "user", "api"],
        "auth_type": "development"
    }


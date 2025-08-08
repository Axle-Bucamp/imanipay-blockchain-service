"""
Authentication API endpoints for ImaniPay Blockchain Service.

This module provides comprehensive authentication endpoints including
registration, login, MFA, API keys, and session management.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.services.auth import AuthService, AuthenticationError, InvalidCredentialsError, MFARequiredError, AccountLockedError
from app.dependencies.auth import (
    get_current_user, get_current_active_user, require_admin,
    require_verified_user, get_security_context
)
from app.schemas import (
    UserRegistration, UserLogin, TokenResponse, UserProfile,
    MFASetupResponse, MFAVerificationRequest, APIKeyCreateRequest,
    APIKeyResponse, PasswordChangeRequest, PasswordResetRequest,
    EmailVerificationRequest, PhoneVerificationRequest
)
from app.models import User

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/auth", tags=["Authentication"])

# Auth service instance
auth_service = AuthService()


# ========================================================================
# User Registration and Login
# ========================================================================

@router.post("/register", response_model=Dict[str, Any])
async def register_user(
    registration: UserRegistration,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    security_context: Dict[str, Any] = Depends(get_security_context)
) -> Dict[str, Any]:
    """
    Register a new user.
    
    Args:
        registration: User registration data
        request: FastAPI request
        session: Database session
        security_context: Security context
        
    Returns:
        Dict[str, Any]: Registration result
        
    Raises:
        HTTPException: If registration fails
    """
    try:
        result = await auth_service.register_user(registration, session)
        
        logger.info(f"User registration successful: {registration.email}")
        
        return {
            "message": "User registered successfully",
            "user_id": result["user_id"],
            "email": result["email"],
            "requires_verification": result["requires_verification"]
        }
        
    except AuthenticationError as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=TokenResponse)
async def login_user(
    login: UserLogin,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    security_context: Dict[str, Any] = Depends(get_security_context)
) -> TokenResponse:
    """
    Authenticate user and return tokens.
    
    Args:
        login: User login credentials
        request: FastAPI request
        session: Database session
        security_context: Security context
        
    Returns:
        TokenResponse: Authentication tokens
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        client_ip = security_context["client_ip"]
        user_agent = security_context["user_agent"]
        
        token_response = await auth_service.authenticate_user(
            login, client_ip, user_agent, session
        )
        
        logger.info(f"User login successful: {login.email}")
        
        return token_response
        
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    except MFARequiredError:
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail="MFA code required",
            headers={"X-MFA-Required": "true"}
        )
    except AccountLockedError:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account temporarily locked"
        )
    except AuthenticationError as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str,
    session: AsyncSession = Depends(get_async_session)
) -> TokenResponse:
    """
    Refresh access token using refresh token.
    
    Args:
        refresh_token: Refresh token
        session: Database session
        
    Returns:
        TokenResponse: New tokens
        
    Raises:
        HTTPException: If refresh fails
    """
    try:
        token_response = await auth_service.refresh_token(refresh_token, session)
        
        logger.info("Token refresh successful")
        
        return token_response
        
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed"
        )


@router.post("/logout")
async def logout_user(
    session_id: Optional[UUID] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
) -> Dict[str, str]:
    """
    Logout user and invalidate session.
    
    Args:
        session_id: Session ID (optional, logout all if not provided)
        current_user: Current user
        session: Database session
        
    Returns:
        Dict[str, str]: Logout result
    """
    try:
        result = await auth_service.logout_user(
            current_user["user_id"], session_id, session
        )
        
        logger.info(f"User logout successful: {current_user['user_id']}")
        
        return result
        
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


# ========================================================================
# User Profile and Management
# ========================================================================

@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
) -> UserProfile:
    """
    Get current user profile.
    
    Args:
        current_user: Current user
        
    Returns:
        UserProfile: User profile data
    """
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        phone=current_user.phone,
        is_active=current_user.is_active,
        email_verified=current_user.email_verified,
        phone_verified=current_user.phone_verified,
        kyc_verified=current_user.kyc_verified,
        mfa_enabled=current_user.mfa_enabled,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )


@router.put("/me", response_model=UserProfile)
async def update_user_profile(
    profile_update: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
) -> UserProfile:
    """
    Update current user profile.
    
    Args:
        profile_update: Profile update data
        current_user: Current user
        session: Database session
        
    Returns:
        UserProfile: Updated user profile
    """
    try:
        # Update allowed fields
        allowed_fields = ["phone"]
        
        for field, value in profile_update.items():
            if field in allowed_fields:
                setattr(current_user, field, value)
        
        await session.commit()
        await session.refresh(current_user)
        
        logger.info(f"User profile updated: {current_user.id}")
        
        return UserProfile(
            id=current_user.id,
            email=current_user.email,
            phone=current_user.phone,
            is_active=current_user.is_active,
            email_verified=current_user.email_verified,
            phone_verified=current_user.phone_verified,
            kyc_verified=current_user.kyc_verified,
            mfa_enabled=current_user.mfa_enabled,
            created_at=current_user.created_at,
            last_login=current_user.last_login
        )
        
    except Exception as e:
        logger.error(f"Profile update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed"
        )


@router.post("/change-password")
async def change_password(
    password_change: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
) -> Dict[str, str]:
    """
    Change user password.
    
    Args:
        password_change: Password change request
        current_user: Current user
        session: Database session
        
    Returns:
        Dict[str, str]: Change result
    """
    try:
        # Verify current password
        if not auth_service.pwd_context.verify(password_change.current_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Hash new password
        new_password_hash = auth_service.pwd_context.hash(password_change.new_password)
        
        # Update password
        current_user.password_hash = new_password_hash
        await session.commit()
        
        logger.info(f"Password changed for user: {current_user.id}")
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


# ========================================================================
# Multi-Factor Authentication
# ========================================================================

@router.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
) -> MFASetupResponse:
    """
    Setup MFA for current user.
    
    Args:
        current_user: Current user
        session: Database session
        
    Returns:
        MFASetupResponse: MFA setup information
    """
    try:
        if current_user.mfa_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MFA is already enabled"
            )
        
        mfa_setup = await auth_service.setup_mfa(current_user.id, session)
        
        logger.info(f"MFA setup initiated for user: {current_user.id}")
        
        return mfa_setup
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MFA setup failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MFA setup failed"
        )


@router.post("/mfa/enable")
async def enable_mfa(
    verification: MFAVerificationRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
) -> Dict[str, str]:
    """
    Enable MFA after verification.
    
    Args:
        verification: MFA verification request
        current_user: Current user
        session: Database session
        
    Returns:
        Dict[str, str]: Enable result
    """
    try:
        if current_user.mfa_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MFA is already enabled"
            )
        
        result = await auth_service.enable_mfa(
            current_user.id, verification.code, session
        )
        
        logger.info(f"MFA enabled for user: {current_user.id}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MFA enable failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MFA enable failed"
        )


@router.post("/mfa/disable")
async def disable_mfa(
    verification: MFAVerificationRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
) -> Dict[str, str]:
    """
    Disable MFA after verification.
    
    Args:
        verification: MFA verification request
        current_user: Current user
        session: Database session
        
    Returns:
        Dict[str, str]: Disable result
    """
    try:
        if not current_user.mfa_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MFA is not enabled"
            )
        
        result = await auth_service.disable_mfa(
            current_user.id, verification.code, session
        )
        
        logger.info(f"MFA disabled for user: {current_user.id}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MFA disable failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MFA disable failed"
        )


# ========================================================================
# API Key Management
# ========================================================================

@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    api_key_request: APIKeyCreateRequest,
    current_user: User = Depends(get_current_verified_user),
    session: AsyncSession = Depends(get_async_session)
) -> APIKeyResponse:
    """
    Create API key for current user.
    
    Args:
        api_key_request: API key creation request
        current_user: Current verified user
        session: Database session
        
    Returns:
        APIKeyResponse: API key information
    """
    try:
        api_key_data = await auth_service.create_api_key(
            current_user.id,
            api_key_request.name,
            api_key_request.scopes,
            api_key_request.expires_at,
            session
        )
        
        logger.info(f"API key created for user: {current_user.id}")
        
        return APIKeyResponse(**api_key_data)
        
    except Exception as e:
        logger.error(f"API key creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key creation failed"
        )


@router.get("/api-keys", response_model=List[Dict[str, Any]])
async def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
) -> List[Dict[str, Any]]:
    """
    List API keys for current user.
    
    Args:
        current_user: Current user
        session: Database session
        
    Returns:
        List[Dict[str, Any]]: List of API keys
    """
    try:
        from sqlalchemy import select
        from app.models import APIKey
        
        result = await session.execute(
            select(APIKey).where(
                APIKey.user_id == current_user.id,
                APIKey.is_active == True
            )
        )
        
        api_keys = result.scalars().all()
        
        return [
            {
                "id": str(api_key.id),
                "name": api_key.name,
                "scopes": api_key.scopes,
                "created_at": api_key.created_at.isoformat(),
                "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
                "last_used_at": api_key.last_used_at.isoformat() if api_key.last_used_at else None
            }
            for api_key in api_keys
        ]
        
    except Exception as e:
        logger.error(f"API key listing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list API keys"
        )


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
) -> Dict[str, str]:
    """
    Revoke API key.
    
    Args:
        key_id: API key ID
        current_user: Current user
        session: Database session
        
    Returns:
        Dict[str, str]: Revoke result
    """
    try:
        from sqlalchemy import update
        from app.models import APIKey
        
        # Update API key to inactive
        result = await session.execute(
            update(APIKey)
            .where(
                APIKey.id == key_id,
                APIKey.user_id == current_user.id
            )
            .values(is_active=False)
        )
        
        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        await session.commit()
        
        logger.info(f"API key revoked: {key_id}")
        
        return {"message": "API key revoked successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API key revocation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key revocation failed"
        )


# ========================================================================
# Session Management
# ========================================================================

@router.get("/sessions", response_model=List[Dict[str, Any]])
async def list_user_sessions(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
) -> List[Dict[str, Any]]:
    """
    List active sessions for current user.
    
    Args:
        current_user: Current user
        session: Database session
        
    Returns:
        List[Dict[str, Any]]: List of active sessions
    """
    try:
        from sqlalchemy import select
        from app.models import UserSession
        
        result = await session.execute(
            select(UserSession).where(
                UserSession.user_id == current_user.id,
                UserSession.is_active == True
            )
        )
        
        sessions = result.scalars().all()
        
        return [
            {
                "id": str(user_session.id),
                "ip_address": user_session.ip_address,
                "user_agent": user_session.user_agent,
                "created_at": user_session.created_at.isoformat(),
                "last_activity": user_session.last_activity.isoformat() if user_session.last_activity else None,
                "expires_at": user_session.expires_at.isoformat()
            }
            for user_session in sessions
        ]
        
    except Exception as e:
        logger.error(f"Session listing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list sessions"
        )


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
) -> Dict[str, str]:
    """
    Revoke specific session.
    
    Args:
        session_id: Session ID
        current_user: Current user
        session: Database session
        
    Returns:
        Dict[str, str]: Revoke result
    """
    try:
        result = await auth_service.logout_user(
            current_user.id, session_id, session
        )
        
        logger.info(f"Session revoked: {session_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"Session revocation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session revocation failed"
        )


# ========================================================================
# Admin Endpoints
# ========================================================================

@router.get("/admin/users", response_model=List[Dict[str, Any]])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    admin_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_async_session)
) -> List[Dict[str, Any]]:
    """
    List users (admin only).
    
    Args:
        skip: Number of users to skip
        limit: Maximum number of users to return
        admin_user: Admin user
        session: Database session
        
    Returns:
        List[Dict[str, Any]]: List of users
    """
    try:
        from sqlalchemy import select
        
        result = await session.execute(
            select(User).offset(skip).limit(limit)
        )
        
        users = result.scalars().all()
        
        return [
            {
                "id": str(user.id),
                "email": user.email,
                "phone": user.phone,
                "is_active": user.is_active,
                "email_verified": user.email_verified,
                "phone_verified": user.phone_verified,
                "kyc_verified": user.kyc_verified,
                "mfa_enabled": user.mfa_enabled,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None
            }
            for user in users
        ]
        
    except Exception as e:
        logger.error(f"User listing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users"
        )


@router.put("/admin/users/{user_id}/status")
async def update_user_status(
    user_id: UUID,
    status_update: Dict[str, bool],
    admin_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_async_session)
) -> Dict[str, str]:
    """
    Update user status (admin only).
    
    Args:
        user_id: User ID
        status_update: Status update data
        admin_user: Admin user
        session: Database session
        
    Returns:
        Dict[str, str]: Update result
    """
    try:
        from sqlalchemy import select, update
        
        # Get user
        user_result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update allowed status fields
        allowed_fields = ["is_active", "email_verified", "phone_verified", "kyc_verified"]
        update_data = {}
        
        for field, value in status_update.items():
            if field in allowed_fields:
                update_data[field] = value
        
        if update_data:
            await session.execute(
                update(User)
                .where(User.id == user_id)
                .values(**update_data)
            )
            await session.commit()
        
        logger.info(f"User status updated by admin: {user_id}")
        
        return {"message": "User status updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User status update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User status update failed"
        )


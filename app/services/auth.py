"""
Authentication service for ImaniPay Blockchain Service.

This module provides comprehensive authentication functionality including
OAuth2, JWT tokens, multi-factor authentication, and session management.
"""

import logging
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from uuid import UUID, uuid4

import jwt
import pyotp
import qrcode
from io import BytesIO
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database import get_async_session_context
from app.models import User, UserSession, APIKey, LoginAttempt, SecurityEvent
from app.schemas import (
    UserLogin, UserRegistration, TokenResponse, UserProfile,
    MFASetupResponse, MFAVerificationRequest
)
from app.services.encryption import EncryptionService

logger = logging.getLogger(__name__)
settings = get_settings()


class AuthenticationError(Exception):
    """Base exception for authentication errors."""
    pass


class InvalidCredentialsError(AuthenticationError):
    """Exception raised for invalid credentials."""
    pass


class TokenExpiredError(AuthenticationError):
    """Exception raised for expired tokens."""
    pass


class MFARequiredError(AuthenticationError):
    """Exception raised when MFA is required."""
    pass


class AccountLockedError(AuthenticationError):
    """Exception raised when account is locked."""
    pass


class AuthService:
    """Comprehensive authentication service."""
    
    def __init__(self):
        self.logger = logger
        self.encryption_service = EncryptionService()
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.security = HTTPBearer()
        
        # JWT configuration
        self.jwt_secret = settings.security.jwt_secret_key
        self.jwt_algorithm = "HS256"
        self.access_token_expire_minutes = settings.security.access_token_expire_minutes
        self.refresh_token_expire_days = settings.security.refresh_token_expire_days
        
        # Security settings
        self.max_login_attempts = 5
        self.lockout_duration_minutes = 30
        self.session_timeout_hours = 24
        
        # MFA settings
        self.mfa_issuer = "ImaniPay"
        self.backup_codes_count = 10
    
    # ========================================================================
    # User Registration and Authentication
    # ========================================================================
    
    async def register_user(
        self,
        registration: UserRegistration,
        session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Register a new user.
        
        Args:
            registration: User registration data
            session: Database session
            
        Returns:
            Dict[str, Any]: Registration result
            
        Raises:
            AuthenticationError: If registration fails
        """
        async def _register_user(db_session: AsyncSession) -> Dict[str, Any]:
            try:
                # Check if user already exists
                existing_user = await db_session.execute(
                    select(User).where(
                        or_(
                            User.email == registration.email,
                            User.phone == registration.phone
                        )
                    )
                )
                
                if existing_user.scalar_one_or_none():
                    raise AuthenticationError("User already exists with this email or phone")
                
                # Hash password
                password_hash = self.pwd_context.hash(registration.password)
                
                # Create user
                user = User(
                    email=registration.email,
                    phone=registration.phone,
                    password_hash=password_hash,
                    is_active=True,
                    email_verified=False,
                    phone_verified=False,
                    mfa_enabled=False,
                    created_at=datetime.utcnow()
                )
                
                db_session.add(user)
                await db_session.commit()
                await db_session.refresh(user)
                
                # Log security event
                await self._log_security_event(
                    user.id, "user_registered", 
                    {"email": registration.email}, db_session
                )
                
                self.logger.info(f"User registered successfully: {user.email}")
                
                return {
                    "user_id": str(user.id),
                    "email": user.email,
                    "message": "User registered successfully",
                    "requires_verification": True
                }
                
            except Exception as e:
                self.logger.error(f"User registration failed: {e}")
                raise AuthenticationError(f"Registration failed: {str(e)}")
        
        if session:
            return await _register_user(session)
        else:
            async with get_async_session_context() as db_session:
                return await _register_user(db_session)
    
    async def authenticate_user(
        self,
        login: UserLogin,
        ip_address: str,
        user_agent: str,
        session: Optional[AsyncSession] = None
    ) -> TokenResponse:
        """
        Authenticate user and return tokens.
        
        Args:
            login: User login credentials
            ip_address: Client IP address
            user_agent: Client user agent
            session: Database session
            
        Returns:
            TokenResponse: Authentication tokens
            
        Raises:
            AuthenticationError: If authentication fails
        """
        async def _authenticate_user(db_session: AsyncSession) -> TokenResponse:
            try:
                # Check rate limiting
                await self._check_login_rate_limit(login.email, ip_address, db_session)
                
                # Get user
                user_result = await db_session.execute(
                    select(User).where(User.email == login.email)
                )
                user = user_result.scalar_one_or_none()
                
                if not user:
                    await self._log_failed_login(login.email, ip_address, "user_not_found", db_session)
                    raise InvalidCredentialsError("Invalid credentials")
                
                # Check if account is locked
                if await self._is_account_locked(user.id, db_session):
                    raise AccountLockedError("Account is temporarily locked due to multiple failed attempts")
                
                # Verify password
                if not self.pwd_context.verify(login.password, user.password_hash):
                    await self._log_failed_login(login.email, ip_address, "invalid_password", db_session)
                    raise InvalidCredentialsError("Invalid credentials")
                
                # Check if account is active
                if not user.is_active:
                    raise AuthenticationError("Account is deactivated")
                
                # Check MFA if enabled
                if user.mfa_enabled:
                    if not login.mfa_code:
                        raise MFARequiredError("MFA code required")
                    
                    if not await self._verify_mfa_code(user.id, login.mfa_code, db_session):
                        await self._log_failed_login(login.email, ip_address, "invalid_mfa", db_session)
                        raise InvalidCredentialsError("Invalid MFA code")
                
                # Generate tokens
                access_token = self._create_access_token(user.id, user.email)
                refresh_token = self._create_refresh_token(user.id)
                
                # Create session
                session_id = await self._create_user_session(
                    user.id, ip_address, user_agent, refresh_token, db_session
                )
                
                # Clear failed login attempts
                await self._clear_failed_login_attempts(user.id, db_session)
                
                # Log successful login
                await self._log_security_event(
                    user.id, "user_login", 
                    {"ip_address": ip_address, "user_agent": user_agent}, db_session
                )
                
                self.logger.info(f"User authenticated successfully: {user.email}")
                
                return TokenResponse(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    token_type="bearer",
                    expires_in=self.access_token_expire_minutes * 60,
                    session_id=str(session_id)
                )
                
            except (InvalidCredentialsError, MFARequiredError, AccountLockedError):
                raise
            except Exception as e:
                self.logger.error(f"Authentication failed: {e}")
                raise AuthenticationError(f"Authentication failed: {str(e)}")
        
        if session:
            return await _authenticate_user(session)
        else:
            async with get_async_session_context() as db_session:
                return await _authenticate_user(db_session)
    
    async def refresh_token(
        self,
        refresh_token: str,
        session: Optional[AsyncSession] = None
    ) -> TokenResponse:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token
            session: Database session
            
        Returns:
            TokenResponse: New tokens
            
        Raises:
            TokenExpiredError: If refresh token is invalid or expired
        """
        async def _refresh_token(db_session: AsyncSession) -> TokenResponse:
            try:
                # Decode refresh token
                payload = jwt.decode(refresh_token, self.jwt_secret, algorithms=[self.jwt_algorithm])
                user_id = UUID(payload.get("sub"))
                token_type = payload.get("type")
                
                if token_type != "refresh":
                    raise TokenExpiredError("Invalid token type")
                
                # Check if session exists and is valid
                session_result = await db_session.execute(
                    select(UserSession).where(
                        and_(
                            UserSession.user_id == user_id,
                            UserSession.refresh_token_hash == self._hash_token(refresh_token),
                            UserSession.is_active == True,
                            UserSession.expires_at > datetime.utcnow()
                        )
                    )
                )
                
                user_session = session_result.scalar_one_or_none()
                if not user_session:
                    raise TokenExpiredError("Invalid or expired refresh token")
                
                # Get user
                user_result = await db_session.execute(
                    select(User).where(User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if not user or not user.is_active:
                    raise TokenExpiredError("User not found or inactive")
                
                # Generate new tokens
                new_access_token = self._create_access_token(user.id, user.email)
                new_refresh_token = self._create_refresh_token(user.id)
                
                # Update session with new refresh token
                user_session.refresh_token_hash = self._hash_token(new_refresh_token)
                user_session.last_activity = datetime.utcnow()
                await db_session.commit()
                
                self.logger.info(f"Token refreshed for user: {user.email}")
                
                return TokenResponse(
                    access_token=new_access_token,
                    refresh_token=new_refresh_token,
                    token_type="bearer",
                    expires_in=self.access_token_expire_minutes * 60,
                    session_id=str(user_session.id)
                )
                
            except jwt.ExpiredSignatureError:
                raise TokenExpiredError("Refresh token expired")
            except jwt.InvalidTokenError:
                raise TokenExpiredError("Invalid refresh token")
            except Exception as e:
                self.logger.error(f"Token refresh failed: {e}")
                raise TokenExpiredError(f"Token refresh failed: {str(e)}")
        
        if session:
            return await _refresh_token(session)
        else:
            async with get_async_session_context() as db_session:
                return await _refresh_token(db_session)
    
    async def logout_user(
        self,
        user_id: UUID,
        session_id: Optional[UUID] = None,
        session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Logout user and invalidate session.
        
        Args:
            user_id: User ID
            session_id: Session ID (if None, logout all sessions)
            session: Database session
            
        Returns:
            Dict[str, Any]: Logout result
        """
        async def _logout_user(db_session: AsyncSession) -> Dict[str, Any]:
            try:
                if session_id:
                    # Logout specific session
                    await db_session.execute(
                        update(UserSession)
                        .where(
                            and_(
                                UserSession.user_id == user_id,
                                UserSession.id == session_id
                            )
                        )
                        .values(is_active=False, logged_out_at=datetime.utcnow())
                    )
                    message = "Session logged out successfully"
                else:
                    # Logout all sessions
                    await db_session.execute(
                        update(UserSession)
                        .where(UserSession.user_id == user_id)
                        .values(is_active=False, logged_out_at=datetime.utcnow())
                    )
                    message = "All sessions logged out successfully"
                
                await db_session.commit()
                
                # Log security event
                await self._log_security_event(
                    user_id, "user_logout", 
                    {"session_id": str(session_id) if session_id else "all"}, db_session
                )
                
                self.logger.info(f"User logged out: {user_id}")
                
                return {"message": message}
                
            except Exception as e:
                self.logger.error(f"Logout failed: {e}")
                raise AuthenticationError(f"Logout failed: {str(e)}")
        
        if session:
            return await _logout_user(session)
        else:
            async with get_async_session_context() as db_session:
                return await _logout_user(db_session)
    
    # ========================================================================
    # Token Management
    # ========================================================================
    
    async def verify_token(
        self,
        credentials: HTTPAuthorizationCredentials,
        session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Verify JWT access token.
        
        Args:
            credentials: HTTP authorization credentials
            session: Database session
            
        Returns:
            Dict[str, Any]: Token payload
            
        Raises:
            HTTPException: If token is invalid
        """
        try:
            # Decode token
            payload = jwt.decode(
                credentials.credentials, 
                self.jwt_secret, 
                algorithms=[self.jwt_algorithm]
            )
            
            user_id = UUID(payload.get("sub"))
            token_type = payload.get("type")
            
            if token_type != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            # Check if user exists and is active
            async def _verify_user(db_session: AsyncSession) -> Dict[str, Any]:
                user_result = await db_session.execute(
                    select(User).where(User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if not user or not user.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="User not found or inactive"
                    )
                
                return {
                    "user_id": user_id,
                    "email": user.email,
                    "scopes": payload.get("scopes", []),
                    "exp": payload.get("exp"),
                    "iat": payload.get("iat")
                }
            
            if session:
                return await _verify_user(session)
            else:
                async with get_async_session_context() as db_session:
                    return await _verify_user(db_session)
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        except Exception as e:
            self.logger.error(f"Token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token verification failed"
            )
    
    def _create_access_token(
        self,
        user_id: UUID,
        email: str,
        scopes: List[str] = None
    ) -> str:
        """Create JWT access token."""
        now = datetime.utcnow()
        expire = now + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            "sub": str(user_id),
            "email": email,
            "type": "access",
            "scopes": scopes or ["user"],
            "iat": now.timestamp(),
            "exp": expire.timestamp(),
            "iss": "imanipay",
            "jti": str(uuid4())
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def _create_refresh_token(self, user_id: UUID) -> str:
        """Create JWT refresh token."""
        now = datetime.utcnow()
        expire = now + timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            "sub": str(user_id),
            "type": "refresh",
            "iat": now.timestamp(),
            "exp": expire.timestamp(),
            "iss": "imanipay",
            "jti": str(uuid4())
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    # ========================================================================
    # Multi-Factor Authentication
    # ========================================================================
    
    async def setup_mfa(
        self,
        user_id: UUID,
        session: Optional[AsyncSession] = None
    ) -> MFASetupResponse:
        """
        Setup MFA for user.
        
        Args:
            user_id: User ID
            session: Database session
            
        Returns:
            MFASetupResponse: MFA setup information
        """
        async def _setup_mfa(db_session: AsyncSession) -> MFASetupResponse:
            try:
                # Get user
                user_result = await db_session.execute(
                    select(User).where(User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if not user:
                    raise AuthenticationError("User not found")
                
                # Generate secret
                secret = pyotp.random_base32()
                
                # Create TOTP
                totp = pyotp.TOTP(secret)
                
                # Generate QR code
                provisioning_uri = totp.provisioning_uri(
                    name=user.email,
                    issuer_name=self.mfa_issuer
                )
                
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(provisioning_uri)
                qr.make(fit=True)
                
                qr_img = qr.make_image(fill_color="black", back_color="white")
                qr_buffer = BytesIO()
                qr_img.save(qr_buffer, format='PNG')
                qr_code_data = qr_buffer.getvalue()
                
                # Generate backup codes
                backup_codes = [secrets.token_hex(8) for _ in range(self.backup_codes_count)]
                
                # Encrypt and store MFA data
                encrypted_secret = await self.encryption_service.encrypt_sensitive_data(secret, user_id)
                encrypted_backup_codes = await self.encryption_service.encrypt_json(
                    {"codes": backup_codes}, user_id
                )
                
                # Update user
                user.mfa_secret = encrypted_secret
                user.mfa_backup_codes = encrypted_backup_codes
                user.mfa_setup_completed = True
                
                await db_session.commit()
                
                # Log security event
                await self._log_security_event(
                    user_id, "mfa_setup", {}, db_session
                )
                
                self.logger.info(f"MFA setup completed for user: {user.email}")
                
                return MFASetupResponse(
                    secret=secret,
                    qr_code=qr_code_data,
                    backup_codes=backup_codes,
                    provisioning_uri=provisioning_uri
                )
                
            except Exception as e:
                self.logger.error(f"MFA setup failed: {e}")
                raise AuthenticationError(f"MFA setup failed: {str(e)}")
        
        if session:
            return await _setup_mfa(session)
        else:
            async with get_async_session_context() as db_session:
                return await _setup_mfa(db_session)
    
    async def enable_mfa(
        self,
        user_id: UUID,
        verification_code: str,
        session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Enable MFA after verification.
        
        Args:
            user_id: User ID
            verification_code: MFA verification code
            session: Database session
            
        Returns:
            Dict[str, Any]: Enable result
        """
        async def _enable_mfa(db_session: AsyncSession) -> Dict[str, Any]:
            try:
                # Verify MFA code
                if not await self._verify_mfa_code(user_id, verification_code, db_session):
                    raise AuthenticationError("Invalid verification code")
                
                # Enable MFA
                await db_session.execute(
                    update(User)
                    .where(User.id == user_id)
                    .values(mfa_enabled=True)
                )
                await db_session.commit()
                
                # Log security event
                await self._log_security_event(
                    user_id, "mfa_enabled", {}, db_session
                )
                
                self.logger.info(f"MFA enabled for user: {user_id}")
                
                return {"message": "MFA enabled successfully"}
                
            except Exception as e:
                self.logger.error(f"MFA enable failed: {e}")
                raise AuthenticationError(f"MFA enable failed: {str(e)}")
        
        if session:
            return await _enable_mfa(session)
        else:
            async with get_async_session_context() as db_session:
                return await _enable_mfa(db_session)
    
    async def disable_mfa(
        self,
        user_id: UUID,
        verification_code: str,
        session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Disable MFA after verification.
        
        Args:
            user_id: User ID
            verification_code: MFA verification code
            session: Database session
            
        Returns:
            Dict[str, Any]: Disable result
        """
        async def _disable_mfa(db_session: AsyncSession) -> Dict[str, Any]:
            try:
                # Verify MFA code
                if not await self._verify_mfa_code(user_id, verification_code, db_session):
                    raise AuthenticationError("Invalid verification code")
                
                # Disable MFA
                await db_session.execute(
                    update(User)
                    .where(User.id == user_id)
                    .values(
                        mfa_enabled=False,
                        mfa_secret=None,
                        mfa_backup_codes=None,
                        mfa_setup_completed=False
                    )
                )
                await db_session.commit()
                
                # Log security event
                await self._log_security_event(
                    user_id, "mfa_disabled", {}, db_session
                )
                
                self.logger.info(f"MFA disabled for user: {user_id}")
                
                return {"message": "MFA disabled successfully"}
                
            except Exception as e:
                self.logger.error(f"MFA disable failed: {e}")
                raise AuthenticationError(f"MFA disable failed: {str(e)}")
        
        if session:
            return await _disable_mfa(session)
        else:
            async with get_async_session_context() as db_session:
                return await _disable_mfa(db_session)
    
    # ========================================================================
    # API Key Management
    # ========================================================================
    
    async def create_api_key(
        self,
        user_id: UUID,
        name: str,
        scopes: List[str],
        expires_at: Optional[datetime] = None,
        session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Create API key for user.
        
        Args:
            user_id: User ID
            name: API key name
            scopes: API key scopes
            expires_at: Expiration date
            session: Database session
            
        Returns:
            Dict[str, Any]: API key information
        """
        async def _create_api_key(db_session: AsyncSession) -> Dict[str, Any]:
            try:
                # Generate API key
                api_key = f"imanipay_{secrets.token_urlsafe(32)}"
                api_key_hash = self._hash_token(api_key)
                
                # Create API key record
                api_key_record = APIKey(
                    user_id=user_id,
                    name=name,
                    key_hash=api_key_hash,
                    scopes=scopes,
                    expires_at=expires_at,
                    is_active=True
                )
                
                db_session.add(api_key_record)
                await db_session.commit()
                await db_session.refresh(api_key_record)
                
                # Log security event
                await self._log_security_event(
                    user_id, "api_key_created", 
                    {"name": name, "scopes": scopes}, db_session
                )
                
                self.logger.info(f"API key created for user: {user_id}")
                
                return {
                    "api_key": api_key,
                    "key_id": str(api_key_record.id),
                    "name": name,
                    "scopes": scopes,
                    "expires_at": expires_at.isoformat() if expires_at else None,
                    "created_at": api_key_record.created_at.isoformat()
                }
                
            except Exception as e:
                self.logger.error(f"API key creation failed: {e}")
                raise AuthenticationError(f"API key creation failed: {str(e)}")
        
        if session:
            return await _create_api_key(session)
        else:
            async with get_async_session_context() as db_session:
                return await _create_api_key(db_session)
    
    async def verify_api_key(
        self,
        api_key: str,
        required_scopes: List[str] = None,
        session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Verify API key.
        
        Args:
            api_key: API key
            required_scopes: Required scopes
            session: Database session
            
        Returns:
            Dict[str, Any]: API key information
            
        Raises:
            AuthenticationError: If API key is invalid
        """
        async def _verify_api_key(db_session: AsyncSession) -> Dict[str, Any]:
            try:
                api_key_hash = self._hash_token(api_key)
                
                # Get API key record
                api_key_result = await db_session.execute(
                    select(APIKey).where(
                        and_(
                            APIKey.key_hash == api_key_hash,
                            APIKey.is_active == True,
                            or_(
                                APIKey.expires_at.is_(None),
                                APIKey.expires_at > datetime.utcnow()
                            )
                        )
                    )
                )
                
                api_key_record = api_key_result.scalar_one_or_none()
                if not api_key_record:
                    raise AuthenticationError("Invalid or expired API key")
                
                # Check scopes
                if required_scopes:
                    if not all(scope in api_key_record.scopes for scope in required_scopes):
                        raise AuthenticationError("Insufficient API key permissions")
                
                # Update last used
                api_key_record.last_used_at = datetime.utcnow()
                await db_session.commit()
                
                return {
                    "user_id": api_key_record.user_id,
                    "key_id": str(api_key_record.id),
                    "name": api_key_record.name,
                    "scopes": api_key_record.scopes
                }
                
            except Exception as e:
                self.logger.error(f"API key verification failed: {e}")
                raise AuthenticationError(f"API key verification failed: {str(e)}")
        
        if session:
            return await _verify_api_key(session)
        else:
            async with get_async_session_context() as db_session:
                return await _verify_api_key(db_session)
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    async def _verify_mfa_code(
        self,
        user_id: UUID,
        code: str,
        session: AsyncSession
    ) -> bool:
        """Verify MFA code."""
        try:
            # Get user MFA data
            user_result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user or not user.mfa_secret:
                return False
            
            # Decrypt secret
            secret = await self.encryption_service.decrypt_sensitive_data(user.mfa_secret, user_id)
            
            # Verify TOTP code
            totp = pyotp.TOTP(secret)
            if totp.verify(code, valid_window=1):
                return True
            
            # Check backup codes
            if user.mfa_backup_codes:
                backup_data = await self.encryption_service.decrypt_json(user.mfa_backup_codes, user_id)
                backup_codes = backup_data.get("codes", [])
                
                if code in backup_codes:
                    # Remove used backup code
                    backup_codes.remove(code)
                    user.mfa_backup_codes = await self.encryption_service.encrypt_json(
                        {"codes": backup_codes}, user_id
                    )
                    await session.commit()
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"MFA verification failed: {e}")
            return False
    
    async def _create_user_session(
        self,
        user_id: UUID,
        ip_address: str,
        user_agent: str,
        refresh_token: str,
        session: AsyncSession
    ) -> UUID:
        """Create user session."""
        user_session = UserSession(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            refresh_token_hash=self._hash_token(refresh_token),
            expires_at=datetime.utcnow() + timedelta(days=self.refresh_token_expire_days),
            is_active=True
        )
        
        session.add(user_session)
        await session.commit()
        await session.refresh(user_session)
        
        return user_session.id
    
    async def _check_login_rate_limit(
        self,
        email: str,
        ip_address: str,
        session: AsyncSession
    ) -> None:
        """Check login rate limiting."""
        # Check failed attempts in last hour
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        failed_attempts = await session.execute(
            select(LoginAttempt).where(
                and_(
                    or_(
                        LoginAttempt.email == email,
                        LoginAttempt.ip_address == ip_address
                    ),
                    LoginAttempt.success == False,
                    LoginAttempt.created_at > one_hour_ago
                )
            )
        )
        
        attempt_count = len(failed_attempts.scalars().all())
        
        if attempt_count >= self.max_login_attempts:
            raise AccountLockedError("Too many failed login attempts. Please try again later.")
    
    async def _is_account_locked(self, user_id: UUID, session: AsyncSession) -> bool:
        """Check if account is locked."""
        lockout_time = datetime.utcnow() - timedelta(minutes=self.lockout_duration_minutes)
        
        failed_attempts = await session.execute(
            select(LoginAttempt).where(
                and_(
                    LoginAttempt.user_id == user_id,
                    LoginAttempt.success == False,
                    LoginAttempt.created_at > lockout_time
                )
            )
        )
        
        return len(failed_attempts.scalars().all()) >= self.max_login_attempts
    
    async def _log_failed_login(
        self,
        email: str,
        ip_address: str,
        reason: str,
        session: AsyncSession
    ) -> None:
        """Log failed login attempt."""
        login_attempt = LoginAttempt(
            email=email,
            ip_address=ip_address,
            success=False,
            failure_reason=reason
        )
        
        session.add(login_attempt)
        await session.commit()
    
    async def _clear_failed_login_attempts(
        self,
        user_id: UUID,
        session: AsyncSession
    ) -> None:
        """Clear failed login attempts for user."""
        await session.execute(
            update(LoginAttempt)
            .where(LoginAttempt.user_id == user_id)
            .values(cleared=True)
        )
        await session.commit()
    
    async def _log_security_event(
        self,
        user_id: UUID,
        event_type: str,
        metadata: Dict[str, Any],
        session: AsyncSession
    ) -> None:
        """Log security event."""
        security_event = SecurityEvent(
            user_id=user_id,
            event_type=event_type,
            metadata=metadata
        )
        
        session.add(security_event)
        await session.commit()
    
    def _hash_token(self, token: str) -> str:
        """Hash token for storage."""
        return hashlib.sha256(token.encode()).hexdigest()


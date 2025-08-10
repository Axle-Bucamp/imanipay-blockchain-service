"""
Pydantic schemas for ImaniPay Blockchain Service.

This module defines all request/response models and data validation schemas
for the payment platform API endpoints.
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator, EmailStr, ConfigDict
from pydantic.types import PositiveFloat, PositiveInt
from app.schemas import BaseSchema

# ============================================================================
# Authentication Schemas
# ============================================================================

class LoginRequest(BaseSchema):
    """Schema for login requests."""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")
    remember_me: bool = Field(default=False, description="Remember login session")


class TokenResponse(BaseSchema):
    """Schema for authentication token response."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class RefreshTokenRequest(BaseSchema):
    """Schema for token refresh requests."""
    refresh_token: str = Field(..., description="Refresh token")


class PasswordChangeRequest(BaseSchema):
    """Schema for password change requests."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")


class PasswordResetRequest(BaseSchema):
    """Schema for password reset requests."""
    email: EmailStr = Field(..., description="User email")


class PasswordResetConfirm(BaseSchema):
    """Schema for password reset confirmation."""
    token: str = Field(..., description="Reset token")
    new_password: str = Field(..., min_length=8, description="New password")

# ============================================================================
# Webhook and Event Schemas
# ============================================================================

class WebhookEvent(BaseSchema):
    """Schema for webhook event data."""
    event_type: str = Field(..., description="Event type")
    event_id: str = Field(..., description="Unique event ID")
    timestamp: datetime = Field(..., description="Event timestamp")
    data: Dict[str, Any] = Field(..., description="Event data")
    signature: Optional[str] = Field(None, description="Event signature")


class NotificationPreferences(BaseSchema):
    """Schema for user notification preferences."""
    email_notifications: bool = Field(default=True)
    sms_notifications: bool = Field(default=True)
    push_notifications: bool = Field(default=True)
    transaction_alerts: bool = Field(default=True)
    security_alerts: bool = Field(default=True)
    marketing_emails: bool = Field(default=False)
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

from pydantic import BaseModel, Field, validator, EmailStr, ConfigDict, constr
from pydantic.types import PositiveFloat, PositiveInt
from app.schemas import BaseSchema, UserStatus, KYCStatus, TimestampMixin

# ============================================================================
# User Management Schemas
# ============================================================================

class UserCreate(BaseSchema):
    """Schema for user registration."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    phone: Optional[str] = Field(None, description="Phone number with country code")
    first_name: Optional[str] = Field(None, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, max_length=100, description="Last name")
    country: Optional[str] = Field(None, max_length=3, description="Country code (ISO 3166-1 alpha-3)")
    
    @validator('phone')
    def validate_phone(cls, v):
        if v and not v.startswith('+'):
            raise ValueError('Phone number must include country code starting with +')
        return v


class UserUpdate(BaseSchema):
    """Schema for user profile updates."""
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None)
    preferred_language: Optional[str] = Field(None, max_length=10)
    timezone: Optional[str] = Field(None, max_length=50)


class UserProfile(BaseSchema):
    """Schema for detailed user profile."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    nationality: Optional[str] = None
    country_of_residence: Optional[str] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    occupation: Optional[str] = None
    employer: Optional[str] = None
    annual_income: Optional[Decimal] = None


class UserResponse(BaseSchema, TimestampMixin):
    """Schema for user response data."""
    id: UUID
    email: EmailStr
    phone: Optional[str] = None
    status: UserStatus
    kyc_status: KYCStatus
    email_verified: bool
    phone_verified: bool
    two_factor_enabled: bool
    preferred_language: str
    timezone: str
    profile: Optional[UserProfile] = None



# --- Authentication ---
class UserLogin(BaseModel):
    email: EmailStr
    password: constr(min_length=8)
    mfa_code: Optional[str] = None


class UserRegistration(BaseModel):
    email: EmailStr
    password: constr(min_length=8)
    full_name: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    session_id: str


# --- MFA ---
class MFASetupResponse(BaseModel):
    secret: str
    qr_code: bytes  # raw PNG data
    backup_codes: List[str]
    provisioning_uri: str


class MFAVerificationRequest(BaseModel):
    mfa_code: str
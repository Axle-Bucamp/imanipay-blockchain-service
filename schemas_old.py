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


# ============================================================================
# Enumerations
# ============================================================================

class UserStatus(str, Enum):
    """User account status enumeration."""
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"
    BANNED = "banned"


class KYCStatus(str, Enum):
    """KYC verification status enumeration."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class TransactionType(str, Enum):
    """Transaction type enumeration."""
    FIAT_TO_CRYPTO = "fiat_to_crypto"
    CRYPTO_TO_FIAT = "crypto_to_fiat"
    CRYPTO_TO_CRYPTO = "crypto_to_crypto"
    CROSS_BORDER_PAYMENT = "cross_border_payment"
    WALLET_TRANSFER = "wallet_transfer"
    FEE_PAYMENT = "fee_payment"


class TransactionStatus(str, Enum):
    """Transaction status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethodType(str, Enum):
    """Payment method type enumeration."""
    BANK_ACCOUNT = "bank_account"
    CARD = "card"
    MOBILE_MONEY = "mobile_money"
    CASH_PICKUP = "cash_pickup"
    CRYPTO_WALLET = "crypto_wallet"


class WalletType(str, Enum):
    """Wallet type enumeration."""
    STANDARD = "standard"
    MULTISIG = "multisig"
    HARDWARE = "hardware"
    CUSTODIAL = "custodial"
    SMART_CONTRACT = "smart_contract"


class RiskLevel(str, Enum):
    """Risk level enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================================
# Base Models
# ============================================================================

class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    
    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v),
        }
    )


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""
    page: PositiveInt = Field(default=1, description="Page number")
    size: PositiveInt = Field(default=20, le=100, description="Page size")
    
    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.size


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""
    items: List[Any] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Page size")
    pages: int = Field(..., description="Total number of pages")
    
    @validator('pages', pre=True, always=True)
    def calculate_pages(cls, v, values):
        total = values.get('total', 0)
        size = values.get('size', 1)
        return (total + size - 1) // size if total > 0 else 0


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
# Wallet Management Schemas
# ============================================================================

class WalletCreate(BaseSchema):
    """Schema for wallet creation."""
    name: Optional[str] = Field(None, max_length=100, description="Wallet name")
    wallet_type: WalletType = Field(default=WalletType.STANDARD, description="Wallet type")
    is_multisig: bool = Field(default=False, description="Enable multi-signature")
    multisig_threshold: Optional[int] = Field(None, description="Multi-signature threshold")
    multisig_addresses: Optional[List[str]] = Field(None, description="Multi-signature addresses")


class WalletResponse(BaseSchema, TimestampMixin):
    """Schema for wallet response data."""
    id: UUID
    user_id: UUID
    address: str
    wallet_type: WalletType
    status: str
    name: Optional[str] = None
    is_multisig: bool
    multisig_threshold: Optional[int] = None
    algo_balance: int  # in microAlgos
    last_used_at: Optional[datetime] = None


class AssetBalance(BaseSchema):
    """Schema for asset balance information."""
    asset_id: int = Field(..., description="Algorand Asset ID (0 for ALGO)")
    asset_name: Optional[str] = Field(None, description="Asset name")
    asset_unit_name: Optional[str] = Field(None, description="Asset unit name")
    balance: int = Field(..., description="Balance in smallest unit")
    decimals: int = Field(default=6, description="Asset decimal places")
    frozen: bool = Field(default=False, description="Asset frozen status")
    
    @property
    def formatted_balance(self) -> Decimal:
        """Get formatted balance as decimal."""
        return Decimal(self.balance) / (10 ** self.decimals)


class WalletBalanceResponse(BaseSchema):
    """Schema for wallet balance response."""
    wallet_id: UUID
    address: str
    algo_balance: int
    assets: List[AssetBalance]
    total_value_usd: Optional[Decimal] = None
    last_updated: datetime


class AssetOptInRequest(BaseSchema):
    """Schema for asset opt-in requests."""
    asset_id: int = Field(..., description="Asset ID to opt into")


# ============================================================================
# Transaction Schemas
# ============================================================================

class TransactionCreate(BaseSchema):
    """Schema for transaction creation."""
    transaction_type: TransactionType
    amount: PositiveFloat = Field(..., description="Transaction amount")
    currency: str = Field(..., max_length=10, description="Currency code")
    destination_address: Optional[str] = Field(None, description="Destination wallet address")
    destination_external_id: Optional[str] = Field(None, description="External destination ID")
    payment_method_id: Optional[UUID] = Field(None, description="Payment method ID")
    description: Optional[str] = Field(None, max_length=500, description="Transaction description")
    reference: Optional[str] = Field(None, max_length=255, description="External reference")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class TransactionStep(BaseSchema):
    """Schema for transaction step information."""
    step_number: int
    step_type: str
    status: str
    description: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class TransactionResponse(BaseSchema, TimestampMixin):
    """Schema for transaction response data."""
    id: UUID
    user_id: UUID
    transaction_type: TransactionType
    status: TransactionStatus
    amount: Decimal
    currency: str
    fee_amount: Optional[Decimal] = None
    fee_currency: Optional[str] = None
    exchange_rate: Optional[Decimal] = None
    source_wallet_id: Optional[UUID] = None
    destination_wallet_id: Optional[UUID] = None
    blockchain_transaction_id: Optional[str] = None
    payment_processor: Optional[str] = None
    processor_transaction_id: Optional[str] = None
    risk_score: int
    description: Optional[str] = None
    reference: Optional[str] = None
    steps: List[TransactionStep] = []
    initiated_at: datetime
    confirmed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TransactionListResponse(PaginatedResponse):
    """Schema for paginated transaction list."""
    items: List[TransactionResponse]


# ============================================================================
# Payment Method Schemas
# ============================================================================

class BankAccountCreate(BaseSchema):
    """Schema for bank account creation."""
    account_number: str = Field(..., description="Bank account number")
    routing_number: str = Field(..., description="Bank routing number")
    bank_name: str = Field(..., max_length=255, description="Bank name")
    account_type: str = Field(..., description="Account type")
    account_holder_name: str = Field(..., max_length=255, description="Account holder name")


class CardCreate(BaseSchema):
    """Schema for card creation."""
    card_number: str = Field(..., description="Card number")
    expiry_month: int = Field(..., ge=1, le=12, description="Expiry month")
    expiry_year: int = Field(..., description="Expiry year")
    cvv: str = Field(..., min_length=3, max_length=4, description="CVV code")
    cardholder_name: str = Field(..., max_length=255, description="Cardholder name")


class MobileMoneyCreate(BaseSchema):
    """Schema for mobile money account creation."""
    mobile_number: str = Field(..., description="Mobile number")
    provider: str = Field(..., description="Mobile money provider")
    country: str = Field(..., max_length=3, description="Country code")


class PaymentMethodCreate(BaseSchema):
    """Schema for payment method creation."""
    method_type: PaymentMethodType
    name: str = Field(..., max_length=100, description="Payment method name")
    bank_account: Optional[BankAccountCreate] = None
    card: Optional[CardCreate] = None
    mobile_money: Optional[MobileMoneyCreate] = None


class PaymentMethodResponse(BaseSchema, TimestampMixin):
    """Schema for payment method response."""
    id: UUID
    user_id: UUID
    method_type: PaymentMethodType
    name: str
    status: str
    is_verified: bool
    last_four: Optional[str] = None  # Last 4 digits for cards/accounts
    bank_name: Optional[str] = None
    card_brand: Optional[str] = None
    mobile_provider: Optional[str] = None
    last_used_at: Optional[datetime] = None


# ============================================================================
# Payment Processing Schemas
# ============================================================================

class FiatToCryptoRequest(BaseSchema):
    """Schema for fiat to crypto conversion requests."""
    amount: PositiveFloat = Field(..., description="Fiat amount to convert")
    fiat_currency: str = Field(..., max_length=3, description="Fiat currency code")
    crypto_currency: str = Field(..., max_length=10, description="Target crypto currency")
    payment_method_id: UUID = Field(..., description="Payment method ID")
    destination_wallet_id: Optional[UUID] = Field(None, description="Destination wallet ID")


class CryptoToFiatRequest(BaseSchema):
    """Schema for crypto to fiat conversion requests."""
    amount: PositiveFloat = Field(..., description="Crypto amount to convert")
    crypto_currency: str = Field(..., max_length=10, description="Source crypto currency")
    fiat_currency: str = Field(..., max_length=3, description="Target fiat currency")
    source_wallet_id: UUID = Field(..., description="Source wallet ID")
    payment_method_id: UUID = Field(..., description="Payout method ID")


class CrossBorderPaymentRequest(BaseSchema):
    """Schema for cross-border payment requests."""
    amount: PositiveFloat = Field(..., description="Payment amount")
    source_currency: str = Field(..., max_length=3, description="Source currency")
    destination_currency: str = Field(..., max_length=3, description="Destination currency")
    recipient_info: Dict[str, Any] = Field(..., description="Recipient information")
    payment_method_id: UUID = Field(..., description="Payment method ID")
    delivery_method: str = Field(..., description="Delivery method")


class ExchangeRate(BaseSchema):
    """Schema for exchange rate information."""
    base_currency: str = Field(..., max_length=10)
    quote_currency: str = Field(..., max_length=10)
    rate: Decimal = Field(..., description="Exchange rate")
    bid_rate: Optional[Decimal] = None
    ask_rate: Optional[Decimal] = None
    spread: Optional[Decimal] = None
    source: str = Field(..., description="Rate source")
    timestamp: datetime = Field(..., description="Rate timestamp")


class FeeCalculation(BaseSchema):
    """Schema for fee calculation response."""
    base_fee: Decimal = Field(..., description="Base transaction fee")
    network_fee: Decimal = Field(..., description="Blockchain network fee")
    processor_fee: Decimal = Field(..., description="Payment processor fee")
    exchange_fee: Decimal = Field(..., description="Currency exchange fee")
    total_fee: Decimal = Field(..., description="Total fee amount")
    fee_currency: str = Field(..., description="Fee currency")


class ConversionQuote(BaseSchema):
    """Schema for conversion quote response."""
    source_amount: Decimal
    source_currency: str
    destination_amount: Decimal
    destination_currency: str
    exchange_rate: Decimal
    fees: FeeCalculation
    expires_at: datetime
    quote_id: str


# ============================================================================
# KYC and Compliance Schemas
# ============================================================================

class KYCDocumentUpload(BaseSchema):
    """Schema for KYC document upload."""
    document_type: str = Field(..., description="Document type")
    file_name: str = Field(..., description="Original file name")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type")


class KYCVerificationRequest(BaseSchema):
    """Schema for KYC verification request."""
    verification_level: str = Field(..., description="Verification level")
    documents: List[KYCDocumentUpload] = Field(..., description="Uploaded documents")
    personal_info: Dict[str, Any] = Field(..., description="Personal information")


class KYCVerificationResponse(BaseSchema, TimestampMixin):
    """Schema for KYC verification response."""
    id: UUID
    user_id: UUID
    verification_level: str
    status: KYCStatus
    provider: str
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    rejection_reasons: List[str] = []


class RiskAssessment(BaseSchema):
    """Schema for risk assessment response."""
    user_id: UUID
    risk_score: int = Field(..., ge=0, le=100, description="Risk score (0-100)")
    risk_level: RiskLevel
    risk_factors: List[str] = Field(..., description="Identified risk factors")
    assessment_date: datetime
    next_review_date: Optional[datetime] = None


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


# ============================================================================
# Error Response Schemas
# ============================================================================

class ErrorDetail(BaseSchema):
    """Schema for error detail information."""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    field: Optional[str] = Field(None, description="Field that caused the error")


class ErrorResponse(BaseSchema):
    """Schema for error responses."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[List[ErrorDetail]] = Field(None, description="Error details")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")


# ============================================================================
# Health Check and Status Schemas
# ============================================================================

class HealthCheck(BaseSchema):
    """Schema for health check response."""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Check timestamp")
    version: str = Field(..., description="Service version")
    uptime: int = Field(..., description="Uptime in seconds")
    
    
class ServiceStatus(BaseSchema):
    """Schema for individual service status."""
    name: str = Field(..., description="Service name")
    status: str = Field(..., description="Service status")
    response_time: Optional[float] = Field(None, description="Response time in ms")
    last_check: datetime = Field(..., description="Last check timestamp")


class SystemStatus(BaseSchema):
    """Schema for system status response."""
    overall_status: str = Field(..., description="Overall system status")
    services: List[ServiceStatus] = Field(..., description="Individual service statuses")
    timestamp: datetime = Field(..., description="Status check timestamp")


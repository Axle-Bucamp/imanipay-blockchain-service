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
from app.schemas import BaseSchema, PaymentMethodType, KYCStatus, TimestampMixin, RiskLevel

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



class SendPaymentRequest(BaseSchema):
    receiver_wallet_address: str
    amount: float
    asset_id: Optional[int] = 0  # 0 for ALGO, or specify ASA ID


class SendPaymentResponse(BaseSchema):
    sender_wallet_address: str
    receiver_wallet_address: str
    amount: float
    actual_payment_amount: float
    fee_amount: float
    params: Dict[str, Any]  # SuggestedParams details
    asset_id: Optional[int] = 0
    admin_wallet_address: str
    txid: str

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


"""
SQLAlchemy database models for ImaniPay Blockchain Service.

This module defines all database models and relationships for the payment platform.
"""

import enum
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum, ForeignKey, Integer, 
    Numeric, String, Text, ARRAY, JSON, Index, CheckConstraint,
    UniqueConstraint, BigInteger
)
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func


# ============================================================================
# Base Model and Mixins
# ============================================================================

Base = declarative_base()


class TimestampMixin:
    """Mixin for timestamp fields."""
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AuditMixin:
    """Mixin for audit fields."""
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    version = Column(Integer, default=1, nullable=False)


# ============================================================================
# Enumerations
# ============================================================================

class UserStatusEnum(enum.Enum):
    """User account status enumeration."""
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"
    BANNED = "banned"


class KYCStatusEnum(enum.Enum):
    """KYC verification status enumeration."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class GenderEnum(enum.Enum):
    """Gender enumeration."""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class DeviceTypeEnum(enum.Enum):
    """Device type enumeration."""
    WEB = "web"
    MOBILE_IOS = "mobile_ios"
    MOBILE_ANDROID = "mobile_android"
    API = "api"
    OTHER = "other"


class LoginMethodEnum(enum.Enum):
    """Login method enumeration."""
    PASSWORD = "password"
    SSO = "sso"
    BIOMETRIC = "biometric"
    HARDWARE_KEY = "hardware_key"
    MAGIC_LINK = "magic_link"


class TransactionTypeEnum(enum.Enum):
    """Transaction type enumeration."""
    FIAT_TO_CRYPTO = "fiat_to_crypto"
    CRYPTO_TO_FIAT = "crypto_to_fiat"
    CRYPTO_TO_CRYPTO = "crypto_to_crypto"
    CROSS_BORDER_PAYMENT = "cross_border_payment"
    WALLET_TRANSFER = "wallet_transfer"
    FEE_PAYMENT = "fee_payment"


class TransactionStatusEnum(enum.Enum):
    """Transaction status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethodTypeEnum(enum.Enum):
    """Payment method type enumeration."""
    BANK_ACCOUNT = "bank_account"
    CARD = "card"
    MOBILE_MONEY = "mobile_money"
    CASH_PICKUP = "cash_pickup"
    CRYPTO_WALLET = "crypto_wallet"


class WalletTypeEnum(enum.Enum):
    """Wallet type enumeration."""
    STANDARD = "standard"
    MULTISIG = "multisig"
    HARDWARE = "hardware"
    CUSTODIAL = "custodial"
    SMART_CONTRACT = "smart_contract"


class WalletStatusEnum(enum.Enum):
    """Wallet status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    FROZEN = "frozen"
    CLOSED = "closed"


class RiskLevelEnum(enum.Enum):
    """Risk level enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================================
# User Management Models
# ============================================================================

class User(Base, TimestampMixin, AuditMixin):
    """User account model."""
    
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(50), nullable=True, index=True)
    password_hash = Column(String(255), nullable=False)
    salt = Column(String(255), nullable=False)
    
    # Status and verification
    status = Column(Enum(UserStatusEnum), default=UserStatusEnum.PENDING, nullable=False, index=True)
    kyc_status = Column(Enum(KYCStatusEnum), default=KYCStatusEnum.NOT_STARTED, nullable=False, index=True)
    risk_score = Column(Integer, default=0, nullable=False)
    
    # Authentication
    last_login_at = Column(DateTime(timezone=True), nullable=True, index=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # Verification flags
    email_verified = Column(Boolean, default=False, nullable=False)
    phone_verified = Column(Boolean, default=False, nullable=False)
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    two_factor_secret = Column(String(255), nullable=True)
    backup_codes = Column(ARRAY(String), nullable=True)
    
    # Preferences
    preferred_language = Column(String(10), default='en', nullable=False)
    timezone = Column(String(50), default='UTC', nullable=False)
    usr_metadata = Column(JSONB, default={}, nullable=False)
    
    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    wallets = relationship("Wallet", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user")
    payment_methods = relationship("PaymentMethod", back_populates="user", cascade="all, delete-orphan")
    kyc_verifications = relationship("KYCVerification", back_populates="user", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'", name="users_email_check"),
        CheckConstraint("phone IS NULL OR phone ~* '^\\+[1-9]\\d{1,14}$'", name="users_phone_check"),
        Index('idx_users_active', 'id', postgresql_where=status == UserStatusEnum.ACTIVE),
    )
    
    @validates('email')
    def validate_email(self, key, email):
        """Validate email format."""
        if '@' not in email:
            raise ValueError("Invalid email format")
        return email.lower()


class UserProfile(Base, TimestampMixin, AuditMixin):
    """User profile model with personal information."""
    
    __tablename__ = "user_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    
    # Personal information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    middle_name = Column(String(100), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(Enum(GenderEnum), nullable=True)
    
    # Location information
    nationality = Column(String(3), nullable=True)  # ISO 3166-1 alpha-3
    country_of_residence = Column(String(3), nullable=True)  # ISO 3166-1 alpha-3
    address_line_1 = Column(String(255), nullable=True)
    address_line_2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state_province = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(3), nullable=True)  # ISO 3166-1 alpha-3
    
    # Professional information
    occupation = Column(String(100), nullable=True)
    employer = Column(String(255), nullable=True)
    annual_income = Column(Numeric(15, 2), nullable=True)
    source_of_funds = Column(Text, nullable=True)
    purpose_of_account = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="profile")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_profiles_user_id', 'user_id'),
        Index('idx_user_profiles_country', 'country'),
        Index('idx_user_profiles_nationality', 'nationality'),
    )


class UserSession(Base, TimestampMixin):
    """User session model for authentication tracking."""
    
    __tablename__ = "user_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Session tokens
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    refresh_token = Column(String(255), unique=True, nullable=True)
    
    # Device information
    device_id = Column(String(255), nullable=True)
    device_type = Column(Enum(DeviceTypeEnum), nullable=True)
    device_name = Column(String(255), nullable=True)
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Location information
    location_country = Column(String(3), nullable=True)
    location_city = Column(String(100), nullable=True)
    
    # Session status
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_activity_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    
    # Security information
    login_method = Column(Enum(LoginMethodEnum), nullable=True)
    mfa_verified = Column(Boolean, default=False, nullable=False)
    risk_score = Column(Integer, default=0, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint('expires_at > created_at', name='user_sessions_expires_check'),
        Index('idx_user_sessions_user_id', 'user_id'),
        Index('idx_user_sessions_active', 'user_id', 'is_active', postgresql_where=is_active == True),
        Index('idx_user_sessions_expires', 'expires_at'),
    )


# ============================================================================
# Wallet Management Models
# ============================================================================

class Wallet(Base, TimestampMixin, AuditMixin):
    """Algorand wallet model."""
    
    __tablename__ = "wallets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Wallet identification
    address = Column(String(58), unique=True, nullable=False, index=True)
    wallet_type = Column(Enum(WalletTypeEnum), default=WalletTypeEnum.STANDARD, nullable=False)
    status = Column(Enum(WalletStatusEnum), default=WalletStatusEnum.ACTIVE, nullable=False)
    
    # Multi-signature configuration
    is_multisig = Column(Boolean, default=False, nullable=False)
    multisig_threshold = Column(Integer, nullable=True)
    multisig_addresses = Column(ARRAY(String), nullable=True)
    
    # Key management (encrypted)
    encrypted_private_key = Column(Text, nullable=True)
    key_derivation_path = Column(String(255), nullable=True)
    public_key = Column(String(64), nullable=True)
    
    # Wallet metadata
    name = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    tags = Column(ARRAY(String), nullable=True)
    
    # Balance tracking (cached)
    algo_balance = Column(BigInteger, default=0, nullable=False)
    last_balance_update = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="wallets")
    assets = relationship("WalletAsset", back_populates="wallet", cascade="all, delete-orphan")
    source_transactions = relationship("Transaction", foreign_keys="Transaction.source_wallet_id")
    destination_transactions = relationship("Transaction", foreign_keys="Transaction.destination_wallet_id")
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint("length(address) = 58", name="wallets_address_check"),
        CheckConstraint(
            "(is_multisig = FALSE) OR (is_multisig = TRUE AND multisig_threshold > 0 AND array_length(multisig_addresses, 1) >= multisig_threshold)",
            name="wallets_multisig_check"
        ),
        Index('idx_wallets_user_id', 'user_id'),
        Index('idx_wallets_status', 'status'),
        Index('idx_wallets_type', 'wallet_type'),
        Index('idx_wallets_last_used', 'last_used_at'),
    )


class WalletAsset(Base, TimestampMixin):
    """Wallet asset holdings model."""
    
    __tablename__ = "wallet_assets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey('wallets.id', ondelete='CASCADE'), nullable=False)
    
    # Asset identification
    asset_id = Column(BigInteger, nullable=False)  # 0 for ALGO
    asset_name = Column(String(32), nullable=True)
    asset_unit_name = Column(String(8), nullable=True)
    asset_decimals = Column(Integer, default=6, nullable=False)
    
    # Balance information
    balance = Column(BigInteger, default=0, nullable=False)
    frozen = Column(Boolean, default=False, nullable=False)
    opted_in = Column(Boolean, default=True, nullable=False)
    
    # Asset metadata
    asset_url = Column(String(255), nullable=True)
    asset_metadata_hash = Column(String(64), nullable=True)
    manager_address = Column(String(58), nullable=True)
    reserve_address = Column(String(58), nullable=True)
    freeze_address = Column(String(58), nullable=True)
    clawback_address = Column(String(58), nullable=True)
    
    # Tracking
    first_opted_in_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    last_transaction_at = Column(DateTime(timezone=True), nullable=True)
    last_balance_update = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    
    # Relationships
    wallet = relationship("Wallet", back_populates="assets")
    
    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('wallet_id', 'asset_id', name='wallet_assets_unique'),
        CheckConstraint('balance >= 0', name='wallet_assets_balance_check'),
        Index('idx_wallet_assets_wallet_id', 'wallet_id'),
        Index('idx_wallet_assets_asset_id', 'asset_id'),
        Index('idx_wallet_assets_balance', 'wallet_id', 'balance', postgresql_where=balance > 0),
    )


# ============================================================================
# Transaction Models
# ============================================================================

class Transaction(Base, TimestampMixin, AuditMixin):
    """Transaction model for all payment operations."""
    
    __tablename__ = "transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    # Transaction classification
    transaction_type = Column(Enum(TransactionTypeEnum), nullable=False, index=True)
    status = Column(Enum(TransactionStatusEnum), default=TransactionStatusEnum.PENDING, nullable=False, index=True)
    
    # Amount and currency information
    amount = Column(Numeric(20, 8), nullable=False)
    currency = Column(String(10), nullable=False)
    fee_amount = Column(Numeric(20, 8), default=0, nullable=False)
    fee_currency = Column(String(10), nullable=True)
    
    # Exchange rate information
    exchange_rate = Column(Numeric(20, 8), nullable=True)
    exchange_rate_source = Column(String(100), nullable=True)
    exchange_rate_timestamp = Column(DateTime(timezone=True), nullable=True)
    
    # Source and destination
    source_wallet_id = Column(UUID(as_uuid=True), ForeignKey('wallets.id'), nullable=True)
    destination_wallet_id = Column(UUID(as_uuid=True), ForeignKey('wallets.id'), nullable=True)
    source_external_id = Column(String(255), nullable=True)
    destination_external_id = Column(String(255), nullable=True)
    
    # Blockchain information
    blockchain_network = Column(String(50), nullable=True)
    blockchain_transaction_id = Column(String(255), nullable=True, index=True)
    block_number = Column(BigInteger, nullable=True)
    block_timestamp = Column(DateTime(timezone=True), nullable=True)
    gas_used = Column(BigInteger, nullable=True)
    gas_price = Column(BigInteger, nullable=True)
    
    # Payment processor information
    payment_processor = Column(String(100), nullable=True)
    processor_transaction_id = Column(String(255), nullable=True, index=True)
    processor_reference = Column(String(255), nullable=True)
    processor_status = Column(String(50), nullable=True)
    
    # Risk and compliance
    risk_score = Column(Integer, default=0, nullable=False)
    compliance_status = Column(String(50), default='pending', nullable=False)
    aml_screening_required = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    description = Column(Text, nullable=True)
    reference = Column(String(255), nullable=True)
    metadata = Column(JSONB, default={}, nullable=False)
    
    # Timestamps
    initiated_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="transactions")
    source_wallet = relationship("Wallet", foreign_keys=[source_wallet_id])
    destination_wallet = relationship("Wallet", foreign_keys=[destination_wallet_id])
    steps = relationship("TransactionStep", back_populates="transaction", cascade="all, delete-orphan")
    aml_screenings = relationship("AMLScreening", back_populates="transaction")
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint('amount > 0', name='transactions_amount_check'),
        CheckConstraint('fee_amount >= 0', name='transactions_fee_check'),
        CheckConstraint(
            'source_wallet_id IS NOT NULL OR source_external_id IS NOT NULL',
            name='transactions_wallet_check'
        ),
        Index('idx_transactions_user_id', 'user_id'),
        Index('idx_transactions_user_status', 'user_id', 'status'),
        Index('idx_transactions_user_type', 'user_id', 'transaction_type'),
        Index('idx_transactions_status_created', 'status', 'created_at'),
    )


class TransactionStep(Base, TimestampMixin):
    """Transaction step model for multi-step transaction tracking."""
    
    __tablename__ = "transaction_steps"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey('transactions.id', ondelete='CASCADE'), nullable=False)
    
    # Step identification
    step_number = Column(Integer, nullable=False)
    step_type = Column(String(50), nullable=False)
    status = Column(String(50), default='pending', nullable=False)
    
    # Step details
    description = Column(Text, nullable=True)
    processor = Column(String(100), nullable=True)
    external_reference = Column(String(255), nullable=True)
    
    # Amount information
    amount = Column(Numeric(20, 8), nullable=True)
    currency = Column(String(10), nullable=True)
    fee_amount = Column(Numeric(20, 8), default=0, nullable=True)
    
    # Execution details
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    
    # Error information
    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    error_details = Column(JSONB, nullable=True)
    
    # Metadata
    step_data = Column(JSONB, default={}, nullable=False)
    
    # Relationships
    transaction = relationship("Transaction", back_populates="steps")
    
    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('transaction_id', 'step_number', name='transaction_steps_unique'),
        CheckConstraint('retry_count <= max_retries', name='transaction_steps_retry_check'),
        Index('idx_transaction_steps_transaction_id', 'transaction_id'),
        Index('idx_transaction_steps_status', 'status'),
        Index('idx_transaction_steps_type', 'step_type'),
    )


# ============================================================================
# Payment Method Models
# ============================================================================

class PaymentMethod(Base, TimestampMixin, AuditMixin):
    """Payment method model for fiat on/off-ramps."""
    
    __tablename__ = "payment_methods"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Method classification
    method_type = Column(Enum(PaymentMethodTypeEnum), nullable=False, index=True)
    status = Column(String(50), default='active', nullable=False, index=True)
    
    # Method details
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Bank account details (encrypted)
    encrypted_account_number = Column(Text, nullable=True)
    encrypted_routing_number = Column(Text, nullable=True)
    bank_name = Column(String(255), nullable=True)
    bank_country = Column(String(3), nullable=True)
    account_type = Column(String(50), nullable=True)
    
    # Card details (encrypted, PCI compliant)
    encrypted_card_number = Column(Text, nullable=True)
    card_last_four = Column(String(4), nullable=True)
    card_brand = Column(String(50), nullable=True)
    card_type = Column(String(50), nullable=True)
    expiry_month = Column(Integer, nullable=True)
    expiry_year = Column(Integer, nullable=True)
    
    # Mobile money details
    mobile_provider = Column(String(100), nullable=True)
    mobile_number = Column(String(50), nullable=True)
    mobile_country = Column(String(3), nullable=True)
    
    # Verification status
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_method = Column(String(100), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Usage tracking
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)
    
    # Limits
    daily_limit = Column(Numeric(15, 2), nullable=True)
    monthly_limit = Column(Numeric(15, 2), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="payment_methods")
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint(
            "method_type != 'card' OR (encrypted_card_number IS NOT NULL AND card_last_four IS NOT NULL AND expiry_month BETWEEN 1 AND 12 AND expiry_year >= EXTRACT(YEAR FROM NOW()))",
            name="payment_methods_card_check"
        ),
        Index('idx_payment_methods_user_id', 'user_id'),
        Index('idx_payment_methods_type', 'method_type'),
        Index('idx_payment_methods_verified', 'user_id', 'is_verified', postgresql_where=is_verified == True),
    )


class ExchangeRate(Base):
    """Exchange rate model for currency conversions."""
    
    __tablename__ = "exchange_rates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Currency pair
    base_currency = Column(String(10), nullable=False)
    quote_currency = Column(String(10), nullable=False)
    rate = Column(Numeric(20, 8), nullable=False)
    source = Column(String(100), nullable=False)
    
    # Rate metadata
    bid_rate = Column(Numeric(20, 8), nullable=True)
    ask_rate = Column(Numeric(20, 8), nullable=True)
    spread = Column(Numeric(10, 6), nullable=True)
    volume_24h = Column(Numeric(20, 2), nullable=True)
    
    # Validity
    valid_from = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Audit
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint('rate > 0', name='exchange_rates_rate_check'),
        CheckConstraint('valid_until IS NULL OR valid_until > valid_from', name='exchange_rates_validity_check'),
        Index('idx_exchange_rates_pair', 'base_currency', 'quote_currency'),
        Index('idx_exchange_rates_active', 'base_currency', 'quote_currency', 'is_active', postgresql_where=is_active == True),
        Index('idx_exchange_rates_valid_from', 'valid_from'),
        Index('idx_exchange_rates_source', 'source'),
    )


# ============================================================================
# KYC and Compliance Models
# ============================================================================

class KYCVerification(Base, TimestampMixin, AuditMixin):
    """KYC verification model."""
    
    __tablename__ = "kyc_verifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Verification details
    verification_level = Column(String(50), nullable=False)
    status = Column(Enum(KYCStatusEnum), default=KYCStatusEnum.PENDING_REVIEW, nullable=False, index=True)
    provider = Column(String(100), nullable=False)
    provider_reference = Column(String(255), nullable=True)
    
    # Timestamps
    submitted_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Verification data
    documents_submitted = Column(JSONB, default=[], nullable=False)
    verification_data = Column(JSONB, default={}, nullable=False)
    rejection_reasons = Column(ARRAY(String), nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    
    # Risk assessment
    risk_score = Column(Integer, nullable=True)
    risk_factors = Column(JSONB, default={}, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="kyc_verifications")
    
    # Indexes
    __table_args__ = (
        Index('idx_kyc_verifications_user_id', 'user_id'),
        Index('idx_kyc_verifications_provider', 'provider'),
        Index('idx_kyc_verifications_submitted', 'submitted_at'),
    )


class AMLScreening(Base, TimestampMixin):
    """AML screening model."""
    
    __tablename__ = "aml_screenings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey('transactions.id', ondelete='CASCADE'), nullable=True)
    
    # Screening details
    screening_type = Column(String(50), nullable=False)
    status = Column(String(50), default='pending', nullable=False, index=True)
    provider = Column(String(100), nullable=False)
    provider_reference = Column(String(255), nullable=True)
    
    # Screening data
    screening_data = Column(JSONB, default={}, nullable=False)
    matches = Column(JSONB, default=[], nullable=False)
    risk_score = Column(Integer, nullable=True)
    risk_level = Column(Enum(RiskLevelEnum), nullable=True, index=True)
    
    # Resolution
    resolution = Column(String(50), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    resolved_by = Column(UUID(as_uuid=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User")
    transaction = relationship("Transaction", back_populates="aml_screenings")
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint(
            "(user_id IS NOT NULL AND transaction_id IS NULL) OR (user_id IS NULL AND transaction_id IS NOT NULL)",
            name="aml_screenings_entity_check"
        ),
        Index('idx_aml_screenings_user_id', 'user_id'),
        Index('idx_aml_screenings_transaction_id', 'transaction_id'),
    )


# ============================================================================
# Audit and Logging Models
# ============================================================================

class AuditLog(Base):
    """Audit log model for tracking all system activities."""
    
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey('user_sessions.id'), nullable=True)
    
    # Action details
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Request details
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    request_method = Column(String(10), nullable=True)
    request_path = Column(String(500), nullable=True)
    request_body = Column(JSONB, nullable=True)
    
    # Response details
    response_status = Column(Integer, nullable=True)
    response_body = Column(JSONB, nullable=True)
    
    # Change tracking
    old_values = Column(JSONB, nullable=True)
    new_values = Column(JSONB, nullable=True)
    
    # Risk and compliance
    risk_score = Column(Integer, nullable=True)
    compliance_flags = Column(ARRAY(String), nullable=True)
    
    # Metadata
    metadata = Column(JSONB, default={}, nullable=False)
    
    # Timestamp (immutable)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    
    # Partitioning key
    partition_date = Column(Date, nullable=False, default=func.current_date())
    
    # Indexes
    __table_args__ = (
        Index('idx_audit_logs_user_id', 'user_id', 'created_at'),
        Index('idx_audit_logs_action', 'action', 'created_at'),
        Index('idx_audit_logs_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_logs_ip', 'ip_address', 'created_at'),
    )


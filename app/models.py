"""
Simplified SQLAlchemy database models for ImaniPay Blockchain Service.

This module defines blockchain-focused database models without authentication.
"""

import enum
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import (
    ARRAY, UUID, Boolean, Column, Date, DateTime, Enum, ForeignKey, Integer, 
    Numeric, String, Text, JSON, Index, CheckConstraint,
    UniqueConstraint, BigInteger, TypeDecorator
)
# Use String for UUID in SQLite compatibility mode
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

# Import from correct schema module
from .schemas.enumerate import TransactionStatus as PydanticTransactionStatus
from app.schemas.base import AuditMixin
from sqlalchemy.dialects import postgresql

# ============================================================================
# Base Model and Mixins
# ============================================================================

Base = declarative_base()


class TimestampMixin:
    """Mixin for timestamp fields."""
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


# ============================================================================
# Enumerations
# ============================================================================

class TransactionTypeEnum(enum.Enum):
    """Transaction type enumeration."""
    ALGORAND_TRANSFER = "algorand_transfer"
    ASSET_TRANSFER = "asset_transfer"
    SMART_CONTRACT_CALL = "smart_contract_call"
    ESCROW_PAYMENT = "escrow_payment"
    MULTISIG_TRANSACTION = "multisig_transaction"
    BATCH_TRANSACTION = "batch_transaction"
    FIAT_TO_CRYPTO="escrow_payment" # TODO
    CRYPTO_TO_FIAT="escrow_payment" # TODO
    CROSS_BORDER_PAYMENT="escrow_payment" # TODO 
 
class TransactionStatusEnum(enum.Enum):
    """Transaction status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WalletTypeEnum(enum.Enum):
    """Wallet type enumeration."""
    STANDARD = "standard"
    MULTISIG = "multisig"
    SMART_CONTRACT = "smart_contract"
    ESCROW = "escrow"


class WalletStatusEnum(enum.Enum):
    """Wallet status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    FROZEN = "frozen"


class ContractTypeEnum(enum.Enum):
    """Smart contract type enumeration."""
    ESCROW = "escrow"
    MULTISIG = "multisig"
    BATCH_PROCESSOR = "batch_processor"
    PAYMENT_SPLITTER = "payment_splitter"


class ContractStatusEnum(enum.Enum):
    """Smart contract status enumeration."""
    DEPLOYED = "deployed"
    ACTIVE = "active"
    PAUSED = "paused"
    TERMINATED = "terminated"


class NetworkEnum(enum.Enum):
    """Blockchain network enumeration."""
    MAINNET = "mainnet"
    TESTNET = "testnet"
    BETANET = "betanet"
    LOCALNET = "localnet"

class IPNetwork(TypeDecorator):
    impl = postgresql.INET

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)

    def process_result_value(self, value, dialect):
        return str(value)

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


class PaymentMethodStatusEnum(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"

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


class PaymentMethodTypeEnum(enum.Enum):
    """Payment method type enumeration."""
    BANK_ACCOUNT = "bank_account"
    CARD = "card"
    MOBILE_MONEY = "mobile_money"
    CASH_PICKUP = "cash_pickup"
    CRYPTO_WALLET = "crypto_wallet"


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
    usr_metadata = Column(JSON, default={}, nullable=False)
    
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
    ip_address = Column(IPNetwork, nullable=True)
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
    error_details = Column(JSON, nullable=True)
    
    # Metadata
    step_data = Column(JSON, default={}, nullable=False)
    
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
# Wallet Management Models
# ============================================================================

class Wallet(Base, TimestampMixin):
    """Simplified wallet model focused on blockchain operations."""
    
    __tablename__ = "wallets"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    
    # Wallet identification
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    wallet_type = Column(Enum(WalletTypeEnum), default=WalletTypeEnum.STANDARD, nullable=False)
    status = Column(Enum(WalletStatusEnum), default=WalletStatusEnum.ACTIVE, nullable=False)
    
    # Algorand-specific fields
    algorand_address = Column(String(58), unique=True, nullable=False, index=True)
    encrypted_private_key = Column(Text, nullable=True)  # Encrypted with app key
    public_key = Column(String(64), nullable=False)
    
    # Multi-signature configuration
    multisig_threshold = Column(Integer, nullable=True)
    multisig_addresses = Column(JSON, nullable=True)  # Use JSON instead of ARRAY for SQLite compatibility
    
    # Network and configuration
    network = Column(Enum(NetworkEnum), default=NetworkEnum.TESTNET, nullable=False)
    wallet_metadata = Column(JSON, default={}, nullable=False)
    
    # Relationships
    transactions = relationship("Transaction", back_populates="wallet")
    contracts = relationship("SmartContract", back_populates="wallet")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("length(algorand_address) = 58", name="wallets_address_check"),
        CheckConstraint("multisig_threshold IS NULL OR multisig_threshold > 0", name="wallets_threshold_check"),
        Index('idx_wallets_address', 'algorand_address'),
        Index('idx_wallets_type_status', 'wallet_type', 'status'),
    )


# ============================================================================
# Transaction Models
# ============================================================================

class Transaction(Base, TimestampMixin):
    """Simplified transaction model for blockchain operations."""
    
    __tablename__ = "transactions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    wallet_id = Column(String(36), ForeignKey('wallets.id', ondelete='CASCADE'), nullable=False)

    # Transaction identification
    transaction_type = Column(Enum(TransactionTypeEnum), nullable=False)
    status = Column(Enum(TransactionStatusEnum), default=TransactionStatusEnum.PENDING, nullable=False, index=True)
    
    # Algorand transaction details
    algorand_tx_id = Column(String(52), unique=True, nullable=True, index=True)
    algorand_tx_hash = Column(String(64), nullable=True)
    block_number = Column(BigInteger, nullable=True)
    round_number = Column(BigInteger, nullable=True)
    
    # Transaction amounts and fees
    amount = Column(Numeric(20, 6), nullable=False)
    fee = Column(Numeric(20, 6), default=0, nullable=False)
    asset_id = Column(BigInteger, nullable=True)  # Algorand Asset ID (0 for ALGO)
    
    # Addresses
    from_address = Column(String(58), nullable=False)
    to_address = Column(String(58), nullable=False)
    
    # Transaction data
    note = Column(Text, nullable=True)
    application_args = Column(JSON, nullable=True)  # For smart contract calls
    
    # Network and confirmation
    network = Column(Enum(NetworkEnum), default=NetworkEnum.TESTNET, nullable=False)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    confirmation_count = Column(Integer, default=0, nullable=False)
    
    # Metadata
    transaction_metadata = Column(JSON, default={}, nullable=False)
    
    # Relationships
    wallet = relationship("Wallet", back_populates="transactions")
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint("amount >= 0", name="transactions_amount_check"),
        CheckConstraint("fee >= 0", name="transactions_fee_check"),
        CheckConstraint("length(from_address) = 58", name="transactions_from_address_check"),
        CheckConstraint("length(to_address) = 58", name="transactions_to_address_check"),
        Index('idx_transactions_wallet_id', 'wallet_id'),
        Index('idx_transactions_algorand_tx_id', 'algorand_tx_id'),
        Index('idx_transactions_status', 'status'),
        Index('idx_transactions_type', 'transaction_type'),
        Index('idx_transactions_addresses', 'from_address', 'to_address'),
    )


# ============================================================================
# Smart Contract Models
# ============================================================================

class SmartContract(Base, TimestampMixin):
    """Smart contract model for Algorand applications."""
    
    __tablename__ = "smart_contracts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    wallet_id = Column(String(36), ForeignKey('wallets.id', ondelete='CASCADE'), nullable=False)
    
    # Contract identification
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    contract_type = Column(Enum(ContractTypeEnum), nullable=False)
    status = Column(Enum(ContractStatusEnum), default=ContractStatusEnum.DEPLOYED, nullable=False)
    
    # Algorand application details
    app_id = Column(BigInteger, unique=True, nullable=True, index=True)
    app_address = Column(String(58), nullable=True)
    creator_address = Column(String(58), nullable=False)
    
    # Contract code and state
    approval_program = Column(Text, nullable=True)  # TEAL code
    clear_program = Column(Text, nullable=True)     # TEAL code
    global_state_schema = Column(JSON, nullable=True)
    local_state_schema = Column(JSON, nullable=True)
    
    # Contract configuration
    global_state = Column(JSON, default={}, nullable=False)
    local_state = Column(JSON, default={}, nullable=False)
    
    # Network and deployment
    network = Column(Enum(NetworkEnum), default=NetworkEnum.TESTNET, nullable=False)
    deployed_at = Column(DateTime(timezone=True), nullable=True)
    deployment_tx_id = Column(String(52), nullable=True)
    
    # Metadata
    transaction_metadata = Column(JSON, default={}, nullable=False)
    
    # Relationships
    wallet = relationship("Wallet", back_populates="contracts")
    executions = relationship("ContractExecution", back_populates="contract")
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint("length(creator_address) = 58", name="contracts_creator_address_check"),
        CheckConstraint("app_address IS NULL OR length(app_address) = 58", name="contracts_app_address_check"),
        Index('idx_smart_contracts_app_id', 'app_id'),
        Index('idx_smart_contracts_type_status', 'contract_type', 'status'),
        Index('idx_smart_contracts_creator', 'creator_address'),
    )


class ContractExecution(Base, TimestampMixin):
    """Smart contract execution tracking."""
    
    __tablename__ = "contract_executions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    contract_id = Column(String(36), ForeignKey('smart_contracts.id', ondelete='CASCADE'), nullable=False)
    
    # Execution details
    transaction_id = Column(String(52), nullable=False, index=True)
    method_name = Column(String(100), nullable=False)
    arguments = Column(JSON, default=[], nullable=False)
    
    # Execution results
    success = Column(Boolean, nullable=False)
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Gas and fees
    gas_used = Column(BigInteger, nullable=True)
    execution_fee = Column(Numeric(20, 6), nullable=True)
    
    # Network and confirmation
    network = Column(Enum(NetworkEnum), default=NetworkEnum.TESTNET, nullable=False)
    block_number = Column(BigInteger, nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    transaction_metadata = Column(JSON, default={}, nullable=False)
    
    # Relationships
    contract = relationship("SmartContract", back_populates="executions")
    
    # Constraints and indexes
    __table_args__ = (
        Index('idx_contract_executions_contract_id', 'contract_id'),
        Index('idx_contract_executions_tx_id', 'transaction_id'),
        Index('idx_contract_executions_method', 'method_name'),
        Index('idx_contract_executions_success', 'success'),
    )


# ============================================================================
# Asset Management Models
# ============================================================================

class AlgorandAsset(Base, TimestampMixin):
    """Algorand Standard Asset (ASA) model."""
    
    __tablename__ = "algorand_assets"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    
    # Asset identification
    asset_id = Column(BigInteger, unique=True, nullable=False, index=True)
    asset_name = Column(String(32), nullable=False)
    unit_name = Column(String(8), nullable=False)
    
    # Asset details
    total_supply = Column(Numeric(20, 6), nullable=False)
    decimals = Column(Integer, default=0, nullable=False)
    default_frozen = Column(Boolean, default=False, nullable=False)
    
    # Asset URLs and metadata
    url = Column(String(96), nullable=True)
    metadata_hash = Column(String(64), nullable=True)
    
    # Asset addresses
    manager_address = Column(String(58), nullable=True)
    reserve_address = Column(String(58), nullable=True)
    freeze_address = Column(String(58), nullable=True)
    clawback_address = Column(String(58), nullable=True)
    creator_address = Column(String(58), nullable=False)
    
    # Network and status
    network = Column(Enum(NetworkEnum), default=NetworkEnum.TESTNET, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    transaction_metadata = Column(JSON, default={}, nullable=False)
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint("total_supply > 0", name="assets_total_supply_check"),
        CheckConstraint("decimals >= 0 AND decimals <= 19", name="assets_decimals_check"),
        CheckConstraint("length(creator_address) = 58", name="assets_creator_address_check"),
        Index('idx_algorand_assets_asset_id', 'asset_id'),
        Index('idx_algorand_assets_name', 'asset_name'),
        Index('idx_algorand_assets_creator', 'creator_address'),
    )


class WalletAsset(Base, TimestampMixin):
    """Wallet asset balance tracking."""
    
    __tablename__ = "wallet_assets"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    wallet_id = Column(String(36), ForeignKey('wallets.id', ondelete='CASCADE'), nullable=False)
    asset_id = Column(BigInteger, nullable=False)  # 0 for ALGO
    
    # Balance information
    balance = Column(Numeric(20, 6), default=0, nullable=False)
    frozen = Column(Boolean, default=False, nullable=False)
    
    # Opt-in information
    opted_in = Column(Boolean, default=False, nullable=False)
    opted_in_at = Column(DateTime(timezone=True), nullable=True)
    opt_in_tx_id = Column(String(52), nullable=True)
    
    # Network
    network = Column(Enum(NetworkEnum), default=NetworkEnum.TESTNET, nullable=False)
    
    # Metadata
    transaction_metadata = Column(JSON, default={}, nullable=False)
    
    # Relationships
    wallet = relationship("Wallet")
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint("balance >= 0", name="wallet_assets_balance_check"),
        CheckConstraint("asset_id >= 0", name="wallet_assets_asset_id_check"),
        UniqueConstraint('wallet_id', 'asset_id', name='wallet_assets_unique'),
        Index('idx_wallet_assets_wallet_id', 'wallet_id'),
        Index('idx_wallet_assets_asset_id', 'asset_id'),
        Index('idx_wallet_assets_balance', 'balance'),
    )


# ============================================================================
# Network and Configuration Models
# ============================================================================

class NetworkConfiguration(Base, TimestampMixin):
    """Network configuration for different Algorand networks."""
    
    __tablename__ = "network_configurations"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    
    # Network identification
    network = Column(Enum(NetworkEnum), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Network endpoints
    algod_url = Column(String(255), nullable=False)
    algod_token = Column(String(255), nullable=True)
    indexer_url = Column(String(255), nullable=True)
    indexer_token = Column(String(255), nullable=True)
    
    # Network parameters
    genesis_id = Column(String(100), nullable=True)
    genesis_hash = Column(String(64), nullable=True)
    
    # Configuration
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    
    # Metadata
    transaction_metadata = Column(JSON, default={}, nullable=False)
    
    # Constraints and indexes
    __table_args__ = (
        Index('idx_network_configurations_network', 'network'),
        Index('idx_network_configurations_active', 'is_active'),
    )



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
    documents_submitted = Column(JSON, default=[], nullable=False)
    verification_data = Column(JSON, default={}, nullable=False)
    rejection_reasons = Column(ARRAY(String), nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    
    # Risk assessment
    risk_score = Column(Integer, nullable=True)
    risk_factors = Column(JSON, default={}, nullable=False)
    
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
    screening_data = Column(JSON, default={}, nullable=False)
    matches = Column(JSON, default=[], nullable=False)
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
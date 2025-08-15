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
    FIAT_TO_CRYPTO = "fiat_to_crypto"

class PaymentMethodStatus(str, Enum):
    """Transaction status enumeration."""
    ACTIVE = "active"
    UNACTIVE = "unactive"


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

class WalletStatus(str, Enum):
    """Wallet status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    FROZEN = "frozen"

# ============================================================================
# Enumerations
# ============================================================================

class ContractType(str,Enum):
    """Smart contract type enumeration."""
    ESCROW = "escrow"
    MULTISIG = "multisig"
    BATCH_PROCESSOR = "batch_processor"
    PAYMENT_SPLITTER = "payment_splitter"


class ContractStatus(str,Enum):
    """Smart contract status enumeration."""
    DEPLOYED = "deployed"
    ACTIVE = "active"
    PAUSED = "paused"
    TERMINATED = "terminated"


class Network(str, Enum):
    """Blockchain network enumeration."""
    MAINNET = "mainnet"
    TESTNET = "testnet"
    BETANET = "betanet"
    LOCALNET = "localnet"

class Gender(str, Enum):
    """ gender """
    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"

class DeviceType(str, Enum):
    PHONE = "phone"
    LAPTOP = "laptop"

class LoginMethod(str, Enum):
    GOOGLE = "google"
    MAIL = "mail"
    OAUTH = "oauth"
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
from app.schemas import BaseSchema, WalletType, TimestampMixin

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

class BalanceRequest(BaseSchema):
    wallet_address: str


class BalanceResponse(BaseSchema):
    wallet_address: str
    balances: Dict[int, float]  # asset_id -> balance


class ValidateWalletRequest(BaseSchema):
    wallet_address: str


class ValidateWalletResponse(BaseSchema):
    wallet_address: str
    is_valid: bool
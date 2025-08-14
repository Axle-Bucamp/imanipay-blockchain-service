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
from .base import TimestampMixin, PaginatedResponse, BaseSchema
from .enumerate import TransactionType, TransactionStatus

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
    trx_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


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

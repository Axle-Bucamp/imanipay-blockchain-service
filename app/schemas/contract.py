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
from .base import BaseSchema

# ============================================================================
# Base Models
# ============================================================================


class ContractDeploymentRequest(BaseSchema):
    deployer_address: str
    app_args: Optional[List[Any]] = None  # Arguments for contract creation


class ContractDeploymentResponse(BaseSchema):
    app_id: int
    transaction_id: str
    contract_type: str
    deployer_address: str
    status: str
    deployment_timestamp: datetime
    contract_address: str


class ContractInteractionRequest(BaseSchema):
    app_id: int
    caller_address: str
    method_name: str
    method_args: Optional[List[Any]] = None
    accounts: Optional[List[str]] = None
    foreign_apps: Optional[List[int]] = None
    foreign_assets: Optional[List[int]] = None


class ContractInteractionResponse(BaseSchema):
    transaction_id: str
    app_id: int
    status: str
    message: str
    logs: Optional[List[Any]] = None
    inner_transactions: Optional[List[Any]] = None
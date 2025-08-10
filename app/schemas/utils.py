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


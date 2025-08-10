# ============================================================================
# Webhook and Event Schemas
# ============================================================================
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
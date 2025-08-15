"""
External payment processor integrations for ImaniPay Blockchain Service.

This module provides integrations with external payment processors including
Circle, YellowCard, Transak, and Coinbase for fiat on/off-ramp functionality.
"""

import logging
import hashlib
import hmac
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4

import httpx
from pydantic import BaseModel

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ProcessorError(Exception):
    """Base exception for payment processor errors."""
    pass


class ProcessorAPIError(ProcessorError):
    """Exception raised for API-related errors."""
    pass


class ProcessorConfigError(ProcessorError):
    """Exception raised for configuration errors."""
    pass


# ============================================================================
# Base Classes and Models
# ============================================================================

class PaymentRequest(BaseModel):
    """Base payment request model."""
    amount: Decimal
    currency: str
    reference: str
    metadata: Optional[Dict[str, Any]] = None


class FiatChargeRequest(PaymentRequest):
    """Fiat charge request model."""
    payment_method_id: str
    description: Optional[str] = None


class FiatPayoutRequest(PaymentRequest):
    """Fiat payout request model."""
    recipient_info: Dict[str, Any]
    payout_method: str


class CryptoTransferRequest(PaymentRequest):
    """Crypto transfer request model."""
    destination_address: str
    asset_id: Optional[str] = None


class ProcessorResponse(BaseModel):
    """Base processor response model."""
    success: bool
    transaction_id: str
    status: str
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class BasePaymentProcessor(ABC):
    """Abstract base class for payment processors."""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logger
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    @abstractmethod
    async def charge_fiat(self, request: FiatChargeRequest) -> ProcessorResponse:
        """Charge fiat payment method."""
        pass
    
    @abstractmethod
    async def payout_fiat(self, request: FiatPayoutRequest) -> ProcessorResponse:
        """Payout to fiat payment method."""
        pass
    
    @abstractmethod
    async def transfer_crypto(self, request: CryptoTransferRequest) -> ProcessorResponse:
        """Transfer cryptocurrency."""
        pass
    
    @abstractmethod
    async def get_transaction_status(self, transaction_id: str) -> ProcessorResponse:
        """Get transaction status."""
        pass
    
    @abstractmethod
    async def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature."""
        pass
    
    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()


# ============================================================================
# Circle Processor (USDC on/off-ramp)
# ============================================================================

class CircleProcessor(BasePaymentProcessor):
    """Circle API integration for USDC on/off-ramp."""
    
    def __init__(self):
        super().__init__("circle")
        self.api_key = settings.payment_processors.circle_api_key
        self.base_url = settings.payment_processors.circle_base_url
        self.webhook_secret = settings.payment_processors.circle_webhook_secret
        
        if not self.api_key:
            raise ProcessorConfigError("Circle API key not configured")
        
        # Set default headers
        self.http_client.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })
    
    async def charge_fiat(self, request: FiatChargeRequest) -> ProcessorResponse:
        """Charge fiat payment method via Circle."""
        try:
            payload = {
                "idempotencyKey": str(uuid4()),
                "amount": {
                    "amount": str(request.amount),
                    "currency": request.currency
                },
                "source": {
                    "id": request.payment_method_id,
                    "type": "card"  # or "wire", "ach"
                },
                "description": request.description or f"ImaniPay charge {request.reference}",
                "metadata": {
                    "reference": request.reference,
                    **(request.metadata or {})
                }
            }
            
            response = await self.http_client.post(
                f"{self.base_url}/v1/payments",
                json=payload
            )
            
            if response.status_code == 201:
                data = response.json()
                return ProcessorResponse(
                    success=True,
                    transaction_id=data["data"]["id"],
                    status=data["data"]["status"],
                    message="Payment created successfully",
                    data=data["data"]
                )
            else:
                error_data = response.json()
                return ProcessorResponse(
                    success=False,
                    transaction_id="",
                    status="failed",
                    message=error_data.get("message", "Payment failed"),
                    data=error_data
                )
                
        except Exception as e:
            self.logger.error(f"Circle charge failed: {e}")
            return ProcessorResponse(
                success=False,
                transaction_id="",
                status="error",
                message=str(e)
            )
    
    async def payout_fiat(self, request: FiatPayoutRequest) -> ProcessorResponse:
        """Payout to fiat payment method via Circle."""
        try:
            payload = {
                "idempotencyKey": str(uuid4()),
                "amount": {
                    "amount": str(request.amount),
                    "currency": request.currency
                },
                "destination": {
                    "type": request.payout_method,
                    **request.recipient_info
                },
                "metadata": {
                    "reference": request.reference,
                    **(request.metadata or {})
                }
            }
            
            response = await self.http_client.post(
                f"{self.base_url}/v1/payouts",
                json=payload
            )
            
            if response.status_code == 201:
                data = response.json()
                return ProcessorResponse(
                    success=True,
                    transaction_id=data["data"]["id"],
                    status=data["data"]["status"],
                    message="Payout created successfully",
                    data=data["data"]
                )
            else:
                error_data = response.json()
                return ProcessorResponse(
                    success=False,
                    transaction_id="",
                    status="failed",
                    message=error_data.get("message", "Payout failed"),
                    data=error_data
                )
                
        except Exception as e:
            self.logger.error(f"Circle payout failed: {e}")
            return ProcessorResponse(
                success=False,
                transaction_id="",
                status="error",
                message=str(e)
            )
    
    async def transfer_crypto(self, request: CryptoTransferRequest) -> ProcessorResponse:
        """Transfer USDC via Circle."""
        try:
            payload = {
                "idempotencyKey": str(uuid4()),
                "amount": {
                    "amount": str(request.amount),
                    "currency": request.currency
                },
                "destination": {
                    "type": "blockchain",
                    "address": request.destination_address,
                    "chain": "ALGO"  # Algorand
                },
                "metadata": {
                    "reference": request.reference,
                    **(request.metadata or {})
                }
            }
            
            response = await self.http_client.post(
                f"{self.base_url}/v1/transfers",
                json=payload
            )
            
            if response.status_code == 201:
                data = response.json()
                return ProcessorResponse(
                    success=True,
                    transaction_id=data["data"]["id"],
                    status=data["data"]["status"],
                    message="Transfer created successfully",
                    data=data["data"]
                )
            else:
                error_data = response.json()
                return ProcessorResponse(
                    success=False,
                    transaction_id="",
                    status="failed",
                    message=error_data.get("message", "Transfer failed"),
                    data=error_data
                )
                
        except Exception as e:
            self.logger.error(f"Circle transfer failed: {e}")
            return ProcessorResponse(
                success=False,
                transaction_id="",
                status="error",
                message=str(e)
            )
    
    async def get_transaction_status(self, transaction_id: str) -> ProcessorResponse:
        """Get Circle transaction status."""
        try:
            response = await self.http_client.get(
                f"{self.base_url}/v1/payments/{transaction_id}"
            )
            
            if response.status_code == 200:
                data = response.json()
                return ProcessorResponse(
                    success=True,
                    transaction_id=transaction_id,
                    status=data["data"]["status"],
                    message="Status retrieved successfully",
                    data=data["data"]
                )
            else:
                return ProcessorResponse(
                    success=False,
                    transaction_id=transaction_id,
                    status="unknown",
                    message="Failed to get status"
                )
                
        except Exception as e:
            self.logger.error(f"Circle status check failed: {e}")
            return ProcessorResponse(
                success=False,
                transaction_id=transaction_id,
                status="error",
                message=str(e)
            )
    
    async def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify Circle webhook signature."""
        if not self.webhook_secret:
            return False
        
        try:
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            self.logger.error(f"Circle webhook verification failed: {e}")
            return False


# ============================================================================
# YellowCard Processor (African fiat on/off-ramp)
# ============================================================================

class YellowCardProcessor(BasePaymentProcessor):
    """YellowCard API integration for African fiat on/off-ramp."""
    
    def __init__(self):
        super().__init__("yellowcard")
        self.api_key = settings.payment_processors.yellowcard_api_key
        self.base_url = settings.payment_processors.yellowcard_base_url
        self.webhook_secret = settings.payment_processors.yellowcard_webhook_secret
        
        if self.api_key:
            self.http_client.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            })
    
    async def charge_fiat(self, request: FiatChargeRequest) -> ProcessorResponse:
        """Charge fiat payment method via YellowCard."""
        try:
            payload = {
                "reference": request.reference,
                "amount": str(request.amount),
                "currency": request.currency,
                "payment_method": request.payment_method_id,
                "description": request.description or f"ImaniPay charge {request.reference}",
                "metadata": request.metadata or {}
            }
            
            response = await self.http_client.post(
                f"{self.base_url}/v1/charges",
                json=payload
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                return ProcessorResponse(
                    success=True,
                    transaction_id=data.get("id", request.reference),
                    status=data.get("status", "pending"),
                    message="Charge created successfully",
                    data=data
                )
            else:
                error_data = response.json() if response.content else {}
                return ProcessorResponse(
                    success=False,
                    transaction_id="",
                    status="failed",
                    message=error_data.get("message", "Charge failed"),
                    data=error_data
                )
                
        except Exception as e:
            self.logger.error(f"YellowCard charge failed: {e}")
            return ProcessorResponse(
                success=False,
                transaction_id="",
                status="error",
                message=str(e)
            )
    
    async def payout_fiat(self, request: FiatPayoutRequest) -> ProcessorResponse:
        """Payout to fiat payment method via YellowCard."""
        try:
            payload = {
                "reference": request.reference,
                "amount": str(request.amount),
                "currency": request.currency,
                "recipient": request.recipient_info,
                "payout_method": request.payout_method,
                "metadata": request.metadata or {}
            }
            
            response = await self.http_client.post(
                f"{self.base_url}/v1/payouts",
                json=payload
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                return ProcessorResponse(
                    success=True,
                    transaction_id=data.get("id", request.reference),
                    status=data.get("status", "pending"),
                    message="Payout created successfully",
                    data=data
                )
            else:
                error_data = response.json() if response.content else {}
                return ProcessorResponse(
                    success=False,
                    transaction_id="",
                    status="failed",
                    message=error_data.get("message", "Payout failed"),
                    data=error_data
                )
                
        except Exception as e:
            self.logger.error(f"YellowCard payout failed: {e}")
            return ProcessorResponse(
                success=False,
                transaction_id="",
                status="error",
                message=str(e)
            )
    
    async def transfer_crypto(self, request: CryptoTransferRequest) -> ProcessorResponse:
        """YellowCard doesn't support direct crypto transfers."""
        return ProcessorResponse(
            success=False,
            transaction_id="",
            status="not_supported",
            message="YellowCard doesn't support direct crypto transfers"
        )
    
    async def get_transaction_status(self, transaction_id: str) -> ProcessorResponse:
        """Get YellowCard transaction status."""
        try:
            response = await self.http_client.get(
                f"{self.base_url}/v1/transactions/{transaction_id}"
            )
            
            if response.status_code == 200:
                data = response.json()
                return ProcessorResponse(
                    success=True,
                    transaction_id=transaction_id,
                    status=data.get("status", "unknown"),
                    message="Status retrieved successfully",
                    data=data
                )
            else:
                return ProcessorResponse(
                    success=False,
                    transaction_id=transaction_id,
                    status="unknown",
                    message="Failed to get status"
                )
                
        except Exception as e:
            self.logger.error(f"YellowCard status check failed: {e}")
            return ProcessorResponse(
                success=False,
                transaction_id=transaction_id,
                status="error",
                message=str(e)
            )
    
    async def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify YellowCard webhook signature."""
        if not self.webhook_secret:
            return False
        
        try:
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            self.logger.error(f"YellowCard webhook verification failed: {e}")
            return False


# ============================================================================
# Transak Processor (Global fiat on/off-ramp)
# ============================================================================

class TransakProcessor(BasePaymentProcessor):
    """Transak API integration for global fiat on/off-ramp."""
    
    def __init__(self):
        super().__init__("transak")
        self.api_key = settings.payment_processors.transak_api_key
        self.base_url = settings.payment_processors.transak_base_url
        self.webhook_secret = settings.payment_processors.transak_webhook_secret
        
        if self.api_key:
            self.http_client.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            })
    
    async def charge_fiat(self, request: FiatChargeRequest) -> ProcessorResponse:
        """Charge fiat payment method via Transak."""
        try:
            payload = {
                "partnerOrderId": request.reference,
                "fiatAmount": str(request.amount),
                "fiatCurrency": request.currency,
                "cryptoCurrency": "USDC",
                "paymentMethod": request.payment_method_id,
                "metadata": request.metadata or {}
            }
            
            response = await self.http_client.post(
                f"{self.base_url}/api/v2/orders",
                json=payload
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                return ProcessorResponse(
                    success=True,
                    transaction_id=data.get("response", {}).get("id", request.reference),
                    status=data.get("response", {}).get("status", "pending"),
                    message="Order created successfully",
                    data=data.get("response", {})
                )
            else:
                error_data = response.json() if response.content else {}
                return ProcessorResponse(
                    success=False,
                    transaction_id="",
                    status="failed",
                    message=error_data.get("message", "Order failed"),
                    data=error_data
                )
                
        except Exception as e:
            self.logger.error(f"Transak charge failed: {e}")
            return ProcessorResponse(
                success=False,
                transaction_id="",
                status="error",
                message=str(e)
            )
    
    async def payout_fiat(self, request: FiatPayoutRequest) -> ProcessorResponse:
        """Payout to fiat payment method via Transak."""
        try:
            payload = {
                "partnerOrderId": request.reference,
                "cryptoAmount": str(request.amount),
                "cryptoCurrency": request.currency,
                "fiatCurrency": request.recipient_info.get("currency", "USD"),
                "bankAccount": request.recipient_info,
                "metadata": request.metadata or {}
            }
            
            response = await self.http_client.post(
                f"{self.base_url}/api/v2/sell-orders",
                json=payload
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                return ProcessorResponse(
                    success=True,
                    transaction_id=data.get("response", {}).get("id", request.reference),
                    status=data.get("response", {}).get("status", "pending"),
                    message="Sell order created successfully",
                    data=data.get("response", {})
                )
            else:
                error_data = response.json() if response.content else {}
                return ProcessorResponse(
                    success=False,
                    transaction_id="",
                    status="failed",
                    message=error_data.get("message", "Sell order failed"),
                    data=error_data
                )
                
        except Exception as e:
            self.logger.error(f"Transak payout failed: {e}")
            return ProcessorResponse(
                success=False,
                transaction_id="",
                status="error",
                message=str(e)
            )
    
    async def transfer_crypto(self, request: CryptoTransferRequest) -> ProcessorResponse:
        """Transak doesn't support direct crypto transfers."""
        return ProcessorResponse(
            success=False,
            transaction_id="",
            status="not_supported",
            message="Transak doesn't support direct crypto transfers"
        )
    
    async def get_transaction_status(self, transaction_id: str) -> ProcessorResponse:
        """Get Transak transaction status."""
        try:
            response = await self.http_client.get(
                f"{self.base_url}/api/v2/orders/{transaction_id}"
            )
            
            if response.status_code == 200:
                data = response.json()
                return ProcessorResponse(
                    success=True,
                    transaction_id=transaction_id,
                    status=data.get("response", {}).get("status", "unknown"),
                    message="Status retrieved successfully",
                    data=data.get("response", {})
                )
            else:
                return ProcessorResponse(
                    success=False,
                    transaction_id=transaction_id,
                    status="unknown",
                    message="Failed to get status"
                )
                
        except Exception as e:
            self.logger.error(f"Transak status check failed: {e}")
            return ProcessorResponse(
                success=False,
                transaction_id=transaction_id,
                status="error",
                message=str(e)
            )
    
    async def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify Transak webhook signature."""
        if not self.webhook_secret:
            return False
        
        try:
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            self.logger.error(f"Transak webhook verification failed: {e}")
            return False


# ============================================================================
# Coinbase Processor (Crypto exchange)
# ============================================================================

class CoinbaseProcessor(BasePaymentProcessor):
    """Coinbase API integration for crypto exchange."""
    
    def __init__(self):
        super().__init__("coinbase")
        self.api_key = settings.payment_processors.coinbase_api_key
        self.api_secret = settings.payment_processors.coinbase_api_secret
        self.base_url = settings.payment_processors.coinbase_base_url
        
        if self.api_key and self.api_secret:
            # Coinbase uses different authentication
            self.http_client.headers.update({
                "Content-Type": "application/json"
            })
    
    async def charge_fiat(self, request: FiatChargeRequest) -> ProcessorResponse:
        """Coinbase doesn't support direct fiat charging."""
        return ProcessorResponse(
            success=False,
            transaction_id="",
            status="not_supported",
            message="Coinbase doesn't support direct fiat charging"
        )
    
    async def payout_fiat(self, request: FiatPayoutRequest) -> ProcessorResponse:
        """Coinbase doesn't support direct fiat payouts."""
        return ProcessorResponse(
            success=False,
            transaction_id="",
            status="not_supported",
            message="Coinbase doesn't support direct fiat payouts"
        )
    
    async def transfer_crypto(self, request: CryptoTransferRequest) -> ProcessorResponse:
        """Transfer crypto via Coinbase."""
        try:
            # This would require proper Coinbase API authentication
            # For now, return a mock response
            return ProcessorResponse(
                success=True,
                transaction_id=str(uuid4()),
                status="pending",
                message="Crypto transfer initiated",
                data={"mock": True}
            )
            
        except Exception as e:
            self.logger.error(f"Coinbase transfer failed: {e}")
            return ProcessorResponse(
                success=False,
                transaction_id="",
                status="error",
                message=str(e)
            )
    
    async def get_transaction_status(self, transaction_id: str) -> ProcessorResponse:
        """Get Coinbase transaction status."""
        try:
            # Mock implementation
            return ProcessorResponse(
                success=True,
                transaction_id=transaction_id,
                status="completed",
                message="Status retrieved successfully",
                data={"mock": True}
            )
            
        except Exception as e:
            self.logger.error(f"Coinbase status check failed: {e}")
            return ProcessorResponse(
                success=False,
                transaction_id=transaction_id,
                status="error",
                message=str(e)
            )
    
    async def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify Coinbase webhook signature."""
        # Mock implementation
        return True


# ============================================================================
# Processor Factory and Manager
# ============================================================================

class ProcessorManager:
    """Manager for all payment processors."""
    
    def __init__(self):
        self.processors = {
            "circle": CircleProcessor(),
            "yellowcard": YellowCardProcessor(),
            "transak": TransakProcessor(),
            "coinbase": CoinbaseProcessor()
        }
        self.logger = logger
    
    def get_processor(self, name: str) -> Optional[BasePaymentProcessor]:
        """Get processor by name."""
        return self.processors.get(name)
    
    def get_best_processor_for_fiat_charge(
        self, 
        currency: str, 
        amount: Decimal,
        country: Optional[str] = None
    ) -> Optional[BasePaymentProcessor]:
        """Get best processor for fiat charging."""
        # Logic to select best processor based on currency, amount, and country
        if currency in ["NGN", "KES", "GHS", "ZAR"]:
            return self.processors.get("yellowcard")
        elif currency in ["USD", "EUR", "GBP"]:
            return self.processors.get("circle") or self.processors.get("transak")
        else:
            return self.processors.get("transak")
    
    def get_best_processor_for_fiat_payout(
        self, 
        currency: str, 
        amount: Decimal,
        country: Optional[str] = None
    ) -> Optional[BasePaymentProcessor]:
        """Get best processor for fiat payout."""
        # Similar logic for payouts
        if currency in ["NGN", "KES", "GHS", "ZAR"]:
            return self.processors.get("yellowcard")
        elif currency in ["USD", "EUR", "GBP"]:
            return self.processors.get("circle") or self.processors.get("transak")
        else:
            return self.processors.get("transak")
    
    def get_best_processor_for_crypto_transfer(
        self, 
        currency: str, 
        amount: Decimal
    ) -> Optional[BasePaymentProcessor]:
        """Get best processor for crypto transfer."""
        if currency == "USDC":
            return self.processors.get("circle")
        else:
            return self.processors.get("coinbase")
    
    async def close_all(self):
        """Close all processor HTTP clients."""
        for processor in self.processors.values():
            await processor.close()


# Global processor manager instance
# processor_manager = ProcessorManager()
processor_manager = None  # Temporarily disabled


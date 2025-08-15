"""
Schemas for imanipay request API security and typing.
"""

import pkgutil
import importlib
import inspect
from typing import TYPE_CHECKING

__all__ = []

# --- Runtime dynamic import ---
for loader, module_name, is_pkg in pkgutil.iter_modules(__path__):
    module = importlib.import_module(f"{__name__}.{module_name}")

    public_names = [
        name for name, obj in inspect.getmembers(module)
        if not name.startswith("_")
    ]

    globals().update({name: getattr(module, name) for name in public_names})
    __all__.extend(public_names)

# Deduplicate while preserving order
seen = set()
__all__ = [x for x in __all__ if not (x in seen or seen.add(x))]

# --- Static type checker / IDE support ---
if TYPE_CHECKING:
    # Explicit imports for static analyzers
    from .wallet import (
        WalletResponse, BalanceResponse, BalanceRequest,
        ValidateWalletRequest, ValidateWalletResponse
    )
    from .user import (
        UserCreate,
        UserUpdate,
        UserProfile,
        UserResponse,
        UserLogin,
        UserRegistration,
        TokenResponse,
        MFASetupResponse,
        MFAVerificationRequest
    )
    from .enumerate import (
        RiskLevel,
        WalletType,
        PaymentMethodType,
        TransactionStatus,
        TransactionType,
        KYCStatus,
        UserStatus
    )
    from .payment import (
        BankAccountCreate, 
        CardCreate, 
        MobileMoneyCreate, 
        PaymentMethodCreate, 
        PaymentMethodResponse, 
        FiatToCryptoRequest, 
        CryptoToFiatRequest, 
        CrossBorderPaymentRequest,
        ExchangeRate,
        FeeCalculation,
        ConversionQuote,
        SendPaymentRequest,
        SendPaymentResponse,
        KYCDocumentUpload,
        KYCVerificationRequest,
        KYCVerificationResponse,
        RiskAssessment
        )
    from .transaction import (TransactionCreate,TransactionStep,TransactionResponse,TransactionListResponse )
    from .webhook import (WebhookEvent, NotificationPreferences)
    from .utils import (ErrorDetail, ErrorResponse, HealthCheck, ServiceStatus, SystemStatus)
    from .contract import (ContractDeploymentRequest, ContractDeploymentResponse, ContractInteractionRequest, ContractInteractionResponse)
    from .base import BaseSchema

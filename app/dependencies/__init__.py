"""
Dependencies package for ImaniPay Blockchain Service.

This package contains FastAPI dependencies for authentication,
authorization, and other request processing components.
"""

from .auth import (
    get_current_user,
    get_current_active_user,
    get_current_user_optional,
    get_api_key_user,
    require_api_key,
    require_scopes,
    require_api_scopes,
    require_admin,
    require_verified_user,
    get_authenticated_user,
    check_rate_limit,
    get_security_context,
    require_wallet_access,
    require_transaction_authorization,
    get_development_user
)

__all__ = [
    "get_current_user",
    "get_current_active_user", 
    "get_current_user_optional",
    "get_api_key_user",
    "require_api_key",
    "require_scopes",
    "require_api_scopes",
    "require_admin",
    "require_verified_user",
    "get_authenticated_user",
    "check_rate_limit",
    "get_security_context",
    "require_wallet_access",
    "require_transaction_authorization",
    "get_development_user"
]


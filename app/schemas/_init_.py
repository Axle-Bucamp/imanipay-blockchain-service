"""
Schemas for imanypay request API security and typing.

This package contains schema and types for each request and response.
It enhances documentation and mitigates XSS attack vectors by enforcing
input validation and strict typing.
"""

from .base import * #
from .user import * #
from .auth import * #
from .enumerate import * #
from .payment import *    #
from .transaction import * #
from .wallet import*    #
from .webhook import *   #
from .utils import *    #
from .contract import *    #

__all__ = [

]

# If enumerate, payment, transaction, webhook, utils also define __all__,
# we can extend this dynamically:
try:
    from .enumerate import __all__ as enum_all
    __all__.extend(enum_all)
except ImportError:
    pass

try:
    from .payment import __all__ as payment_all
    __all__.extend(payment_all)
except ImportError:
    pass

try:
    from .transaction import __all__ as transaction_all
    __all__.extend(transaction_all)
except ImportError:
    pass

try:
    from .webhook import __all__ as webhook_all
    __all__.extend(webhook_all)
except ImportError:
    pass

try:
    from .utils import __all__ as utils_all
    __all__.extend(utils_all)
except ImportError:
    pass

try:
    from .wallet import __all__ as wallet_all
    __all__.extend(wallet_all)
except ImportError:
    pass

try:
    from .auth import __all__ as auth_all
    __all__.extend(auth_all)
except ImportError:
    pass

try:
    from .user import __all__ as user_all
    __all__.extend(user_all)
except ImportError:
    pass

try:
    from .base import __all__ as base_all
    __all__.extend(base_all)
except ImportError:
    pass

try:
    from .contract import __all__ as contract_all
    __all__.extend(contract_all)
except ImportError:
    pass
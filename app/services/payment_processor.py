"""
Payment processing service for ImaniPay Blockchain Service.

This module handles all payment processing operations including fiat-to-crypto
conversions, crypto-to-fiat conversions, and cross-border payments.
"""

import logging
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID, uuid4
from datetime import datetime, timedelta
import enum

from sqlalchemy import Enum, select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.database import get_async_session_context, database_transaction
from app.models import (
     User, Wallet, Transaction, PaymentMethod, ExchangeRate,
     TransactionStep, 
)

from app.schemas.enumerate import (TransactionType, TransactionStatus,
     UserStatus, PaymentMethodStatus)

from app.schemas import (
    FiatToCryptoRequest, CryptoToFiatRequest, CrossBorderPaymentRequest,
    TransactionResponse, ConversionQuote, FeeCalculation, ExchangeRate as ExchangeRateSchema
)
from app.services.enhanced_wallets import EnhancedWalletService
from app.services.external_processors import (
    CircleProcessor, YellowCardProcessor, TransakProcessor, CoinbaseProcessor
)
from app.services.compliance import ComplianceService
from app.services.exchange_rate import ExchangeRateService

logger = logging.getLogger(__name__)
settings = get_settings()


class PaymentProcessorError(Exception):
    """Base exception for payment processor errors."""
    pass


class InsufficientFundsError(PaymentProcessorError):
    """Exception raised when insufficient funds for payment."""
    pass


class ExchangeRateError(PaymentProcessorError):
    """Exception raised when exchange rate is unavailable."""
    pass


class ComplianceError(PaymentProcessorError):
    """Exception raised when compliance checks fail."""
    pass


class PaymentProcessorService:
    """Comprehensive payment processing service."""
    
    def __init__(self):
        self.wallet_service = EnhancedWalletService()
        self.compliance_service = ComplianceService()
        self.exchange_rate_service = ExchangeRateService()
        
        # Initialize external processors
        self.circle_processor = CircleProcessor()
        self.yellowcard_processor = YellowCardProcessor()
        self.transak_processor = TransakProcessor()
        self.coinbase_processor = CoinbaseProcessor()
        
        self.logger = logger
    
    # ========================================================================
    # Fiat to Crypto Conversions
    # ========================================================================
    
    async def process_fiat_to_crypto(
        self,
        user_id: UUID,
        request: FiatToCryptoRequest,
        session: Optional[AsyncSession] = None
    ) -> TransactionResponse:
        """
        Process fiat to crypto conversion.
        
        Args:
            user_id: User ID
            request: Fiat to crypto conversion request
            session: Database session
            
        Returns:
            TransactionResponse: Transaction details
            
        Raises:
            PaymentProcessorError: If conversion fails
        """
        async def _process_conversion(db_session: AsyncSession) -> TransactionResponse:
            # Validate user and payment method
            await self._validate_user_and_payment_method(
                user_id, request.payment_method_id, db_session
            )
            
            # Perform compliance checks
            await self.compliance_service.check_transaction_compliance(
                user_id=user_id,
                transaction_type=TransactionType.FIAT_TO_CRYPTO,            
                amount=Decimal(str(request.amount)),
                currency=request.fiat_currency,
                session=db_session
            )
            
            # Get exchange rate and calculate fees
            quote = await self.get_conversion_quote(
                source_currency=request.fiat_currency,
                destination_currency=request.crypto_currency,
                amount=Decimal(str(request.amount)),
                session=db_session
            )
            
            # Create transaction record
            transaction = Transaction(
                user_id=user_id,
                transaction_type=TransactionType.FIAT_TO_CRYPTO,
                status=TransactionStatus.PENDING,
                amount=request.amount,
                currency=request.fiat_currency,
                fee_amount=quote.fees.total_fee,
                fee_currency=request.fiat_currency,
                exchange_rate=quote.exchange_rate,
                exchange_rate_source="internal",
                exchange_rate_timestamp=datetime.utcnow(),
                destination_wallet_id=request.destination_wallet_id,
                payment_processor="multi_processor",
                description=f"Fiat to crypto conversion: {request.amount} {request.fiat_currency} to {request.crypto_currency}",
                metadata={
                    "quote_id": quote.quote_id,
                    "payment_method_id": str(request.payment_method_id),
                    "destination_amount": str(quote.destination_amount),
                    "destination_currency": quote.destination_currency,
                }
            )
            
            db_session.add(transaction)
            await db_session.commit()
            await db_session.refresh(transaction)
            
            # Execute conversion steps
            try:
                await self._execute_fiat_to_crypto_steps(
                    transaction, request, quote, db_session
                )
                
                # Update transaction status
                transaction.status = TransactionStatus.COMPLETED.value
                transaction.completed_at = datetime.utcnow()
                await db_session.commit()
                
            except Exception as e:
                # Update transaction status to failed
                transaction.status = TransactionStatus.FAILED.value
                transaction.failed_at = datetime.utcnow()
                await db_session.commit()
                
                self.logger.error(f"Fiat to crypto conversion failed for transaction {transaction.id}: {e}")
                raise PaymentProcessorError(f"Conversion failed: {str(e)}")
            
            return TransactionResponse.model_validate(transaction)
        
        if session:
            return await _process_conversion(session)
        else:
            async with database_transaction() as db_session:
                return await _process_conversion(db_session)
    
    async def process_crypto_to_fiat(
        self,
        user_id: UUID,
        request: CryptoToFiatRequest,
        session: Optional[AsyncSession] = None
    ) -> TransactionResponse:
        """
        Process crypto to fiat conversion.
        
        Args:
            user_id: User ID
            request: Crypto to fiat conversion request
            session: Database session
            
        Returns:
            TransactionResponse: Transaction details
            
        Raises:
            PaymentProcessorError: If conversion fails
        """
        async def _process_conversion(db_session: AsyncSession) -> TransactionResponse:
            # Validate user, wallet, and payment method
            await self._validate_user_and_payment_method(
                user_id, request.payment_method_id, db_session
            )
            
            wallet = await self.wallet_service.get_wallet_by_id(
                request.source_wallet_id, user_id, db_session
            )
            if not wallet:
                raise PaymentProcessorError("Source wallet not found")
            
            # Check wallet balance
            balance = await self.wallet_service.get_wallet_balance(
                request.source_wallet_id, user_id, True, db_session
            )
            
            crypto_balance = self._get_asset_balance(balance, request.crypto_currency)
            if crypto_balance < request.amount:
                raise InsufficientFundsError(
                    f"Insufficient {request.crypto_currency} balance: {crypto_balance} < {request.amount}"
                )
            
            # Perform compliance checks
            await self.compliance_service.check_transaction_compliance(
                user_id=user_id,
                transaction_type=TransactionType.CRYPTO_TO_FIAT,
                amount=Decimal(str(request.amount)),
                currency=request.crypto_currency,
                session=db_session
            )
            
            # Get exchange rate and calculate fees
            quote = await self.get_conversion_quote(
                source_currency=request.crypto_currency,
                destination_currency=request.fiat_currency,
                amount=Decimal(str(request.amount)),
                session=db_session
            )
            
            # Create transaction record
            transaction = Transaction(
                user_id=user_id,
                transaction_type=TransactionType.CRYPTO_TO_FIAT,
                status=TransactionStatus.PENDING,
                amount=request.amount,
                currency=request.crypto_currency,
                fee_amount=quote.fees.total_fee,
                fee_currency=request.crypto_currency,
                exchange_rate=quote.exchange_rate,
                exchange_rate_source="internal",
                exchange_rate_timestamp=datetime.utcnow(),
                source_wallet_id=request.source_wallet_id,
                payment_processor="multi_processor",
                description=f"Crypto to fiat conversion: {request.amount} {request.crypto_currency} to {request.fiat_currency}",
                metadata={
                    "quote_id": quote.quote_id,
                    "payment_method_id": str(request.payment_method_id),
                    "destination_amount": str(quote.destination_amount),
                    "destination_currency": quote.destination_currency,
                }
            )
            
            db_session.add(transaction)
            await db_session.commit()
            await db_session.refresh(transaction)
            
            # Execute conversion steps
            try:
                await self._execute_crypto_to_fiat_steps(
                    transaction, request, quote, db_session
                )
                
                # Update transaction status
                transaction.status = TransactionStatus.COMPLETED.value
                transaction.completed_at = datetime.utcnow()
                await db_session.commit()
                
            except Exception as e:
                # Update transaction status to failed
                transaction.status = TransactionStatus.FAILED.value
                transaction.failed_at = datetime.utcnow()
                await db_session.commit()
                
                self.logger.error(f"Crypto to fiat conversion failed for transaction {transaction.id}: {e}")
                raise PaymentProcessorError(f"Conversion failed: {str(e)}")
            
            return TransactionResponse.model_validate(transaction)
        
        if session:
            return await _process_conversion(session)
        else:
            async with database_transaction() as db_session:
                return await _process_conversion(db_session)
    
    # ========================================================================
    # Cross-Border Payments
    # ========================================================================
    
    async def process_cross_border_payment(
        self,
        user_id: UUID,
        request: CrossBorderPaymentRequest,
        session: Optional[AsyncSession] = None
    ) -> TransactionResponse:
        """
        Process cross-border payment.
        
        Args:
            user_id: User ID
            request: Cross-border payment request
            session: Database session
            
        Returns:
            TransactionResponse: Transaction details
            
        Raises:
            PaymentProcessorError: If payment fails
        """
        async def _process_payment(db_session: AsyncSession) -> TransactionResponse:
            # Validate user and payment method
            await self._validate_user_and_payment_method(
                user_id, request.payment_method_id, db_session
            )
            
            # Perform compliance checks
            await self.compliance_service.check_cross_border_compliance(
                user_id=user_id,
                amount=Decimal(str(request.amount)),
                source_currency=request.source_currency,
                destination_currency=request.destination_currency,
                recipient_info=request.recipient_info,
                session=db_session
            )
            
            # Get exchange rate and calculate fees
            quote = await self.get_conversion_quote(
                source_currency=request.source_currency,
                destination_currency=request.destination_currency,
                amount=Decimal(str(request.amount)),
                session=db_session
            )
            
            # Create transaction record
            transaction = Transaction(
                user_id=user_id,
                transaction_type=TransactionType.CROSS_BORDER_PAYMENT,
                status=TransactionStatus.PENDING,
                amount=request.amount,
                currency=request.source_currency,
                fee_amount=quote.fees.total_fee,
                fee_currency=request.source_currency,
                exchange_rate=quote.exchange_rate,
                exchange_rate_source="internal",
                exchange_rate_timestamp=datetime.utcnow(),
                payment_processor="multi_processor",
                description=f"Cross-border payment: {request.amount} {request.source_currency} to {request.destination_currency}",
                metadata={
                    "quote_id": quote.quote_id,
                    "payment_method_id": str(request.payment_method_id),
                    "recipient_info": request.recipient_info,
                    "delivery_method": request.delivery_method,
                    "destination_amount": str(quote.destination_amount),
                    "destination_currency": quote.destination_currency,
                }
            )
            
            db_session.add(transaction)
            await db_session.commit()
            await db_session.refresh(transaction)
            
            # Execute payment steps
            try:
                await self._execute_cross_border_payment_steps(
                    transaction, request, quote, db_session
                )
                
                # Update transaction status
                transaction.status = TransactionStatus.COMPLETED.value
                transaction.completed_at = datetime.utcnow()
                await db_session.commit()
                
            except Exception as e:
                # Update transaction status to failed
                transaction.status = TransactionStatus.FAILED.value
                transaction.failed_at = datetime.utcnow()
                await db_session.commit()
                
                self.logger.error(f"Cross-border payment failed for transaction {transaction.id}: {e}")
                raise PaymentProcessorError(f"Payment failed: {str(e)}")
            
            return TransactionResponse.model_validate(transaction)
        
        if session:
            return await _process_payment(session)
        else:
            async with database_transaction() as db_session:
                return await _process_payment(db_session)
    
    # ========================================================================
    # Quote and Rate Management
    # ========================================================================
    
    async def get_conversion_quote(
        self,
        source_currency: str,
        destination_currency: str,
        amount: Decimal,
        session: Optional[AsyncSession] = None
    ) -> ConversionQuote:
        """
        Get conversion quote with fees and exchange rate.
        
        Args:
            source_currency: Source currency code
            destination_currency: Destination currency code
            amount: Amount to convert
            session: Database session
            
        Returns:
            ConversionQuote: Conversion quote details
            
        Raises:
            ExchangeRateError: If exchange rate unavailable
        """
        async def _get_quote(db_session: AsyncSession) -> ConversionQuote:
            # Get exchange rate
            exchange_rate = await self.exchange_rate_service.get_exchange_rate(
                source_currency, destination_currency, db_session
            )
            
            if not exchange_rate:
                raise ExchangeRateError(
                    f"Exchange rate not available for {source_currency}/{destination_currency}"
                )
            
            # Calculate destination amount
            destination_amount = amount * exchange_rate.rate
            
            # Calculate fees
            fees = await self._calculate_conversion_fees(
                amount, source_currency, destination_currency, db_session
            )
            
            # Generate quote ID
            quote_id = str(uuid4())
            
            # Quote expires in 5 minutes
            expires_at = datetime.utcnow() + timedelta(minutes=5)
            
            return ConversionQuote(
                source_amount=amount,
                source_currency=source_currency,
                destination_amount=destination_amount,
                destination_currency=destination_currency,
                exchange_rate=exchange_rate.rate,
                fees=fees,
                expires_at=expires_at,
                quote_id=quote_id
            )
        
        if session:
            return await _get_quote(session)
        else:
            async with get_async_session_context() as db_session:
                return await _get_quote(db_session)
    
    async def get_supported_currencies(
        self,
        session: Optional[AsyncSession] = None
    ) -> Dict[str, List[str]]:
        """
        Get supported currencies for conversions.
        
        Args:
            session: Database session
            
        Returns:
            Dict[str, List[str]]: Supported currencies by type
        """
        async def _get_currencies(db_session: AsyncSession) -> Dict[str, List[str]]:
            # Get available exchange rates
            result = await db_session.execute(
                select(ExchangeRate.base_currency, ExchangeRate.quote_currency)
                .where(ExchangeRate.is_active == True)
                .distinct()
            )
            
            rates = result.fetchall()
            
            fiat_currencies = set()
            crypto_currencies = set()
            
            for base, quote in rates:
                if base in ['USD', 'EUR', 'GBP', 'NGN', 'KES', 'GHS', 'ZAR']:
                    fiat_currencies.add(base)
                else:
                    crypto_currencies.add(base)
                
                if quote in ['USD', 'EUR', 'GBP', 'NGN', 'KES', 'GHS', 'ZAR']:
                    fiat_currencies.add(quote)
                else:
                    crypto_currencies.add(quote)
            
            return {
                "fiat": sorted(list(fiat_currencies)),
                "crypto": sorted(list(crypto_currencies)),
                "all": sorted(list(fiat_currencies | crypto_currencies))
            }
        
        if session:
            return await _get_currencies(session)
        else:
            async with get_async_session_context() as db_session:
                return await _get_currencies(db_session)
    
    # ========================================================================
    # Transaction Management
    # ========================================================================
    
    async def get_user_transactions(
        self,
        user_id: UUID,
        transaction_type: Optional[TransactionType] = None,
        status: Optional[TransactionStatus] = None,
        limit: int = 50,
        offset: int = 0,
        session: Optional[AsyncSession] = None
    ) -> List[TransactionResponse]:
        """
        Get user transactions with optional filtering.
        
        Args:
            user_id: User ID
            transaction_type: Optional transaction type filter
            status: Optional status filter
            limit: Maximum number of transactions
            offset: Offset for pagination
            session: Database session
            
        Returns:
            List[TransactionResponse]: User transactions
        """
        async def _get_transactions(db_session: AsyncSession) -> List[TransactionResponse]:
            query = select(Transaction).where(Transaction.user_id == user_id)
            
            if transaction_type:
                query = query.where(Transaction.transaction_type == transaction_type)
            
            if status:
                query = query.where(Transaction.status == status)
            
            query = (
                query.options(selectinload(Transaction.steps))
                .order_by(Transaction.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            
            result = await db_session.execute(query)
            transactions = result.scalars().all()
            
            return [TransactionResponse.model_validate(txn) for txn in transactions]
        
        if session:
            return await _get_transactions(session)
        else:
            async with get_async_session_context() as db_session:
                return await _get_transactions(db_session)
    
    async def get_transaction_by_id(
        self,
        transaction_id: UUID,
        user_id: Optional[UUID] = None,
        session: Optional[AsyncSession] = None
    ) -> Optional[TransactionResponse]:
        """
        Get transaction by ID.
        
        Args:
            transaction_id: Transaction ID
            user_id: Optional user ID for access control
            session: Database session
            
        Returns:
            TransactionResponse: Transaction details or None if not found
        """
        async def _get_transaction(db_session: AsyncSession) -> Optional[TransactionResponse]:
            query = select(Transaction).where(Transaction.id == transaction_id)
            
            if user_id:
                query = query.where(Transaction.user_id == user_id)
            
            query = query.options(selectinload(Transaction.steps))
            
            result = await db_session.execute(query)
            transaction = result.scalar_one_or_none()
            
            if transaction:
                return TransactionResponse.model_validate(transaction)
            return None
        
        if session:
            return await _get_transaction(session)
        else:
            async with get_async_session_context() as db_session:
                return await _get_transaction(db_session)
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    async def _validate_user_and_payment_method(
        self,
        user_id: UUID,
        payment_method_id: UUID,
        session: AsyncSession
    ) -> Tuple[User, PaymentMethod]:
        """Validate user and payment method."""
        # Get user
        user_result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise PaymentProcessorError("User not found")
        
        if user.status != UserStatus.ACTIVE:
            raise PaymentProcessorError("User account is not active")
        
        # Get payment method
        pm_result = await session.execute(
            select(PaymentMethod).where(
                and_(
                    PaymentMethod.id == payment_method_id,
                    PaymentMethod.user_id == user_id
                )
            )
        )
        payment_method = pm_result.scalar_one_or_none()
        
        if not payment_method:
            raise PaymentProcessorError("Payment method not found")
        
        if payment_method.status != PaymentMethodStatus.ACTIVE:
            raise PaymentProcessorError("Payment method is not active")
        
        return user, payment_method
    
    async def _calculate_conversion_fees(
        self,
        amount: Decimal,
        source_currency: str,
        destination_currency: str,
        session: AsyncSession
    ) -> FeeCalculation:
        """Calculate conversion fees."""
        # Base fee calculation (simplified)
        base_fee_rate = Decimal('0.01')  # 1%
        base_fee = amount * base_fee_rate
        
        # Network fee (for crypto transactions)
        network_fee = Decimal('0')
        if destination_currency in ['ALGO', 'USDC']:
            network_fee = Decimal('0.001')  # 0.001 ALGO
        
        # Processor fee
        processor_fee_rate = Decimal('0.005')  # 0.5%
        processor_fee = amount * processor_fee_rate
        
        # Exchange fee
        exchange_fee_rate = Decimal('0.002')  # 0.2%
        exchange_fee = amount * exchange_fee_rate
        
        total_fee = base_fee + network_fee + processor_fee + exchange_fee
        
        return FeeCalculation(
            base_fee=base_fee,
            network_fee=network_fee,
            processor_fee=processor_fee,
            exchange_fee=exchange_fee,
            total_fee=total_fee,
            fee_currency=source_currency
        )
    
    def _get_asset_balance(
        self,
        wallet_balance: Any,
        currency: str
    ) -> Decimal:
        """Get asset balance from wallet balance response."""
        if currency == 'ALGO':
            return Decimal(wallet_balance.algo_balance) / Decimal('1000000')  # Convert microAlgos
        
        for asset in wallet_balance.assets:
            if asset.asset_unit_name == currency:
                return asset.formatted_balance
        
        return Decimal('0')
    
    async def _execute_fiat_to_crypto_steps(
        self,
        transaction: Transaction,
        request: FiatToCryptoRequest,
        quote: ConversionQuote,
        session: AsyncSession
    ) -> None:
        """Execute fiat to crypto conversion steps."""
        # Step 1: Charge fiat payment method
        await self._create_transaction_step(
            UUID(transaction.id), 1, "fiat_charge", "Charging fiat payment method", session
        )
        
        # Step 2: Convert fiat to USDC
        await self._create_transaction_step(
            UUID(transaction.id), 2, "fiat_to_usdc", "Converting fiat to USDC", session
        )
        
        # Step 3: Convert USDC to target crypto (if needed)
        if request.crypto_currency != 'USDC':
            await self._create_transaction_step(
                UUID(transaction.id), 3, "usdc_to_crypto", f"Converting USDC to {request.crypto_currency}", session
            )
        
        # Step 4: Transfer to destination wallet
        await self._create_transaction_step(
            UUID(transaction.id), 4, "crypto_transfer", "Transferring crypto to destination wallet", session
        )
    
    async def _execute_crypto_to_fiat_steps(
        self,
        transaction: Transaction,
        request: CryptoToFiatRequest,
        quote: ConversionQuote,
        session: AsyncSession
    ) -> None:
        """Execute crypto to fiat conversion steps."""
        # Step 1: Transfer crypto from source wallet
        await self._create_transaction_step(
            UUID(transaction.id), 1, "crypto_transfer", "Transferring crypto from source wallet", session
        )
        
        # Step 2: Convert crypto to USDC (if needed)
        if request.crypto_currency != 'USDC':
            await self._create_transaction_step(
                UUID(transaction.id), 2, "crypto_to_usdc", f"Converting {request.crypto_currency} to USDC", session
            )
        
        # Step 3: Convert USDC to fiat
        await self._create_transaction_step(
            UUID(transaction.id), 3, "usdc_to_fiat", "Converting USDC to fiat", session
        )
        
        # Step 4: Transfer fiat to payment method
        await self._create_transaction_step(
            UUID(transaction.id), 4, "fiat_transfer", "Transferring fiat to payment method", session
        )
    
    async def _execute_cross_border_payment_steps(
        self,
        transaction: Transaction,
        request: CrossBorderPaymentRequest,
        quote: ConversionQuote,
        session: AsyncSession
    ) -> None:
        """Execute cross-border payment steps."""
        # Step 1: Charge source payment method
        await self._create_transaction_step(
            UUID(transaction.id), 1, "source_charge", "Charging source payment method", session
        )
        
        # Step 2: Convert to bridge currency (USDC)
        await self._create_transaction_step(
            UUID(transaction.id), 2, "to_bridge", "Converting to bridge currency", session
        )
        
        # Step 3: Cross-border transfer via Algorand
        await self._create_transaction_step(
            UUID(transaction.id), 3, "cross_border", "Cross-border transfer via blockchain", session
        )
        
        # Step 4: Convert to destination currency
        await self._create_transaction_step(
            UUID(transaction.id), 4, "to_destination", "Converting to destination currency", session
        )
        
        # Step 5: Deliver to recipient
        await self._create_transaction_step(
            UUID(transaction.id), 5, "delivery", f"Delivering via {request.delivery_method}", session
        )
    
    async def _create_transaction_step(
        self,
        transaction_id: UUID,
        step_number: int,
        step_type: str,
        description: str,
        session: AsyncSession
    ) -> None:
        """Create a transaction step."""
        step = TransactionStep(
            transaction_id=transaction_id,
            step_number=step_number,
            step_type=step_type,
            status="completed",  # Simplified for now
            description=description,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        
        session.add(step)
        await session.commit()


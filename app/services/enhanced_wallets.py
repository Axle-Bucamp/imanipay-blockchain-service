"""
Enhanced wallet service for ImaniPay Blockchain Service.

This module provides comprehensive wallet management functionality including
wallet creation, asset management, balance tracking, and security features.
"""

import logging
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
import enum

from algosdk import account, mnemonic, transaction
from algosdk.v2client import algod, indexer
from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.database import get_async_session_context
# from app.models import User, Wallet, WalletAsset, Transaction, WalletTypeEnum, WalletStatusEnum
from app.models import Wallet, WalletAsset
from app.schemas import (
    WalletResponse, TransactionCreate, TransactionType
)
from app.schemas.wallet import WalletCreate, AssetBalance, WalletBalanceResponse, AssetOptInRequest
from app.services.algorand_client import AlgorandClient
from app.services.encryption import EncryptionService

logger = logging.getLogger(__name__)
settings = get_settings()

# Placeholder enums for missing models
class WalletTypeEnum(enum.Enum):
    STANDARD = "standard"
    MULTISIG = "multisig"
    SMART_CONTRACT = "smart_contract"
    ESCROW = "escrow"

class WalletStatusEnum(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    FROZEN = "frozen"


class WalletServiceError(Exception):
    """Base exception for wallet service errors."""
    pass


class InsufficientFundsError(WalletServiceError):
    """Exception raised when wallet has insufficient funds."""
    pass


class WalletNotFoundError(WalletServiceError):
    """Exception raised when wallet is not found."""
    pass


class AssetNotOptedInError(WalletServiceError):
    """Exception raised when wallet is not opted into an asset."""
    pass


class EnhancedWalletService:
    """Enhanced wallet service with comprehensive payment features."""
    
    def __init__(self):
        self.algorand_client = AlgorandClient()
        self.encryption_service = EncryptionService()
        self.logger = logger
    
    # ========================================================================
    # Wallet Creation and Management
    # ========================================================================
    
    async def create_wallet(
        self, 
        user_id: UUID, 
        wallet_data: WalletCreate,
        session: Optional[AsyncSession] = None
    ) -> WalletResponse:
        """
        Create a new Algorand wallet for a user.
        
        Args:
            user_id: User ID
            wallet_data: Wallet creation data
            session: Database session
            
        Returns:
            WalletResponse: Created wallet information
            
        Raises:
            WalletServiceError: If wallet creation fails
        """
        async def _create_wallet(db_session: AsyncSession) -> WalletResponse:
            try:
                # Generate new Algorand account
                private_key, address = account.generate_account()
                public_key = account.address_from_private_key(private_key)
                
                # Generate mnemonic for backup
                wallet_mnemonic = mnemonic.from_private_key(private_key)
                
                # Encrypt private key and mnemonic
                encrypted_private_key = await self.encryption_service.encrypt_sensitive_data(
                    private_key, user_id
                )
                
                # Create wallet record
                wallet = Wallet(
                    user_id=user_id,
                    address=address,
                    wallet_type=wallet_data.wallet_type,
                    status=WalletStatusEnum.ACTIVE,
                    is_multisig=wallet_data.is_multisig,
                    multisig_threshold=wallet_data.multisig_threshold,
                    multisig_addresses=wallet_data.multisig_addresses,
                    encrypted_private_key=encrypted_private_key,
                    public_key=public_key,
                    name=wallet_data.name or f"Wallet {address[:8]}...",
                    algo_balance=0,
                )
                
                db_session.add(wallet)
                await db_session.commit()
                await db_session.refresh(wallet)
                
                # Initialize with ALGO asset
                algo_asset = WalletAsset(
                    wallet_id=wallet.id,
                    asset_id=0,  # ALGO
                    asset_name="Algorand",
                    asset_unit_name="ALGO",
                    asset_decimals=6,
                    balance=0,
                    opted_in=True,
                )
                
                db_session.add(algo_asset)
                await db_session.commit()
                
                # Opt into USDC if enabled
                if settings.app.enable_fiat_onramp:
                    try:
                        await self._opt_into_asset(
                # Initialize with ALGO asset
                            UUID(wallet.id), 
                            settings.algorand.usdc_asset_id,
                            db_session
                        )
                    except Exception as e:
                        self.logger.warning(f"Failed to opt into USDC for wallet {wallet.id}: {e}")
                
                # Update balance from blockchain
                await self._update_wallet_balance(wallet.id, db_session)
                
                self.logger.info(f"Created wallet {wallet.id} for user {user_id}")
                
                return WalletResponse.model_validate(wallet)
                
            except Exception as e:
                self.logger.error(f"Failed to create wallet for user {user_id}: {e}")
                raise WalletServiceError(f"Wallet creation failed: {str(e)}")
        
        if session:
            return await _create_wallet(session)
        else:
            async with get_async_session_context() as db_session:
                return await _create_wallet(db_session)
    
    async def get_user_wallets(
        self, 
        user_id: UUID,
        session: Optional[AsyncSession] = None
    ) -> List[WalletResponse]:
        """
        Get all wallets for a user.
        
        Args:
            user_id: User ID
            session: Database session
            
        Returns:
            List[WalletResponse]: User's wallets
        """
        async def _get_wallets(db_session: AsyncSession) -> List[WalletResponse]:
            result = await db_session.execute(
                select(Wallet)
                .where(Wallet.user_id == user_id)
                .options(selectinload(Wallet.assets))
                .order_by(Wallet.created_at.desc())
            )
            wallets = result.scalars().all()
            
            return [WalletResponse.model_validate(wallet) for wallet in wallets]
        
        if session:
            return await _get_wallets(session)
        else:
            async with get_async_session_context() as db_session:
                return await _get_wallets(db_session)
    
    async def get_wallet_by_id(
        self, 
        wallet_id: UUID,
        user_id: Optional[UUID] = None,
        session: Optional[AsyncSession] = None
    ) -> Optional[WalletResponse]:
        """
        Get wallet by ID.
        
        Args:
            wallet_id: Wallet ID
            user_id: Optional user ID for access control
            session: Database session
            
        Returns:
            WalletResponse: Wallet information or None if not found
        """
        async def _get_wallet(db_session: AsyncSession) -> Optional[WalletResponse]:
            query = select(Wallet).where(Wallet.id == wallet_id)
            
            if user_id:
                query = query.where(Wallet.user_id == user_id)
            
            result = await db_session.execute(
                query.options(selectinload(Wallet.assets))
            )
            wallet = result.scalar_one_or_none()
            
            if wallet:
                return WalletResponse.model_validate(wallet)
            return None
        
        if session:
            return await _get_wallet(session)
        else:
            async with get_async_session_context() as db_session:
                return await _get_wallet(db_session)
    
    async def get_wallet_by_address(
        self, 
        address: str,
        session: Optional[AsyncSession] = None
    ) -> Optional[WalletResponse]:
        """
        Get wallet by Algorand address.
        
        Args:
            address: Algorand address
            session: Database session
            
        Returns:
            WalletResponse: Wallet information or None if not found
        """
        async def _get_wallet(db_session: AsyncSession) -> Optional[WalletResponse]:
            result = await db_session.execute(
                select(Wallet)
                .where(Wallet.address == address)
                .options(selectinload(Wallet.assets))
            )
            wallet = result.scalar_one_or_none()
            
            if wallet:
                return WalletResponse.model_validate(wallet)
            return None
        
        if session:
            return await _get_wallet(session)
        else:
            async with get_async_session_context() as db_session:
                return await _get_wallet(db_session)
    
    # ========================================================================
    # Asset Management
    # ========================================================================
    
    async def opt_into_asset(
        self, 
        wallet_id: UUID, 
        asset_id: int,
        user_id: Optional[UUID] = None,
        session: Optional[AsyncSession] = None
    ) -> bool:
        """
        Opt wallet into an Algorand Standard Asset.
        
        Args:
            wallet_id: Wallet ID
            asset_id: Asset ID to opt into
            user_id: Optional user ID for access control
            session: Database session
            
        Returns:
            bool: True if successful
            
        Raises:
            WalletNotFoundError: If wallet not found
            WalletServiceError: If opt-in fails
        """
        async def _opt_in(db_session: AsyncSession) -> bool:
            # Get wallet
            wallet = await self._get_wallet_with_access_check(
                wallet_id, user_id, db_session
            )
            
            # Check if already opted in
            existing_asset = await db_session.execute(
                select(WalletAsset).where(
                    and_(
                        WalletAsset.wallet_id == wallet_id,
                        WalletAsset.asset_id == asset_id
                    )
                )
            )
            
            if existing_asset.scalar_one_or_none():
                self.logger.info(f"Wallet {wallet_id} already opted into asset {asset_id}")
                return True
            
            # Perform blockchain opt-in
            success = await self._opt_into_asset(wallet_id, asset_id, db_session)
            
            if success:
                self.logger.info(f"Successfully opted wallet {wallet_id} into asset {asset_id}")
            
            return success
        
        if session:
            return await _opt_in(session)
        else:
            async with get_async_session_context() as db_session:
                return await _opt_in(db_session)
    
    async def get_wallet_balance(
        self, 
        wallet_id: UUID,
        user_id: Optional[UUID] = None,
        refresh: bool = False,
        session: Optional[AsyncSession] = None
    ) -> WalletBalanceResponse:
        """
        Get comprehensive wallet balance information.
        
        Args:
            wallet_id: Wallet ID
            user_id: Optional user ID for access control
            refresh: Whether to refresh from blockchain
            session: Database session
            
        Returns:
            WalletBalanceResponse: Wallet balance information
            
        Raises:
            WalletNotFoundError: If wallet not found
        """
        async def _get_balance(db_session: AsyncSession) -> WalletBalanceResponse:
            # Get wallet with assets
            wallet = await self._get_wallet_with_access_check(
                wallet_id, user_id, db_session
            )
            
            # Refresh balance if requested
            if refresh:
                await self._update_wallet_balance(wallet_id, db_session)
                await db_session.refresh(wallet)
            
            # Get all assets
            result = await db_session.execute(
                select(WalletAsset)
                .where(WalletAsset.wallet_id == wallet_id)
                .order_by(WalletAsset.asset_id)
            )
            assets = result.scalars().all()
            
            # Convert to response format
            asset_balances = [
                AssetBalance(
                    asset_id=asset.asset_id,
                    asset_name=asset.asset_name,
                    asset_unit_name=asset.asset_unit_name,
                    balance=asset.balance,
                    decimals=asset.asset_decimals,
                    frozen=asset.frozen,
                )
                for asset in assets
            ]
            
            # Calculate total USD value (placeholder - would integrate with price feeds)
            total_value_usd = await self._calculate_portfolio_value_usd(assets)
            
            return WalletBalanceResponse(
                wallet_id=wallet.id,
                address=wallet.address,
                algo_balance=wallet.algo_balance,
                assets=asset_balances,
                total_value_usd=total_value_usd,
                last_updated=wallet.last_balance_update or wallet.updated_at,
            )
        
        if session:
            return await _get_balance(session)
        else:
            async with get_async_session_context() as db_session:
                return await _get_balance(db_session)
    
    # ========================================================================
    # Transaction Operations
    # ========================================================================
    
    async def send_payment(
        self,
        wallet_id: UUID,
        recipient_address: str,
        amount: int,
        asset_id: int = 0,
        note: Optional[str] = None,
        user_id: Optional[UUID] = None,
        session: Optional[AsyncSession] = None
    ) -> str:
        """
        Send payment from wallet to recipient.
        
        Args:
            wallet_id: Source wallet ID
            recipient_address: Recipient Algorand address
            amount: Amount to send (in smallest unit)
            asset_id: Asset ID (0 for ALGO)
            note: Optional transaction note
            user_id: Optional user ID for access control
            session: Database session
            
        Returns:
            str: Transaction ID
            
        Raises:
            WalletNotFoundError: If wallet not found
            InsufficientFundsError: If insufficient balance
            WalletServiceError: If transaction fails
        """
        async def _send_payment(db_session: AsyncSession) -> str:
            # Get wallet and verify access
            wallet = await self._get_wallet_with_access_check(
                wallet_id, user_id, db_session
            )
            
            # Check balance
            if asset_id == 0:
                # ALGO payment
                if wallet.algo_balance < amount:
                    raise InsufficientFundsError(
                        f"Insufficient ALGO balance: {wallet.algo_balance} < {amount}"
                    )
            else:
                # ASA payment
                asset_result = await db_session.execute(
                    select(WalletAsset).where(
                        and_(
                            WalletAsset.wallet_id == wallet_id,
                            WalletAsset.asset_id == asset_id
                        )
                    )
                )
                asset = asset_result.scalar_one_or_none()
                
                if not asset:
                    raise AssetNotOptedInError(f"Wallet not opted into asset {asset_id}")
                
                if asset.balance < amount:
                    raise InsufficientFundsError(
                        f"Insufficient asset balance: {asset.balance} < {amount}"
                    )
            
            # Get private key
            private_key = await self.encryption_service.decrypt_sensitive_data(
                wallet.encrypted_private_key, wallet.user_id
            )
            
            # Create and send transaction
            txn_id = await self.algorand_client.send_payment(
                private_key=private_key,
                recipient=recipient_address,
                amount=amount,
                asset_id=asset_id,
                note=note
            )
            
            # Update wallet balance
            await self._update_wallet_balance(wallet_id, db_session)
            
            self.logger.info(
                f"Sent payment from wallet {wallet_id} to {recipient_address}: "
                f"{amount} of asset {asset_id}, txn: {txn_id}"
            )
            
            return txn_id
        
        if session:
            return await _send_payment(session)
        else:
            async with get_async_session_context() as db_session:
                return await _send_payment(db_session)
    
    async def create_multisig_transaction(
        self,
        wallet_id: UUID,
        recipient_address: str,
        amount: int,
        asset_id: int = 0,
        note: Optional[str] = None,
        user_id: Optional[UUID] = None,
        session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Create a multisig transaction for approval.
        
        Args:
            wallet_id: Source wallet ID
            recipient_address: Recipient address
            amount: Amount to send
            asset_id: Asset ID (0 for ALGO)
            note: Optional transaction note
            user_id: Optional user ID for access control
            session: Database session
            
        Returns:
            Dict[str, Any]: Transaction data for signing
            
        Raises:
            WalletNotFoundError: If wallet not found
            WalletServiceError: If wallet is not multisig
        """
        async def _create_multisig_txn(db_session: AsyncSession) -> Dict[str, Any]:
            # Get wallet and verify it's multisig
            wallet = await self._get_wallet_with_access_check(
                wallet_id, user_id, db_session
            )
            
            if not wallet.is_multisig:
                raise WalletServiceError("Wallet is not configured for multisig")
            
            # Create unsigned transaction
            unsigned_txn = await self.algorand_client.create_unsigned_payment(
                sender=wallet.address,
                recipient=recipient_address,
                amount=amount,
                asset_id=asset_id,
                note=note
            )
            
            return {
                "transaction": unsigned_txn,
                "multisig_addresses": wallet.multisig_addresses,
                "threshold": wallet.multisig_threshold,
                "wallet_id": str(wallet_id),
            }
        
        if session:
            return await _create_multisig_txn(session)
        else:
            async with get_async_session_context() as db_session:
                return await _create_multisig_txn(db_session)
    
    # ========================================================================
    # Balance and Asset Updates
    # ========================================================================
    
    async def refresh_wallet_balance(
        self,
        wallet_id: UUID,
        user_id: Optional[UUID] = None,
        session: Optional[AsyncSession] = None
    ) -> WalletBalanceResponse:
        """
        Refresh wallet balance from blockchain.
        
        Args:
            wallet_id: Wallet ID
            user_id: Optional user ID for access control
            session: Database session
            
        Returns:
            WalletBalanceResponse: Updated balance information
        """
        async def _refresh_balance(db_session: AsyncSession) -> WalletBalanceResponse:
            await self._update_wallet_balance(wallet_id, db_session)
            return await self.get_wallet_balance(wallet_id, user_id, False, db_session)
        
        if session:
            return await _refresh_balance(session)
        else:
            async with get_async_session_context() as db_session:
                return await _refresh_balance(db_session)
    
    async def refresh_all_user_wallets(
        self,
        user_id: UUID,
        session: Optional[AsyncSession] = None
    ) -> List[WalletBalanceResponse]:
        """
        Refresh all wallet balances for a user.
        
        Args:
            user_id: User ID
            session: Database session
            
        Returns:
            List[WalletBalanceResponse]: Updated balance information for all wallets
        """
        async def _refresh_all(db_session: AsyncSession) -> List[WalletBalanceResponse]:
            # Get all user wallets
            result = await db_session.execute(
                select(Wallet).where(Wallet.user_id == user_id)
            )
            wallets = result.scalars().all()
            
            # Refresh each wallet
            balances = []
            for wallet in wallets:
                await self._update_wallet_balance(wallet.id, db_session)
                balance = await self.get_wallet_balance(wallet.id, user_id, False, db_session)
                balances.append(balance)
            
            return balances
        
        if session:
            return await _refresh_all(session)
        else:
            async with get_async_session_context() as db_session:
                return await _refresh_all(db_session)
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    async def _get_wallet_with_access_check(
        self,
        wallet_id: UUID,
        user_id: Optional[UUID],
        session: AsyncSession
    ) -> Wallet:
        """Get wallet with optional user access check."""
        query = select(Wallet).where(Wallet.id == wallet_id)
        
        if user_id:
            query = query.where(Wallet.user_id == user_id)
        
        result = await session.execute(query)
        wallet = result.scalar_one_or_none()
        
        if not wallet:
            raise WalletNotFoundError(f"Wallet {wallet_id} not found")
        
        return wallet
    
    async def _opt_into_asset(
        self,
        wallet_id: UUID,
        asset_id: int,
        session: AsyncSession
    ) -> bool:
        """Perform asset opt-in on blockchain and update database."""
        try:
            # Get wallet
            wallet = await self._get_wallet_with_access_check(wallet_id, None, session)
            
            # Get asset information from blockchain
            asset_info = await self.algorand_client.get_asset_info(asset_id)
            
            if not asset_info:
                raise WalletServiceError(f"Asset {asset_id} not found")
            
            # Get private key
            private_key = await self.encryption_service.decrypt_sensitive_data(
                wallet.encrypted_private_key, wallet.user_id
            )
            
            # Perform opt-in transaction
            txn_id = await self.algorand_client.opt_into_asset(
                private_key=private_key,
                asset_id=asset_id
            )
            
            # Create asset record
            wallet_asset = WalletAsset(
                wallet_id=wallet_id,
                asset_id=asset_id,
                asset_name=asset_info.get('name'),
                asset_unit_name=asset_info.get('unit-name'),
                asset_decimals=asset_info.get('decimals', 6),
                balance=0,
                opted_in=True,
                asset_url=asset_info.get('url'),
                asset_metadata_hash=asset_info.get('metadata-hash'),
                manager_address=asset_info.get('manager'),
                reserve_address=asset_info.get('reserve'),
                freeze_address=asset_info.get('freeze'),
                clawback_address=asset_info.get('clawback'),
            )
            
            session.add(wallet_asset)
            await session.commit()
            
            self.logger.info(f"Opted wallet {wallet_id} into asset {asset_id}, txn: {txn_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to opt wallet {wallet_id} into asset {asset_id}: {e}")
            raise WalletServiceError(f"Asset opt-in failed: {str(e)}")
    
    async def _update_wallet_balance(
        self,
        wallet_id: UUID,
        session: AsyncSession
    ) -> None:
        """Update wallet balance from blockchain."""
        try:
            # Get wallet
            wallet = await self._get_wallet_with_access_check(wallet_id, None, session)
            
            # Get account info from blockchain
            account_info = await self.algorand_client.get_account_info(wallet.address)
            
            if not account_info:
                self.logger.warning(f"Could not get account info for wallet {wallet_id}")
                return
            
            # Update ALGO balance
            algo_balance = account_info.get('amount', 0)
            await session.execute(
                update(Wallet)
                .where(Wallet.id == wallet_id)
                .values(
                    algo_balance=algo_balance,
                    last_balance_update=func.now()
                )
            )
            
            # Update asset balances
            assets = account_info.get('assets', [])
            for asset_data in assets:
                asset_id = asset_data['asset-id']
                balance = asset_data['amount']
                frozen = asset_data.get('is-frozen', False)
                
                # Update or create asset record
                await session.execute(
                    update(WalletAsset)
                    .where(
                        and_(
                            WalletAsset.wallet_id == wallet_id,
                            WalletAsset.asset_id == asset_id
                        )
                    )
                    .values(
                        balance=balance,
                        frozen=frozen,
                        last_balance_update=func.now()
                    )
                )
            
            await session.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to update balance for wallet {wallet_id}: {e}")
            # Don't raise exception to avoid breaking other operations
    
    async def _calculate_portfolio_value_usd(
        self,
        assets: List[WalletAsset]
    ) -> Optional[Decimal]:
        """Calculate total portfolio value in USD."""
        # Placeholder implementation - would integrate with price feeds
        try:
            total_value = Decimal('0')
            
            for asset in assets:
                if asset.balance > 0:
                    # Get price from price feed service
                    price_usd = await self._get_asset_price_usd(asset.asset_id)
                    if price_usd:
                        asset_value = (Decimal(asset.balance) / (10 ** asset.asset_decimals)) * price_usd
                        total_value += asset_value
            
            return total_value
            
        except Exception as e:
            self.logger.error(f"Failed to calculate portfolio value: {e}")
            return None
    
    async def _get_asset_price_usd(self, asset_id: int) -> Optional[Decimal]:
        """Get asset price in USD."""
        # Placeholder implementation - would integrate with price feeds
        # For now, return hardcoded values for testing
        price_map = {
            0: Decimal('0.25'),  # ALGO
            settings.algorand.usdc_asset_id: Decimal('1.00'),  # USDC
        }
        
        return price_map.get(asset_id)


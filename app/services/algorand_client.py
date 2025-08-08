"""
Enhanced Algorand client service for ImaniPay Blockchain Service.

This module provides comprehensive Algorand blockchain integration including
transaction creation, asset management, and account operations.
"""

import logging
from typing import Optional, Dict, Any, List
from decimal import Decimal

from algosdk import account, mnemonic, transaction, encoding
from algosdk.v2client import algod, indexer
from algosdk.future.transaction import PaymentTxn, AssetTransferTxn, AssetOptInTxn
from algosdk.error import AlgodHTTPError, IndexerHTTPError

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AlgorandClientError(Exception):
    """Base exception for Algorand client errors."""
    pass


class TransactionError(AlgorandClientError):
    """Exception raised when transaction fails."""
    pass


class AccountError(AlgorandClientError):
    """Exception raised when account operation fails."""
    pass


class AlgorandClient:
    """Enhanced Algorand blockchain client."""
    
    def __init__(self):
        self.algod_client = algod.AlgodClient(
            settings.algorand.algod_token,
            settings.algorand.algod_address
        )
        
        self.indexer_client = indexer.IndexerClient(
            settings.algorand.indexer_token,
            settings.algorand.indexer_address
        )
        
        self.logger = logger
    
    # ========================================================================
    # Account Operations
    # ========================================================================
    
    async def get_account_info(self, address: str) -> Optional[Dict[str, Any]]:
        """
        Get account information from Algorand blockchain.
        
        Args:
            address: Algorand address
            
        Returns:
            Dict[str, Any]: Account information or None if not found
            
        Raises:
            AccountError: If account lookup fails
        """
        try:
            account_info = self.algod_client.account_info(address)
            return account_info
            
        except AlgodHTTPError as e:
            if e.code == 404:
                self.logger.warning(f"Account {address} not found on blockchain")
                return None
            else:
                self.logger.error(f"Failed to get account info for {address}: {e}")
                raise AccountError(f"Account lookup failed: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error getting account info for {address}: {e}")
            raise AccountError(f"Account lookup failed: {str(e)}")
    
    async def get_account_balance(self, address: str, asset_id: int = 0) -> int:
        """
        Get account balance for specific asset.
        
        Args:
            address: Algorand address
            asset_id: Asset ID (0 for ALGO)
            
        Returns:
            int: Balance in smallest unit
            
        Raises:
            AccountError: If balance lookup fails
        """
        try:
            account_info = await self.get_account_info(address)
            
            if not account_info:
                return 0
            
            if asset_id == 0:
                # ALGO balance
                return account_info.get('amount', 0)
            else:
                # ASA balance
                assets = account_info.get('assets', [])
                for asset in assets:
                    if asset['asset-id'] == asset_id:
                        return asset['amount']
                return 0
                
        except Exception as e:
            self.logger.error(f"Failed to get balance for {address}, asset {asset_id}: {e}")
            raise AccountError(f"Balance lookup failed: {str(e)}")
    
    async def is_account_opted_into_asset(self, address: str, asset_id: int) -> bool:
        """
        Check if account is opted into an asset.
        
        Args:
            address: Algorand address
            asset_id: Asset ID
            
        Returns:
            bool: True if opted in, False otherwise
        """
        try:
            account_info = await self.get_account_info(address)
            
            if not account_info:
                return False
            
            assets = account_info.get('assets', [])
            for asset in assets:
                if asset['asset-id'] == asset_id:
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to check asset opt-in for {address}, asset {asset_id}: {e}")
            return False
    
    # ========================================================================
    # Asset Operations
    # ========================================================================
    
    async def get_asset_info(self, asset_id: int) -> Optional[Dict[str, Any]]:
        """
        Get asset information from blockchain.
        
        Args:
            asset_id: Asset ID
            
        Returns:
            Dict[str, Any]: Asset information or None if not found
        """
        try:
            asset_info = self.algod_client.asset_info(asset_id)
            return asset_info.get('params', {})
            
        except AlgodHTTPError as e:
            if e.code == 404:
                self.logger.warning(f"Asset {asset_id} not found")
                return None
            else:
                self.logger.error(f"Failed to get asset info for {asset_id}: {e}")
                raise AlgorandClientError(f"Asset lookup failed: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error getting asset info for {asset_id}: {e}")
            raise AlgorandClientError(f"Asset lookup failed: {str(e)}")
    
    async def opt_into_asset(
        self, 
        private_key: str, 
        asset_id: int,
        note: Optional[str] = None
    ) -> str:
        """
        Opt account into an Algorand Standard Asset.
        
        Args:
            private_key: Account private key
            asset_id: Asset ID to opt into
            note: Optional transaction note
            
        Returns:
            str: Transaction ID
            
        Raises:
            TransactionError: If opt-in transaction fails
        """
        try:
            # Get account address
            sender_address = account.address_from_private_key(private_key)
            
            # Check if already opted in
            if await self.is_account_opted_into_asset(sender_address, asset_id):
                self.logger.info(f"Account {sender_address} already opted into asset {asset_id}")
                return "already_opted_in"
            
            # Get suggested parameters
            params = self.algod_client.suggested_params()
            
            # Create opt-in transaction
            opt_in_txn = AssetOptInTxn(
                sender=sender_address,
                sp=params,
                index=asset_id,
                note=note.encode() if note else None
            )
            
            # Sign and send transaction
            signed_txn = opt_in_txn.sign(private_key)
            txn_id = self.algod_client.send_transaction(signed_txn)
            
            # Wait for confirmation
            await self._wait_for_confirmation(txn_id)
            
            self.logger.info(f"Successfully opted {sender_address} into asset {asset_id}, txn: {txn_id}")
            return txn_id
            
        except Exception as e:
            self.logger.error(f"Asset opt-in failed for asset {asset_id}: {e}")
            raise TransactionError(f"Asset opt-in failed: {str(e)}")
    
    # ========================================================================
    # Payment Operations
    # ========================================================================
    
    async def send_payment(
        self,
        private_key: str,
        recipient: str,
        amount: int,
        asset_id: int = 0,
        note: Optional[str] = None
    ) -> str:
        """
        Send payment transaction.
        
        Args:
            private_key: Sender private key
            recipient: Recipient address
            amount: Amount to send (in smallest unit)
            asset_id: Asset ID (0 for ALGO)
            note: Optional transaction note
            
        Returns:
            str: Transaction ID
            
        Raises:
            TransactionError: If payment fails
        """
        try:
            # Get sender address
            sender_address = account.address_from_private_key(private_key)
            
            # Validate recipient address
            if not encoding.is_valid_address(recipient):
                raise TransactionError(f"Invalid recipient address: {recipient}")
            
            # Check sender balance
            balance = await self.get_account_balance(sender_address, asset_id)
            if balance < amount:
                raise TransactionError(
                    f"Insufficient balance: {balance} < {amount} for asset {asset_id}"
                )
            
            # Get suggested parameters
            params = self.algod_client.suggested_params()
            
            if asset_id == 0:
                # ALGO payment
                txn = PaymentTxn(
                    sender=sender_address,
                    sp=params,
                    receiver=recipient,
                    amt=amount,
                    note=note.encode() if note else None
                )
            else:
                # ASA payment
                txn = AssetTransferTxn(
                    sender=sender_address,
                    sp=params,
                    receiver=recipient,
                    amt=amount,
                    index=asset_id,
                    note=note.encode() if note else None
                )
            
            # Sign and send transaction
            signed_txn = txn.sign(private_key)
            txn_id = self.algod_client.send_transaction(signed_txn)
            
            # Wait for confirmation
            await self._wait_for_confirmation(txn_id)
            
            self.logger.info(
                f"Payment sent from {sender_address} to {recipient}: "
                f"{amount} of asset {asset_id}, txn: {txn_id}"
            )
            return txn_id
            
        except Exception as e:
            self.logger.error(f"Payment failed: {e}")
            raise TransactionError(f"Payment failed: {str(e)}")
    
    async def create_unsigned_payment(
        self,
        sender: str,
        recipient: str,
        amount: int,
        asset_id: int = 0,
        note: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create unsigned payment transaction for multisig.
        
        Args:
            sender: Sender address
            recipient: Recipient address
            amount: Amount to send
            asset_id: Asset ID (0 for ALGO)
            note: Optional transaction note
            
        Returns:
            Dict[str, Any]: Unsigned transaction data
        """
        try:
            # Validate addresses
            if not encoding.is_valid_address(sender):
                raise TransactionError(f"Invalid sender address: {sender}")
            if not encoding.is_valid_address(recipient):
                raise TransactionError(f"Invalid recipient address: {recipient}")
            
            # Get suggested parameters
            params = self.algod_client.suggested_params()
            
            if asset_id == 0:
                # ALGO payment
                txn = PaymentTxn(
                    sender=sender,
                    sp=params,
                    receiver=recipient,
                    amt=amount,
                    note=note.encode() if note else None
                )
            else:
                # ASA payment
                txn = AssetTransferTxn(
                    sender=sender,
                    sp=params,
                    receiver=recipient,
                    amt=amount,
                    index=asset_id,
                    note=note.encode() if note else None
                )
            
            return {
                "transaction": encoding.msgpack_encode(txn),
                "transaction_id": txn.get_txid(),
                "sender": sender,
                "recipient": recipient,
                "amount": amount,
                "asset_id": asset_id,
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create unsigned payment: {e}")
            raise TransactionError(f"Unsigned transaction creation failed: {str(e)}")
    
    # ========================================================================
    # Transaction History
    # ========================================================================
    
    async def get_account_transactions(
        self,
        address: str,
        limit: int = 50,
        next_token: Optional[str] = None,
        asset_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get account transaction history.
        
        Args:
            address: Account address
            limit: Maximum number of transactions
            next_token: Pagination token
            asset_id: Optional asset ID filter
            
        Returns:
            Dict[str, Any]: Transaction history
        """
        try:
            params = {
                "limit": limit,
                "address": address,
            }
            
            if next_token:
                params["next"] = next_token
            
            if asset_id is not None:
                params["asset-id"] = asset_id
            
            response = self.indexer_client.search_transactions(**params)
            return response
            
        except IndexerHTTPError as e:
            self.logger.error(f"Failed to get transactions for {address}: {e}")
            raise AlgorandClientError(f"Transaction history lookup failed: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error getting transactions for {address}: {e}")
            raise AlgorandClientError(f"Transaction history lookup failed: {str(e)}")
    
    async def get_transaction_info(self, txn_id: str) -> Optional[Dict[str, Any]]:
        """
        Get transaction information by ID.
        
        Args:
            txn_id: Transaction ID
            
        Returns:
            Dict[str, Any]: Transaction information or None if not found
        """
        try:
            response = self.indexer_client.search_transactions(txid=txn_id)
            transactions = response.get('transactions', [])
            
            if transactions:
                return transactions[0]
            return None
            
        except IndexerHTTPError as e:
            if e.code == 404:
                return None
            else:
                self.logger.error(f"Failed to get transaction {txn_id}: {e}")
                raise AlgorandClientError(f"Transaction lookup failed: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error getting transaction {txn_id}: {e}")
            raise AlgorandClientError(f"Transaction lookup failed: {str(e)}")
    
    # ========================================================================
    # Network Operations
    # ========================================================================
    
    async def get_network_status(self) -> Dict[str, Any]:
        """
        Get Algorand network status.
        
        Returns:
            Dict[str, Any]: Network status information
        """
        try:
            status = self.algod_client.status()
            return {
                "last_round": status.get("last-round"),
                "last_consensus_version": status.get("last-consensus-version"),
                "next_consensus_version": status.get("next-consensus-version"),
                "next_consensus_version_round": status.get("next-consensus-version-round"),
                "next_consensus_version_supported": status.get("next-consensus-version-supported"),
                "stopped_at_unsupported_round": status.get("stopped-at-unsupported-round"),
                "time_since_last_round": status.get("time-since-last-round"),
                "catchup_time": status.get("catchup-time"),
                "has_sync_finished": status.get("has-sync-finished"),
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get network status: {e}")
            raise AlgorandClientError(f"Network status lookup failed: {str(e)}")
    
    async def get_suggested_params(self) -> Dict[str, Any]:
        """
        Get suggested transaction parameters.
        
        Returns:
            Dict[str, Any]: Suggested parameters
        """
        try:
            params = self.algod_client.suggested_params()
            return {
                "fee": params.fee,
                "first": params.first,
                "last": params.last,
                "gh": params.gh,
                "gen": params.gen,
                "flat_fee": params.flat_fee,
                "consensus_version": params.consensus_version,
                "min_fee": params.min_fee,
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get suggested params: {e}")
            raise AlgorandClientError(f"Suggested params lookup failed: {str(e)}")
    
    # ========================================================================
    # Health Check
    # ========================================================================
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Algorand connections.
        
        Returns:
            Dict[str, Any]: Health check results
        """
        health_status = {
            "algod": {"status": "unknown", "error": None},
            "indexer": {"status": "unknown", "error": None},
            "overall": "unknown"
        }
        
        # Test algod connection
        try:
            status = self.algod_client.status()
            health_status["algod"]["status"] = "healthy"
            health_status["algod"]["last_round"] = status.get("last-round")
        except Exception as e:
            health_status["algod"]["status"] = "unhealthy"
            health_status["algod"]["error"] = str(e)
        
        # Test indexer connection
        try:
            health = self.indexer_client.health()
            health_status["indexer"]["status"] = "healthy"
            health_status["indexer"]["round"] = health.get("round")
        except Exception as e:
            health_status["indexer"]["status"] = "unhealthy"
            health_status["indexer"]["error"] = str(e)
        
        # Determine overall status
        if (health_status["algod"]["status"] == "healthy" and 
            health_status["indexer"]["status"] == "healthy"):
            health_status["overall"] = "healthy"
        elif (health_status["algod"]["status"] == "healthy" or 
              health_status["indexer"]["status"] == "healthy"):
            health_status["overall"] = "degraded"
        else:
            health_status["overall"] = "unhealthy"
        
        return health_status
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    async def _wait_for_confirmation(
        self, 
        txn_id: str, 
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Wait for transaction confirmation.
        
        Args:
            txn_id: Transaction ID
            timeout: Timeout in rounds
            
        Returns:
            Dict[str, Any]: Confirmed transaction info
            
        Raises:
            TransactionError: If confirmation times out
        """
        try:
            confirmed_txn = transaction.wait_for_confirmation(
                self.algod_client, txn_id, timeout
            )
            
            self.logger.debug(f"Transaction {txn_id} confirmed in round {confirmed_txn['confirmed-round']}")
            return confirmed_txn
            
        except Exception as e:
            self.logger.error(f"Transaction confirmation failed for {txn_id}: {e}")
            raise TransactionError(f"Transaction confirmation failed: {str(e)}")
    
    def _format_amount(self, amount: int, decimals: int = 6) -> Decimal:
        """Format amount from smallest unit to decimal."""
        return Decimal(amount) / (10 ** decimals)
    
    def _parse_amount(self, amount: Decimal, decimals: int = 6) -> int:
        """Parse amount from decimal to smallest unit."""
        return int(amount * (10 ** decimals))


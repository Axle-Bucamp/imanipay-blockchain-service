"""
AlgoKit LocalNet Manager for ImaniPay Blockchain Service.

This module provides integration with AlgoKit LocalNet for development
and testing of Algorand smart contracts and applications.
"""

import logging
import asyncio
import subprocess
from typing import Dict, Any, Optional, List
from pathlib import Path

from algokit_utils import (
    AlgoClientNetworkConfig,
    ApplicationClient,
    ApplicationSpecification,
    ClientManager,
    get_algod_client,
    get_indexer_client,
    ensure_funded,
    get_account,
    transfer,
)
from algosdk import account, mnemonic
from algosdk.v2client import algod, indexer
from algosdk.error import AlgodHTTPError, IndexerHTTPError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class AlgoKitManager:
    """Manager for AlgoKit LocalNet operations."""
    
    def __init__(self):
        """Initialize AlgoKit manager."""
        self.settings = get_settings()
        self._algod_client: Optional[algod.AlgodClient] = None
        self._indexer_client: Optional[indexer.IndexerClient] = None
        self._localnet_running = False
        
    @property
    def algod_client(self) -> algod.AlgodClient:
        """Get Algorand client based on current network configuration."""
        if self._algod_client is None:
            try:
                if self.settings.algorand.is_localnet:
                    algod_config = AlgoClientNetworkConfig(server=self.settings.algorand.localnet_algod_address, token=self.settings.algorand.localnet_algod_token)
                    self._algod_client = ClientManager.get_algod_client(
                        algod_config
                    )
                else:
                    algod_config = AlgoClientNetworkConfig(server=self.settings.algorand.current_algod_address, token=self.settings.algorand.current_algod_token)

                    self._algod_client = ClientManager.get_algod_client(
                        algod_config
                    )
            except Exception as e:
                logger.error(f"Failed to create algod client: {e}")
                # Fallback to direct client creation
                from algosdk.v2client import algod
                self._algod_client = algod.AlgodClient(
                    self.settings.algorand.current_algod_token,
                    self.settings.algorand.current_algod_address
                )
        return self._algod_client
    
    @property
    def indexer_client(self) -> indexer.IndexerClient:
        """Get Algorand indexer client based on current network configuration."""
        if self._indexer_client is None:
            try:
                if self.settings.algorand.is_localnet:
                    """
                    indexer_address=self.settings.algorand.localnet_indexer_address,
                    indexer_token=self.settings.algorand.localnet_indexer_token
                    """
                    algod_config = AlgoClientNetworkConfig(server=self.settings.algorand.localnet_indexer_address, token=self.settings.algorand.localnet_indexer_token)
                    self._indexer_client = ClientManager.get_indexer_client(algod_config)
                else:
                    algod_config = AlgoClientNetworkConfig(server=self.settings.algorand.current_indexer_address, token=self.settings.algorand.current_indexer_token)
                    self._indexer_client = ClientManager.get_indexer_client(algod_config)
            except Exception as e:
                logger.error(f"Failed to create indexer client: {e}")
                # Fallback to direct client creation
                from algosdk.v2client import indexer
                self._indexer_client = indexer.IndexerClient(
                    self.settings.algorand.current_indexer_token,
                    self.settings.algorand.current_indexer_address
                )
        return self._indexer_client
    
    async def start_localnet(self) -> Dict[str, Any]:
        """Start AlgoKit LocalNet."""
        if not self.settings.algorand.is_localnet:
            raise ValueError("LocalNet start requested but network is not set to 'localnet'")
        
        try:
            logger.info("Starting AlgoKit LocalNet...")
            
            # Start LocalNet using algokit command
            result = subprocess.run(
                ["algokit", "localnet", "start"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                self._localnet_running = True
                logger.info("AlgoKit LocalNet started successfully")
                
                # Wait a moment for services to be ready
                await asyncio.sleep(3)
                
                # Test connection
                status = await self.get_network_status()
                return {
                    "success": True,
                    "message": "LocalNet started successfully",
                    "status": status
                }
            else:
                logger.error(f"Failed to start LocalNet: {result.stderr}")
                return {
                    "success": False,
                    "message": f"Failed to start LocalNet: {result.stderr}",
                    "error": result.stderr
                }
                
        except subprocess.TimeoutExpired:
            logger.error("LocalNet start timed out")
            return {
                "success": False,
                "message": "LocalNet start timed out",
                "error": "Timeout after 60 seconds"
            }
        except Exception as e:
            logger.error(f"Error starting LocalNet: {e}")
            return {
                "success": False,
                "message": f"Error starting LocalNet: {str(e)}",
                "error": str(e)
            }
    
    async def stop_localnet(self) -> Dict[str, Any]:
        """Stop AlgoKit LocalNet."""
        try:
            logger.info("Stopping AlgoKit LocalNet...")
            
            result = subprocess.run(
                ["algokit", "localnet", "stop"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self._localnet_running = False
                logger.info("AlgoKit LocalNet stopped successfully")
                return {
                    "success": True,
                    "message": "LocalNet stopped successfully"
                }
            else:
                logger.warning(f"LocalNet stop warning: {result.stderr}")
                return {
                    "success": True,
                    "message": "LocalNet stop completed with warnings",
                    "warning": result.stderr
                }
                
        except subprocess.TimeoutExpired:
            logger.error("LocalNet stop timed out")
            return {
                "success": False,
                "message": "LocalNet stop timed out",
                "error": "Timeout after 30 seconds"
            }
        except Exception as e:
            logger.error(f"Error stopping LocalNet: {e}")
            return {
                "success": False,
                "message": f"Error stopping LocalNet: {str(e)}",
                "error": str(e)
            }
    
    async def reset_localnet(self) -> Dict[str, Any]:
        """Reset AlgoKit LocalNet to clean state."""
        try:
            logger.info("Resetting AlgoKit LocalNet...")
            
            result = subprocess.run(
                ["algokit", "localnet", "reset"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                logger.info("AlgoKit LocalNet reset successfully")
                
                # Wait for services to restart
                await asyncio.sleep(5)
                
                return {
                    "success": True,
                    "message": "LocalNet reset successfully"
                }
            else:
                logger.error(f"Failed to reset LocalNet: {result.stderr}")
                return {
                    "success": False,
                    "message": f"Failed to reset LocalNet: {result.stderr}",
                    "error": result.stderr
                }
                
        except subprocess.TimeoutExpired:
            logger.error("LocalNet reset timed out")
            return {
                "success": False,
                "message": "LocalNet reset timed out",
                "error": "Timeout after 60 seconds"
            }
        except Exception as e:
            logger.error(f"Error resetting LocalNet: {e}")
            return {
                "success": False,
                "message": f"Error resetting LocalNet: {str(e)}",
                "error": str(e)
            }
    
    async def get_network_status(self) -> Dict[str, Any]:
        """Get current network status."""
        try:
            # Test algod connection
            algod_status = await self._test_algod_connection()
            
            # Test indexer connection
            indexer_status = await self._test_indexer_connection()
            
            return {
                "network": self.settings.algorand.network,
                "algod": algod_status,
                "indexer": indexer_status,
                "localnet_running": self._localnet_running if self.settings.algorand.is_localnet else None
            }
            
        except Exception as e:
            logger.error(f"Error getting network status: {e}")
            return {
                "network": self.settings.algorand.network,
                "error": str(e),
                "algod": {"connected": False, "error": str(e)},
                "indexer": {"connected": False, "error": str(e)}
            }
    
    async def _test_algod_connection(self) -> Dict[str, Any]:
        """Test algod client connection."""
        try:
            status = self.algod_client.status()
            return {
                "connected": True,
                "last_round": status.get("last-round"),
                "time_since_last_round": status.get("time-since-last-round"),
                "catchup_time": status.get("catchup-time"),
                "address": self.settings.algorand.current_algod_address
            }
        except AlgodHTTPError as e:
            logger.error(f"Algod connection error: {e}")
            return {
                "connected": False,
                "error": str(e),
                "address": self.settings.algorand.current_algod_address
            }
        except Exception as e:
            logger.error(f"Unexpected algod error: {e}")
            return {
                "connected": False,
                "error": str(e),
                "address": self.settings.algorand.current_algod_address
            }
    
    async def _test_indexer_connection(self) -> Dict[str, Any]:
        """Test indexer client connection."""
        try:
            health = self.indexer_client.health()
            return {
                "connected": True,
                "round": health.get("round"),
                "is_migrating": health.get("is-migrating"),
                "address": self.settings.algorand.current_indexer_address
            }
        except IndexerHTTPError as e:
            logger.error(f"Indexer connection error: {e}")
            return {
                "connected": False,
                "error": str(e),
                "address": self.settings.algorand.current_indexer_address
            }
        except Exception as e:
            logger.error(f"Unexpected indexer error: {e}")
            return {
                "connected": False,
                "error": str(e),
                "address": self.settings.algorand.current_indexer_address
            }
    
    async def create_test_account(self, initial_balance: int = 10_000_000) -> Dict[str, Any]:
        """Create a test account with initial funding."""
        try:
            # Generate new account
            private_key, address = account.generate_account()
            mnemonic_phrase = mnemonic.from_private_key(private_key)
            
            # Fund account if on LocalNet
            if self.settings.algorand.is_localnet:
                try:
                    # Use AlgoKit utils to fund the account
                    account_info = get_account(
                        name="test_account",
                        parameters={"private_key": private_key}
                    )
                    ensure_funded(
                        client=self.algod_client,
                        account_to_fund=address,
                        min_spending_balance_micro_algos=initial_balance
                    )
                    
                    logger.info(f"Created and funded test account: {address}")
                    
                except Exception as funding_error:
                    logger.warning(f"Account created but funding failed: {funding_error}")
                    return {
                        "success": True,
                        "address": address,
                        "private_key": private_key,
                        "mnemonic": mnemonic_phrase,
                        "funded": False,
                        "funding_error": str(funding_error)
                    }
            
            return {
                "success": True,
                "address": address,
                "private_key": private_key,
                "mnemonic": mnemonic_phrase,
                "funded": self.settings.algorand.is_localnet,
                "initial_balance": initial_balance if self.settings.algorand.is_localnet else 0
            }
            
        except Exception as e:
            logger.error(f"Error creating test account: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_account_info(self, address: str) -> Dict[str, Any]:
        """Get account information."""
        try:
            account_info = self.algod_client.account_info(address)
            
            return {
                "success": True,
                "address": address,
                "balance": account_info.get("amount", 0),
                "min_balance": account_info.get("min-balance", 0),
                "assets": account_info.get("assets", []),
                "apps_local_state": account_info.get("apps-local-state", []),
                "apps_total_schema": account_info.get("apps-total-schema", {}),
                "round": account_info.get("round", 0)
            }
            
        except AlgodHTTPError as e:
            logger.error(f"Error getting account info for {address}: {e}")
            return {
                "success": False,
                "address": address,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error getting account info for {address}: {e}")
            return {
                "success": False,
                "address": address,
                "error": str(e)
            }
    
    def get_network_endpoints(self) -> Dict[str, str]:
        """Get current network endpoints."""
        return {
            "network": self.settings.algorand.network,
            "algod_address": self.settings.algorand.current_algod_address,
            "algod_token": "***" if self.settings.algorand.current_algod_token else "",
            "indexer_address": self.settings.algorand.current_indexer_address,
            "indexer_token": "***" if self.settings.algorand.current_indexer_token else "",
        }


# Global AlgoKit manager instance
_algokit_manager: Optional[AlgoKitManager] = None


def get_algokit_manager() -> AlgoKitManager:
    """Get global AlgoKit manager instance."""
    global _algokit_manager
    if _algokit_manager is None:
        _algokit_manager = AlgoKitManager()
    return _algokit_manager


# Export for easy import
__all__ = ["AlgoKitManager", "get_algokit_manager"]


"""
AlgoKit API endpoints for ImaniPay Blockchain Service.

This module provides REST API endpoints for managing AlgoKit LocalNet
and Algorand network operations.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field

from app.services.algokit_manager import get_algokit_manager, AlgoKitManager
from app.core.config import get_settings

router = APIRouter()


# ============================================================================
# Pydantic Models
# ============================================================================

class NetworkStatusResponse(BaseModel):
    """Network status response model."""
    network: str = Field(..., description="Current network (testnet, mainnet, localnet)")
    algod: Dict[str, Any] = Field(..., description="Algod client status")
    indexer: Dict[str, Any] = Field(..., description="Indexer client status")
    localnet_running: Optional[bool] = Field(None, description="LocalNet running status")


class LocalNetOperationResponse(BaseModel):
    """LocalNet operation response model."""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Operation result message")
    error: Optional[str] = Field(None, description="Error message if operation failed")
    warning: Optional[str] = Field(None, description="Warning message if applicable")


class TestAccountRequest(BaseModel):
    """Test account creation request model."""
    initial_balance: int = Field(default=10_000_000, description="Initial balance in microAlgos")


class TestAccountResponse(BaseModel):
    """Test account creation response model."""
    success: bool = Field(..., description="Account creation success status")
    address: Optional[str] = Field(None, description="Account address")
    private_key: Optional[str] = Field(None, description="Account private key (for testing only)")
    mnemonic: Optional[str] = Field(None, description="Account mnemonic phrase")
    funded: bool = Field(default=False, description="Whether account was funded")
    initial_balance: int = Field(default=0, description="Initial balance in microAlgos")
    error: Optional[str] = Field(None, description="Error message if creation failed")
    funding_error: Optional[str] = Field(None, description="Funding error if applicable")


class AccountInfoResponse(BaseModel):
    """Account information response model."""
    success: bool = Field(..., description="Request success status")
    address: Optional[str] = Field(None, description="Account address")
    balance: int = Field(default=0, description="Account balance in microAlgos")
    min_balance: int = Field(default=0, description="Minimum required balance")
    assets: list = Field(default_factory=list, description="Account assets")
    apps_local_state: list = Field(default_factory=list, description="Local application state")
    apps_total_schema: Dict[str, Any] = Field(default_factory=dict, description="Application schema")
    round: int = Field(default=0, description="Last round")
    error: Optional[str] = Field(None, description="Error message if request failed")


class NetworkEndpointsResponse(BaseModel):
    """Network endpoints response model."""
    network: str = Field(..., description="Current network")
    algod_address: str = Field(..., description="Algod server address")
    algod_token: str = Field(..., description="Algod token (masked)")
    indexer_address: str = Field(..., description="Indexer server address")
    indexer_token: str = Field(..., description="Indexer token (masked)")


# ============================================================================
# Dependency Functions
# ============================================================================

def get_algokit_dependency() -> AlgoKitManager:
    """Get AlgoKit manager dependency."""
    return get_algokit_manager()


# ============================================================================
# Network Status Endpoints
# ============================================================================

@router.get(
    "/status",
    response_model=NetworkStatusResponse,
    summary="Get network status",
    description="Get the current Algorand network status including algod and indexer connectivity"
)
async def get_network_status(
    algokit_manager: AlgoKitManager = Depends(get_algokit_dependency)
) -> NetworkStatusResponse:
    """Get current network status."""
    try:
        status = await algokit_manager.get_network_status()
        return NetworkStatusResponse(**status)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get network status: {str(e)}"
        )


@router.get(
    "/endpoints",
    response_model=NetworkEndpointsResponse,
    summary="Get network endpoints",
    description="Get the current network endpoints configuration"
)
async def get_network_endpoints(
    algokit_manager: AlgoKitManager = Depends(get_algokit_dependency)
) -> NetworkEndpointsResponse:
    """Get current network endpoints."""
    try:
        endpoints = algokit_manager.get_network_endpoints()
        return NetworkEndpointsResponse(**endpoints)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get network endpoints: {str(e)}"
        )


# ============================================================================
# LocalNet Management Endpoints
# ============================================================================

@router.post(
    "/localnet/start",
    response_model=LocalNetOperationResponse,
    summary="Start LocalNet",
    description="Start AlgoKit LocalNet for development and testing"
)
async def start_localnet(
    background_tasks: BackgroundTasks,
    algokit_manager: AlgoKitManager = Depends(get_algokit_dependency)
) -> LocalNetOperationResponse:
    """Start AlgoKit LocalNet."""
    settings = get_settings()
    
    if not settings.algorand.is_localnet:
        raise HTTPException(
            status_code=400,
            detail="LocalNet operations are only available when network is set to 'localnet'"
        )
    
    try:
        result = await algokit_manager.start_localnet()
        return LocalNetOperationResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start LocalNet: {str(e)}"
        )


@router.post(
    "/localnet/stop",
    response_model=LocalNetOperationResponse,
    summary="Stop LocalNet",
    description="Stop AlgoKit LocalNet"
)
async def stop_localnet(
    algokit_manager: AlgoKitManager = Depends(get_algokit_dependency)
) -> LocalNetOperationResponse:
    """Stop AlgoKit LocalNet."""
    try:
        result = await algokit_manager.stop_localnet()
        return LocalNetOperationResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop LocalNet: {str(e)}"
        )


@router.post(
    "/localnet/reset",
    response_model=LocalNetOperationResponse,
    summary="Reset LocalNet",
    description="Reset AlgoKit LocalNet to clean state"
)
async def reset_localnet(
    algokit_manager: AlgoKitManager = Depends(get_algokit_dependency)
) -> LocalNetOperationResponse:
    """Reset AlgoKit LocalNet."""
    settings = get_settings()
    
    if not settings.algorand.is_localnet:
        raise HTTPException(
            status_code=400,
            detail="LocalNet operations are only available when network is set to 'localnet'"
        )
    
    try:
        result = await algokit_manager.reset_localnet()
        return LocalNetOperationResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset LocalNet: {str(e)}"
        )


# ============================================================================
# Account Management Endpoints
# ============================================================================

@router.post(
    "/accounts/create-test",
    response_model=TestAccountResponse,
    summary="Create test account",
    description="Create a test account with optional initial funding (LocalNet only)"
)
async def create_test_account(
    request: TestAccountRequest,
    algokit_manager: AlgoKitManager = Depends(get_algokit_dependency)
) -> TestAccountResponse:
    """Create a test account."""
    try:
        result = await algokit_manager.create_test_account(
            initial_balance=request.initial_balance
        )
        return TestAccountResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create test account: {str(e)}"
        )


@router.get(
    "/accounts/{address}",
    response_model=AccountInfoResponse,
    summary="Get account information",
    description="Get detailed information about an Algorand account"
)
async def get_account_info(
    address: str,
    algokit_manager: AlgoKitManager = Depends(get_algokit_dependency)
) -> AccountInfoResponse:
    """Get account information."""
    # Basic address validation
    if len(address) != 58:
        raise HTTPException(
            status_code=400,
            detail="Invalid Algorand address format"
        )
    
    try:
        result = await algokit_manager.get_account_info(address)
        return AccountInfoResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get account info: {str(e)}"
        )


# ============================================================================
# Development Utilities
# ============================================================================

@router.get(
    "/dev/config",
    summary="Get development configuration",
    description="Get current AlgoKit and network configuration for development"
)
async def get_dev_config():
    """Get development configuration."""
    settings = get_settings()
    
    return {
        "network": settings.algorand.network,
        "is_localnet": settings.algorand.is_localnet,
        "is_testnet": settings.algorand.is_testnet,
        "is_mainnet": settings.algorand.is_mainnet,
        "algod_address": settings.algorand.current_algod_address,
        "indexer_address": settings.algorand.current_indexer_address,
        "usdc_asset_id": settings.algorand.usdc_asset_id,
        "default_fee": settings.algorand.default_fee,
        "confirmation_rounds": settings.algorand.confirmation_rounds,
        "environment": settings.app.environment,
        "debug": settings.app.debug
    }


@router.get(
    "/dev/health",
    summary="Development health check",
    description="Comprehensive health check for development environment"
)
async def dev_health_check(
    algokit_manager: AlgoKitManager = Depends(get_algokit_dependency)
):
    """Development health check."""
    try:
        # Get network status
        network_status = await algokit_manager.get_network_status()
        
        # Get configuration
        settings = get_settings()
        
        return {
            "status": "healthy",
            "timestamp": "2025-01-15T00:00:00Z",  # This would be actual timestamp
            "network": network_status,
            "configuration": {
                "network": settings.algorand.network,
                "environment": settings.app.environment,
                "debug": settings.app.debug
            },
            "services": {
                "algod": network_status["algod"]["connected"],
                "indexer": network_status["indexer"]["connected"],
                "localnet": network_status.get("localnet_running", False)
            }
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": "2025-01-15T00:00:00Z",  # This would be actual timestamp
            "error": str(e)
        }


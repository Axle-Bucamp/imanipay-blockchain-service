"""
ImaniPay Blockchain Service - Simplified FastAPI Application

A blockchain-focused service for Algorand smart contracts and wallet operations.
Simplified version without authentication, managed by external backend.
"""

import logging
import asyncio
from contextlib import asynccontextmanager
import time
from typing import Dict, Any
import uuid

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import get_settings
from app.database import init_database, close_database
from app.middleware.security import SimplifiedSecurityMiddleware

# Import simplified API routers
from app.api import wallets, transactions, health, algokit

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting ImaniPay Blockchain Service (Simplified)...")
    
    try:
        # Initialize database
        await init_database()
        logger.info("Database initialized successfully")
        
        logger.info("ImaniPay Blockchain Service started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down ImaniPay Blockchain Service...")
        
        try:
            # Close database
            await close_database()
            
            logger.info("ImaniPay Blockchain Service shut down successfully")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="ImaniPay Blockchain Service",
    description="""
    A simplified blockchain service focused on Algorand smart contracts and wallet operations.
    
    ## Features
    
    * **Algorand Integration** - Full Algorand blockchain connectivity
    * **Smart Contracts** - Escrow, multi-signature, and batch processing contracts
    * **Wallet Management** - Secure wallet creation and management
    * **Transaction Processing** - Algorand transaction handling
    * **Asset Management** - Algorand Standard Assets (ASA) support
    
    ## Architecture
    
    This service focuses exclusively on blockchain operations:
    - Authentication is handled by external backend
    - No user management or sessions
    - Direct blockchain interactions
    - Smart contract deployment and execution
    
    ## Networks Supported
    
    * **MainNet** - Production Algorand network
    * **TestNet** - Testing Algorand network  
    * **LocalNet** - Local development network (AlgoKit)
    """,

    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "wallets",
            "description": "Algorand wallet management and operations"
        },
        {
            "name": "transactions", 
            "description": "Algorand transaction processing and tracking"
        },
        {
            "name": "contracts",
            "description": "Smart contract deployment and execution"
        },
        {
            "name": "health",
            "description": "Health checks and system status"
        }
    ]
)

# Add simplified security middleware
app.add_middleware(SimplifiedSecurityMiddleware)

# Add rate limiting middleware
app.state.limiter = limiter
async def _rate_limit_exceeded_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded"},
    )
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Add CORS middleware (permissive for external backend integration)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins since auth is external
    allow_credentials=False,  # No credentials needed
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)


# ============================================================================
# Global Exception Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "type": "http_error"
            },
            "request_id": getattr(request.state, "request_id", None),
            "timestamp": asyncio.get_event_loop().time()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "type": "internal_error"
            },
            "request_id": getattr(request.state, "request_id", None),
            "timestamp": asyncio.get_event_loop().time()
        }
    )


@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next):
    """Add a unique request ID to each request and include it in response headers."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all incoming requests and their response times."""
    start_time = time.time()

    client_host = request.client.host if request.client else "unknown"
    logger.info(f"Request: {request.method} {request.url.path} from {client_host}")

    response = await call_next(request)

    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} in {process_time:.3f}s")

    return response

@app.middleware("http")
async def add_csp_header(request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self' https:; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' https://fastapi.tiangolo.com;"
    )
    return response

# ============================================================================
# API Routes
# ============================================================================

# Include API routers (no authentication dependencies)
app.include_router(
    health.router,
    prefix="/health",
    tags=["health"]
)

app.include_router(
    wallets.router,
    prefix="/api/v1/wallets",
    tags=["wallets"]
)

app.include_router(
    transactions.router,
    prefix="/api/v1/transactions",
    tags=["transactions"]
)

app.include_router(
    algokit.router,
    prefix="/api/v1/algokit",
    tags=["algokit"]
)

# Smart contracts router (to be created)
# app.include_router(
#     contracts.router,
#     prefix="/api/v1/contracts",
#     tags=["contracts"]
# )


# ============================================================================
# Root Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "ImaniPay Blockchain Service",
        "version": "2.0.0-simplified",
        "description": "Blockchain-focused service for Algorand operations",
        "status": "operational",
        "features": [
            "Algorand wallet management",
            "Smart contract deployment",
            "Transaction processing", 
            "Asset management",
            "Multi-signature support",
            "Escrow contracts"
        ],
        "networks": [
            "MainNet",
            "TestNet", 
            "LocalNet (AlgoKit)"
        ],
        "documentation": "/docs",
        "authentication": "Managed by external backend"
    }


@app.get("/api/v1/info")
@limiter.limit("100/minute")
async def api_info(request: Request):
    """API information endpoint."""
    return {
        "api_version": "v1",
        "service": "ImaniPay Blockchain Service (Simplified)",
        "environment": settings.app.environment if hasattr(settings, 'app') else "development",
        "blockchain": {
            "network": "Algorand",
            "supported_networks": ["mainnet", "testnet", "localnet"],
            "features": [
                "Native ALGO transfers",
                "Algorand Standard Assets (ASA)",
                "Smart contracts (TEAL)",
                "Multi-signature wallets",
                "Atomic transactions"
            ]
        },
        "capabilities": {
            "wallet_creation": True,
            "transaction_signing": True,
            "smart_contract_deployment": True,
            "asset_management": True,
            "multi_signature": True,
            "batch_transactions": True
        },
        "authentication": {
            "managed_externally": True,
            "requires_api_key": False,
            "session_management": False
        }
    }


# ============================================================================
# Development Endpoints
# ============================================================================

@app.get("/dev/network-status")
async def network_status():
    """Get Algorand network status."""
    # This will be implemented with AlgoKit integration
    return {
        "message": "Network status endpoint - to be implemented with AlgoKit",
        "networks": {
            "mainnet": {"status": "unknown"},
            "testnet": {"status": "unknown"},
            "localnet": {"status": "unknown"}
        }
    }


# ============================================================================
# Application Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Default configuration for simplified service
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable reload for development
        log_level="info",
        access_log=True
    )


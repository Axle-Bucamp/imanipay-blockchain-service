"""
ImaniPay Blockchain Service - Enhanced FastAPI Application

A comprehensive blockchain payment service for cross-border African payments
with fiat-to-crypto conversions, USDC bridge, and Algorand integration.
"""

import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import get_settings
from app.core.startup import startup_event, shutdown_event
from app.database import init_db, close_db
from app.services.external_processors import processor_manager
from app.services.exchange_rate import ExchangeRateService

# Import API routers
from app.api import (
    wallets, transactions, payments, compliance, 
    exchange_rates, webhooks, health
)

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

# Security
security = HTTPBearer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting ImaniPay Blockchain Service...")
    
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized successfully")
        
        # Run startup tasks
        await startup_event()
        logger.info("Startup tasks completed")
        
        # Start background tasks
        if settings.app.environment == "production":
            # Start exchange rate refresh task
            exchange_rate_service = ExchangeRateService()
            asyncio.create_task(periodic_rate_refresh(exchange_rate_service))
            logger.info("Background tasks started")
        
        logger.info("ImaniPay Blockchain Service started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down ImaniPay Blockchain Service...")
        
        try:
            # Run shutdown tasks
            await shutdown_event()
            
            # Close external processors
            await processor_manager.close_all()
            
            # Close database
            await close_db()
            
            logger.info("ImaniPay Blockchain Service shut down successfully")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="ImaniPay Blockchain Service",
    description="""
    A comprehensive blockchain payment service for cross-border African payments.
    
    ## Features
    
    * **Cross-border payments** - Bypass local taxes for African co-workers
    * **Multi-currency support** - Fiat to USDC to Algorand conversions
    * **Regulatory compliance** - KYC/AML verification and monitoring
    * **Secure wallet management** - Multi-signature and encrypted storage
    * **Real-time exchange rates** - Multiple provider aggregation
    * **Comprehensive APIs** - RESTful endpoints for all operations
    
    ## Payment Flows
    
    1. **Fiat to USDC** - Convert local currency to USDC via payment processors
    2. **USDC to Algorand** - Bridge USDC to Algorand blockchain
    3. **Algorand/USDC to Fiat** - Convert crypto back to local currency
    4. **Cross-border transfers** - Direct peer-to-peer payments
    
    ## Security
    
    * OAuth2 authentication with JWT tokens
    * End-to-end encryption for sensitive data
    * Rate limiting and DDoS protection
    * Comprehensive audit logging
    * Multi-factor authentication support
    """,
    version="2.0.0",
    docs_url="/docs" if not settings.app.is_production else None,
    redoc_url="/redoc" if not settings.app.is_production else None,
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "wallets",
            "description": "Wallet management and operations"
        },
        {
            "name": "transactions", 
            "description": "Transaction processing and tracking"
        },
        {
            "name": "payments",
            "description": "Payment processing and conversions"
        },
        {
            "name": "compliance",
            "description": "KYC/AML verification and risk assessment"
        },
        {
            "name": "exchange-rates",
            "description": "Currency exchange rates and conversions"
        },
        {
            "name": "webhooks",
            "description": "Webhook endpoints for external integrations"
        },
        {
            "name": "health",
            "description": "Health checks and system status"
        }
    ]
)

# Add rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.security.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Add trusted host middleware for production
if settings.app.is_production:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.security.allowed_hosts
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
            "request_id": getattr(request.state, "request_id", None)
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
            "request_id": getattr(request.state, "request_id", None)
        }
    )


# ============================================================================
# Middleware
# ============================================================================

@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next):
    """Add request ID to all requests."""
    import uuid
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all requests."""
    import time
    
    start_time = time.time()
    
    # Log request
    logger.info(
        f"Request: {request.method} {request.url.path} "
        f"from {request.client.host if request.client else 'unknown'}"
    )
    
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(
        f"Response: {response.status_code} "
        f"in {process_time:.3f}s"
    )
    
    return response


# ============================================================================
# API Routes
# ============================================================================

# Include API routers
app.include_router(
    health.router,
    prefix="/health",
    tags=["health"]
)

app.include_router(
    wallets.router,
    prefix="/api/v1/wallets",
    tags=["wallets"],
    dependencies=[Depends(security)] if settings.security.require_auth else []
)

app.include_router(
    transactions.router,
    prefix="/api/v1/transactions",
    tags=["transactions"],
    dependencies=[Depends(security)] if settings.security.require_auth else []
)

app.include_router(
    payments.router,
    prefix="/api/v1/payments",
    tags=["payments"],
    dependencies=[Depends(security)] if settings.security.require_auth else []
)

app.include_router(
    compliance.router,
    prefix="/api/v1/compliance",
    tags=["compliance"],
    dependencies=[Depends(security)] if settings.security.require_auth else []
)

app.include_router(
    exchange_rates.router,
    prefix="/api/v1/exchange-rates",
    tags=["exchange-rates"]
)

app.include_router(
    webhooks.router,
    prefix="/webhooks",
    tags=["webhooks"]
)


# ============================================================================
# Root Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "ImaniPay Blockchain Service",
        "version": "2.0.0",
        "description": "Cross-border payment service for African co-workers",
        "status": "operational",
        "features": [
            "Fiat to USDC conversion",
            "USDC to Algorand bridge", 
            "Algorand/USDC to fiat conversion",
            "Cross-border payments",
            "KYC/AML compliance",
            "Multi-signature wallets",
            "Real-time exchange rates"
        ],
        "documentation": "/docs" if not settings.app.is_production else None
    }


@app.get("/api/v1/info")
@limiter.limit("10/minute")
async def api_info(request: Request):
    """API information endpoint."""
    return {
        "api_version": "v1",
        "service": "ImaniPay Blockchain Service",
        "environment": settings.app.environment,
        "supported_currencies": {
            "fiat": ["USD", "EUR", "NGN", "KES", "GHS", "ZAR"],
            "crypto": ["ALGO", "USDC", "BTC", "ETH"]
        },
        "supported_networks": ["Algorand"],
        "payment_processors": ["Circle", "YellowCard", "Transak", "Coinbase"],
        "features": {
            "kyc_verification": True,
            "aml_screening": True,
            "multi_signature": True,
            "cross_border_payments": True,
            "real_time_rates": True,
            "webhook_notifications": True
        }
    }


# ============================================================================
# Background Tasks
# ============================================================================

async def periodic_rate_refresh(exchange_rate_service: ExchangeRateService):
    """Periodically refresh exchange rates."""
    while True:
        try:
            logger.info("Starting periodic exchange rate refresh...")
            results = await exchange_rate_service.refresh_all_rates()
            logger.info(f"Exchange rate refresh completed: {results}")
            
            # Wait 5 minutes before next refresh
            await asyncio.sleep(300)
            
        except Exception as e:
            logger.error(f"Exchange rate refresh failed: {e}")
            # Wait 1 minute before retry on error
            await asyncio.sleep(60)


# ============================================================================
# Development and Testing Endpoints
# ============================================================================

if not settings.app.is_production:
    
    @app.get("/dev/test-processors")
    async def test_processors():
        """Test external processor connectivity."""
        results = {}
        
        for name, processor in processor_manager.processors.items():
            try:
                # Test with a mock transaction status check
                response = await processor.get_transaction_status("test-123")
                results[name] = {
                    "status": "connected" if response.success else "error",
                    "message": response.message
                }
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "message": str(e)
                }
        
        return {"processor_tests": results}
    
    
    @app.post("/dev/refresh-rates")
    async def refresh_rates_dev(background_tasks: BackgroundTasks):
        """Manually trigger exchange rate refresh."""
        exchange_rate_service = ExchangeRateService()
        background_tasks.add_task(exchange_rate_service.refresh_all_rates)
        
        return {"message": "Exchange rate refresh triggered"}


# ============================================================================
# Application Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.app.port,
        reload=not settings.app.is_production,
        log_level="info",
        access_log=True
    )


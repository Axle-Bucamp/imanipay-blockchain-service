"""
Health check API endpoints for ImaniPay Blockchain Service.

This module provides health check endpoints for monitoring service status,
database connectivity, external service availability, and system metrics.
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database import get_async_session
from app.services.algorand_client import AlgorandClient
from app.services.external_processors import processor_manager
# from app.services.exchange_rate import ExchangeRateService  # Temporarily disabled

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "ImaniPay Blockchain Service",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.app.environment
    }


@router.get("/detailed")
async def detailed_health_check(
    session: AsyncSession = Depends(get_async_session)
):
    """Detailed health check with dependency status."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "ImaniPay Blockchain Service",
        "version": "2.0.0",
        "environment": settings.app.environment,
        "checks": {}
    }
    
    overall_healthy = True
    
    # Database health check
    try:
        result = await session.execute(text("SELECT 1"))
        result.scalar()
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
        overall_healthy = False
    
    # Algorand network health check
    try:
        algorand_client = AlgorandClient()
        network_status = await algorand_client.get_network_status()
        
        if network_status:
            health_status["checks"]["algorand"] = {
                "status": "healthy",
                "message": "Algorand network accessible",
                "data": {
                    "last_round": network_status.get("last_round"),
                    "time_since_last_round": network_status.get("time_since_last_round")
                }
            }
        else:
            health_status["checks"]["algorand"] = {
                "status": "degraded",
                "message": "Algorand network status unknown"
            }
    except Exception as e:
        logger.error(f"Algorand health check failed: {e}")
        health_status["checks"]["algorand"] = {
            "status": "unhealthy",
            "message": f"Algorand network check failed: {str(e)}"
        }
        overall_healthy = False
    
    # Exchange rate service health check
    try:
        exchange_service = ExchangeRateService()
        test_rate = await exchange_service.get_exchange_rate("USD", "EUR", session)
        
        if test_rate:
            health_status["checks"]["exchange_rates"] = {
                "status": "healthy",
                "message": "Exchange rate service operational"
            }
        else:
            health_status["checks"]["exchange_rates"] = {
                "status": "degraded",
                "message": "Exchange rates unavailable"
            }
    except Exception as e:
        logger.error(f"Exchange rate health check failed: {e}")
        health_status["checks"]["exchange_rates"] = {
            "status": "unhealthy",
            "message": f"Exchange rate service failed: {str(e)}"
        }
    
    # External processors health check
    processor_checks = {}
    for name, processor in processor_manager.processors.items():
        try:
            # Test with a mock status check
            response = await processor.get_transaction_status("health-check-test")
            
            if response.success or response.status in ["not_found", "unknown"]:
                processor_checks[name] = {
                    "status": "healthy",
                    "message": "Processor accessible"
                }
            else:
                processor_checks[name] = {
                    "status": "degraded", 
                    "message": f"Processor responded with: {response.message}"
                }
        except Exception as e:
            processor_checks[name] = {
                "status": "unhealthy",
                "message": f"Processor check failed: {str(e)}"
            }
    
    health_status["checks"]["processors"] = processor_checks
    
    # Set overall status
    if not overall_healthy:
        health_status["status"] = "unhealthy"
    elif any(check.get("status") == "degraded" for check in health_status["checks"].values() if isinstance(check, dict)):
        health_status["status"] = "degraded"
    
    return health_status


@router.get("/ready")
async def readiness_check(
    session: AsyncSession = Depends(get_async_session)
):
    """Readiness check for Kubernetes deployments."""
    try:
        # Check database connectivity
        await session.execute(text("SELECT 1"))
        
        # Check critical services
        algorand_client = AlgorandClient()
        network_status = await algorand_client.get_network_status()
        
        if not network_status:
            raise HTTPException(
                status_code=503,
                detail="Algorand network not accessible"
            )
        
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Service not ready: {str(e)}"
        )


@router.get("/live")
async def liveness_check():
    """Liveness check for Kubernetes deployments."""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/metrics")
async def metrics(
    session: AsyncSession = Depends(get_async_session)
):
    """Basic metrics endpoint."""
    try:
        # Get database metrics
        db_metrics = await _get_database_metrics(session)
        
        # Get system metrics
        system_metrics = _get_system_metrics()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "database": db_metrics,
            "system": system_metrics
        }
        
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to collect metrics: {str(e)}"
        )


async def _get_database_metrics(session: AsyncSession) -> Dict[str, Any]:
    """Get database-related metrics."""
    try:
        # Count users
        user_count_result = await session.execute(
            text("SELECT COUNT(*) FROM users")
        )
        user_count = user_count_result.scalar()
        
        # Count transactions (last 24 hours)
        recent_txn_result = await session.execute(
            text("""
                SELECT COUNT(*) FROM transactions 
                WHERE created_at > NOW() - INTERVAL '24 hours'
            """)
        )
        recent_txn_count = recent_txn_result.scalar()
        
        # Count wallets
        wallet_count_result = await session.execute(
            text("SELECT COUNT(*) FROM wallets")
        )
        wallet_count = wallet_count_result.scalar()
        
        return {
            "total_users": user_count,
            "total_wallets": wallet_count,
            "transactions_24h": recent_txn_count,
            "connection_status": "connected"
        }
        
    except Exception as e:
        logger.error(f"Database metrics collection failed: {e}")
        return {
            "connection_status": "error",
            "error": str(e)
        }


def _get_system_metrics() -> Dict[str, Any]:
    """Get system-related metrics."""
    import psutil
    import os
    
    try:
        # CPU and memory usage
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_percent": cpu_percent,
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent
            },
            "disk": {
                "total": disk.total,
                "free": disk.free,
                "percent": (disk.used / disk.total) * 100
            },
            "process_id": os.getpid(),
            "uptime": _get_uptime()
        }
        
    except Exception as e:
        logger.error(f"System metrics collection failed: {e}")
        return {
            "error": str(e)
        }


def _get_uptime() -> float:
    """Get application uptime in seconds."""
    try:
        import time
        # This is a simplified uptime calculation
        # In production, you might want to track actual start time
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
        return uptime_seconds
    except:
        return 0.0


@router.get("/version")
async def version_info():
    """Get version and build information."""
    return {
        "service": "ImaniPay Blockchain Service",
        "version": "2.0.0",
        "api_version": "v1",
        "build_date": "2024-01-01",  # This would be set during build
        "git_commit": "unknown",     # This would be set during build
        "environment": settings.app.environment,
        "python_version": "3.11+",
        "dependencies": {
            "fastapi": "0.104+",
            "sqlalchemy": "2.0+",
            "algorand-sdk": "2.0+",
            "httpx": "0.25+"
        }
    }


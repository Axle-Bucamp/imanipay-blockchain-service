"""
Database connection and session management for ImaniPay Blockchain Service.

This module provides database connectivity, session management, and
connection pooling for the payment platform.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from app.core.config import get_settings
from app.models import Base

logger = logging.getLogger(__name__)
settings = get_settings()


# ============================================================================
# Database Engine Configuration
# ============================================================================

# Async engine for FastAPI endpoints
async_engine = create_async_engine(
    settings.database.postgres_url,
    echo=settings.app.debug,
    pool_size=settings.database.db_pool_size,
    max_overflow=settings.database.db_max_overflow,
    pool_timeout=settings.database.db_pool_timeout,
    pool_pre_ping=True,
    pool_recycle=3600,  # Recycle connections every hour
    poolclass=QueuePool,
    # Connection arguments
    connect_args={
        "server_settings": {
            "application_name": "imanipay_blockchain_service",
            "jit": "off",  # Disable JIT for better performance with short queries
        },
        "command_timeout": 60,
    }
)

# Sync engine for migrations and admin tasks
sync_engine = create_engine(
    settings.database.postgres_url.replace("+asyncpg", "+psycopg2"),
    echo=settings.app.debug,
    pool_size=settings.database.db_pool_size,
    max_overflow=settings.database.db_max_overflow,
    pool_timeout=settings.database.db_pool_timeout,
    pool_pre_ping=True,
    pool_recycle=3600,
    poolclass=QueuePool,
    connect_args={
        "application_name": "imanipay_blockchain_service_sync",
        "options": "-c jit=off",
    }
)

# Session factories
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,
    autocommit=False,
)

SessionLocal = sessionmaker(
    bind=sync_engine,
    autoflush=True,
    autocommit=False,
)


# ============================================================================
# Database Event Listeners
# ============================================================================

@event.listens_for(async_engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set database connection parameters for optimal performance."""
    if hasattr(dbapi_connection, 'execute'):
        # PostgreSQL-specific optimizations
        cursor = dbapi_connection.cursor()
        
        # Set connection-level parameters
        cursor.execute("SET statement_timeout = '300s'")  # 5 minutes
        cursor.execute("SET lock_timeout = '30s'")
        cursor.execute("SET idle_in_transaction_session_timeout = '600s'")  # 10 minutes
        cursor.execute("SET tcp_keepalives_idle = 600")
        cursor.execute("SET tcp_keepalives_interval = 30")
        cursor.execute("SET tcp_keepalives_count = 3")
        
        cursor.close()


@event.listens_for(sync_engine, "connect")
def set_sync_sqlite_pragma(dbapi_connection, connection_record):
    """Set database connection parameters for sync engine."""
    if hasattr(dbapi_connection, 'execute'):
        cursor = dbapi_connection.cursor()
        
        # Set connection-level parameters
        cursor.execute("SET statement_timeout = '300s'")
        cursor.execute("SET lock_timeout = '30s'")
        cursor.execute("SET idle_in_transaction_session_timeout = '600s'")
        
        cursor.close()


# ============================================================================
# Database Session Management
# ============================================================================

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get async database session.
    
    Yields:
        AsyncSession: Database session for async operations
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_session() -> Session:
    """
    Get synchronous database session.
    
    Returns:
        Session: Database session for sync operations
    """
    return SessionLocal()


@asynccontextmanager
async def get_async_session_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for async database sessions.
    
    Yields:
        AsyncSession: Database session with automatic cleanup
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session context error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


# ============================================================================
# Database Initialization and Management
# ============================================================================

async def init_database() -> None:
    """
    Initialize database tables and perform startup checks.
    """
    try:
        logger.info("Initializing database...")
        
        # Create all tables
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


async def close_database() -> None:
    """
    Close database connections and cleanup resources.
    """
    try:
        logger.info("Closing database connections...")
        
        # Close async engine
        await async_engine.dispose()
        
        # Close sync engine
        sync_engine.dispose()
        
        logger.info("Database connections closed successfully")
        
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")
        raise


def create_tables() -> None:
    """
    Create all database tables (sync version for migrations).
    """
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=sync_engine)
        logger.info("Database tables created successfully")
        
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


def drop_tables() -> None:
    """
    Drop all database tables (sync version for cleanup).
    """
    try:
        logger.info("Dropping database tables...")
        Base.metadata.drop_all(bind=sync_engine)
        logger.info("Database tables dropped successfully")
        
    except Exception as e:
        logger.error(f"Error dropping database tables: {e}")
        raise


# ============================================================================
# Database Health Check
# ============================================================================

async def check_database_health() -> dict:
    """
    Check database connectivity and performance.
    
    Returns:
        dict: Database health status information
    """
    try:
        async with get_async_session_context() as session:
            # Test basic connectivity
            result = await session.execute("SELECT 1 as health_check")
            health_check = result.scalar()
            
            # Test connection pool status
            pool = async_engine.pool
            pool_status = {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": pool.invalid(),
            }
            
            return {
                "status": "healthy" if health_check == 1 else "unhealthy",
                "connection_test": health_check == 1,
                "pool_status": pool_status,
                "engine_url": str(async_engine.url).replace(async_engine.url.password or "", "***"),
            }
            
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "connection_test": False,
        }


# ============================================================================
# Transaction Management Utilities
# ============================================================================

@asynccontextmanager
async def database_transaction() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database transactions with automatic rollback on error.
    
    Yields:
        AsyncSession: Database session within a transaction
    """
    async with get_async_session_context() as session:
        async with session.begin():
            try:
                yield session
            except Exception as e:
                logger.error(f"Transaction error, rolling back: {e}")
                await session.rollback()
                raise


async def execute_in_transaction(func, *args, **kwargs):
    """
    Execute a function within a database transaction.
    
    Args:
        func: Function to execute
        *args: Function arguments
        **kwargs: Function keyword arguments
        
    Returns:
        Function result
    """
    async with database_transaction() as session:
        return await func(session, *args, **kwargs)


# ============================================================================
# Database Migration Utilities
# ============================================================================

def get_database_version() -> Optional[str]:
    """
    Get current database schema version.
    
    Returns:
        str: Database version or None if not found
    """
    try:
        with SessionLocal() as session:
            result = session.execute(
                "SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1"
            )
            version = result.scalar()
            return version
            
    except Exception as e:
        logger.warning(f"Could not get database version: {e}")
        return None


def check_database_schema() -> bool:
    """
    Check if database schema is up to date.
    
    Returns:
        bool: True if schema is current, False otherwise
    """
    try:
        # Check if all expected tables exist
        with SessionLocal() as session:
            inspector = session.get_bind().dialect.get_table_names(session.get_bind())
            expected_tables = [table.name for table in Base.metadata.tables.values()]
            
            missing_tables = set(expected_tables) - set(inspector)
            if missing_tables:
                logger.warning(f"Missing database tables: {missing_tables}")
                return False
                
            return True
            
    except Exception as e:
        logger.error(f"Error checking database schema: {e}")
        return False


# ============================================================================
# Database Utilities
# ============================================================================

async def get_database_stats() -> dict:
    """
    Get database statistics and metrics.
    
    Returns:
        dict: Database statistics
    """
    try:
        async with get_async_session_context() as session:
            # Get table sizes
            table_stats = await session.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            """)
            
            tables = [
                {
                    "schema": row[0],
                    "table": row[1],
                    "size": row[2],
                    "size_bytes": row[3],
                }
                for row in table_stats.fetchall()
            ]
            
            # Get database size
            db_size = await session.execute("""
                SELECT pg_size_pretty(pg_database_size(current_database())) as db_size,
                       pg_database_size(current_database()) as db_size_bytes
            """)
            db_size_row = db_size.fetchone()
            
            # Get connection stats
            connection_stats = await session.execute("""
                SELECT 
                    count(*) as total_connections,
                    count(*) FILTER (WHERE state = 'active') as active_connections,
                    count(*) FILTER (WHERE state = 'idle') as idle_connections
                FROM pg_stat_activity 
                WHERE datname = current_database()
            """)
            conn_stats = connection_stats.fetchone()
            
            return {
                "database_size": db_size_row[0],
                "database_size_bytes": db_size_row[1],
                "total_connections": conn_stats[0],
                "active_connections": conn_stats[1],
                "idle_connections": conn_stats[2],
                "tables": tables,
            }
            
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return {"error": str(e)}


# ============================================================================
# Export commonly used objects
# ============================================================================

__all__ = [
    "async_engine",
    "sync_engine",
    "AsyncSessionLocal",
    "SessionLocal",
    "get_async_session",
    "get_sync_session",
    "get_async_session_context",
    "init_database",
    "close_database",
    "create_tables",
    "drop_tables",
    "check_database_health",
    "database_transaction",
    "execute_in_transaction",
    "get_database_version",
    "check_database_schema",
    "get_database_stats",
]


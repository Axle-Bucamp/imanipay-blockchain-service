"""
Configuration settings for ImaniPay Blockchain Service.

This module provides comprehensive configuration management for all aspects
of the payment platform including database, blockchain, external APIs,
security, and operational settings.
"""

import os
from typing import Optional, List, Dict, Any
from pydantic import validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings import SettingsConfigDict



class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    # PostgreSQL Primary Database
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_user: str = Field(default="imanipay")
    postgres_password: str = Field(default="")
    postgres_db: str = Field(default="imanipay")
    postgres_ssl_mode: str = Field(default="prefer")
    
    # Redis Cache
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_password: Optional[str] = Field(default=None)
    redis_db: int = Field(default=0)
    
    # Connection Pool Settings
    db_pool_size: int = Field(default=20)
    db_max_overflow: int = Field(default=30)
    db_pool_timeout: int = Field(default=30)
    
    @property
    def postgres_url(self) -> str:
        """Generate PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            f"?sslmode={self.postgres_ssl_mode}"
        )
    
    @property
    def redis_url(self) -> str:
        """Generate Redis connection URL."""
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"


class AlgorandSettings(BaseSettings):
    """Algorand blockchain configuration settings."""
    
    # Network Configuration
    algod_address: str = Field(default="https://testnet-api.algonode.cloud")
    algod_token: str = Field(default="")
    indexer_address: str = Field(default="https://testnet-idx.algonode.cloud")
    indexer_token: str = Field(default="")
    
    # Network Type
    network: str = Field(default="testnet")  # testnet, mainnet
    
    # Asset Configuration
    usdc_asset_id: int = Field(default=10458941)  # Testnet USDC
    platform_token_id: Optional[int] = Field(default=None)
    
    # Transaction Configuration
    default_fee: int = Field(default=1000)  # microAlgos
    confirmation_rounds: int = Field(default=4)
    
    # Wallet Configuration
    master_wallet_mnemonic: Optional[str] = Field(default=None)
    hot_wallet_mnemonic: Optional[str] = Field(default=None)
    
    @validator('network')
    def validate_network(cls, v):
        if v not in ['testnet', 'mainnet']:
            raise ValueError('Network must be either testnet or mainnet')
        return v


class SecuritySettings(BaseSettings):
    """Security and authentication configuration."""
    
    # JWT Configuration
    secret_key: str = Field(default="p0qcVKw+V9oogCkXde0sxTb3k1L438lghJ3/OUp8wKQjL4vhUGzQReWGHBulirLhDV0DQDiScY5ri2u5oZ3yvA==")
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    refresh_token_expire_days: int = Field(default=7)
    
    # Password Security
    password_min_length: int = Field(default=8)
    password_require_uppercase: bool = Field(default=True)
    password_require_lowercase: bool = Field(default=True)
    password_require_numbers: bool = Field(default=True)
    password_require_symbols: bool = Field(default=True)
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=100)
    rate_limit_window: int = Field(default=3600)  # seconds
    
    # CORS Configuration
    cors_origins: List[str] = Field(default=["*"])
    cors_methods: List[str] = Field(default=["*"])
    cors_headers: List[str] = Field(default=["*"])
    
    # Encryption
    encryption_key: Optional[str] = Field(default=None)
    
    @validator('secret_key')
    def validate_secret_key(cls, v):
        if not v or len(v) < 32:
            raise ValueError('SECRET_KEY must be at least 32 characters long')
        return v


class PaymentProcessorSettings(BaseSettings):
    """External payment processor configuration."""
    
    # Circle API Configuration
    circle_api_key: Optional[str] = Field(default=None)
    circle_base_url: str = Field(default="https://api-sandbox.circle.com")
    circle_webhook_secret: Optional[str] = Field(default=None)
    
    # Yellow Card Configuration
    yellowcard_api_key: Optional[str] = Field(default=None)
    yellowcard_base_url: str = Field(default="https://api.yellowcard.io")
    yellowcard_webhook_secret: Optional[str] = Field(default=None)
    
    # Transak Configuration
    transak_api_key: Optional[str] = Field(default=None)
    transak_base_url: str = Field(default="https://api.transak.com")
    transak_webhook_secret: Optional[str] = Field(default=None)
    
    # Coinbase Configuration
    coinbase_api_key: Optional[str] = Field(default=None)
    coinbase_api_secret: Optional[str] = Field(default=None)
    coinbase_base_url: str = Field(default="https://api.coinbase.com")


class ComplianceSettings(BaseSettings):
    """Compliance and KYC/AML configuration."""
    
    # KYC Provider Configuration
    kyc_provider: str = Field(default="jumio")  # jumio, onfido, etc.
    kyc_api_key: Optional[str] = Field(default=None)
    kyc_api_secret: Optional[str] = Field(default=None)
    kyc_base_url: Optional[str] = Field(default=None)
    
    # AML Configuration
    aml_provider: str = Field(default="chainalysis")
    aml_api_key: Optional[str] = Field(default=None)
    aml_base_url: Optional[str] = Field(default=None)
    
    # Transaction Limits
    daily_transaction_limit: float = Field(default=10000.0)
    monthly_transaction_limit: float = Field(default=50000.0)
    single_transaction_limit: float = Field(default=5000.0)
    
    # Risk Scoring
    high_risk_threshold: int = Field(default=80)
    medium_risk_threshold: int = Field(default=50)
    
    # Reporting
    suspicious_activity_threshold: float = Field(default=10000.0)
    large_transaction_threshold: float = Field(default=3000.0)


class MonitoringSettings(BaseSettings):
    """Monitoring and observability configuration."""
    
    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")  # json, text
    
    # Sentry Configuration
    sentry_dsn: Optional[str] = Field(default=None)
    sentry_environment: str = Field(default="development")
    
    # Metrics
    enable_metrics: bool = Field(default=True)
    metrics_port: int = Field(default=8001)
    
    # Health Checks
    health_check_interval: int = Field(default=30)  # seconds


class ApplicationSettings(BaseSettings):
    """Main application configuration."""
    
    # Application Info
    app_name: str = Field(default="ImaniPay Blockchain Service")
    app_version: str = Field(default="1.0.0")
    app_description: str = Field(default="Cross-border payment platform for Africa")
    
    # Environment
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    
    # Server Configuration
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    workers: int = Field(default=1)
    
    # API Configuration
    api_v1_prefix: str = Field(default="/api/v1")
    docs_url: str = Field(default="/docs")
    redoc_url: str = Field(default="/redoc")
    
    # Feature Flags
    enable_registration: bool = Field(default=True)
    enable_kyc: bool = Field(default=True)
    enable_cross_border: bool = Field(default=True)
    enable_fiat_onramp: bool = Field(default=True)
    
    @validator('environment')
    def validate_environment(cls, v):
        if v not in ['development', 'staging', 'production']:
            raise ValueError('Environment must be development, staging, or production')
        return v


class Settings(BaseSettings):
    """Main settings class that combines all configuration sections."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Configuration Sections
    app: ApplicationSettings = ApplicationSettings()
    database: DatabaseSettings = DatabaseSettings()
    algorand: AlgorandSettings = AlgorandSettings()
    security: SecuritySettings = SecuritySettings()
    payment_processors: PaymentProcessorSettings = PaymentProcessorSettings()
    compliance: ComplianceSettings = ComplianceSettings()
    monitoring: MonitoringSettings = MonitoringSettings()
    project_name: str = Field(default="imanypay")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Initialize nested settings
        self.app = ApplicationSettings()
        self.database = DatabaseSettings()
        self.algorand = AlgorandSettings()
        self.security = SecuritySettings()
        self.payment_processors = PaymentProcessorSettings()
        self.compliance = ComplianceSettings()
        self.monitoring = MonitoringSettings()
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app.environment == "development"
    
    def get_cors_config(self) -> Dict[str, Any]:
        """Get CORS configuration for FastAPI."""
        return {
            "allow_origins": self.security.cors_origins,
            "allow_credentials": True,
            "allow_methods": self.security.cors_methods,
            "allow_headers": self.security.cors_headers,
        }


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings


# Environment-specific configurations
def get_database_url() -> str:
    """Get the database URL for the current environment."""
    return settings.database.postgres_url


def get_redis_url() -> str:
    """Get the Redis URL for the current environment."""
    return settings.database.redis_url


def get_algorand_config() -> Dict[str, Any]:
    """Get Algorand configuration dictionary."""
    return {
        "algod_address": settings.algorand.algod_address,
        "algod_token": settings.algorand.algod_token,
        "indexer_address": settings.algorand.indexer_address,
        "indexer_token": settings.algorand.indexer_token,
        "network": settings.algorand.network,
        "usdc_asset_id": settings.algorand.usdc_asset_id,
    }


def validate_configuration() -> None:
    """Validate critical configuration settings."""
    errors = []
    
    # Check required security settings
    if not settings.security.secret_key:
        errors.append("SECRET_KEY is required")
    
    # Check database configuration
    if not settings.database.postgres_password and settings.app.environment == "production":
        errors.append("POSTGRES_PASSWORD is required in production")
    
    # Check Algorand configuration
    if not settings.algorand.algod_address:
        errors.append("ALGOD_ADDRESS is required")
    
    # Check payment processor configuration for production
    if settings.app.environment == "production":
        if not settings.payment_processors.circle_api_key:
            errors.append("CIRCLE_API_KEY is required in production")
    
    if errors:
        raise ValueError(f"Configuration validation failed: {', '.join(errors)}")


# Validate configuration on import
if os.getenv("SKIP_CONFIG_VALIDATION") != "true":
    try:
        validate_configuration()
    except ValueError as e:
        print(f"Warning: {e}")


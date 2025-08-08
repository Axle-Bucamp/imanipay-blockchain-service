"""
Configuration settings for ImaniPay Blockchain Service.

This module provides comprehensive configuration management for all aspects
of the payment platform including database, blockchain, external APIs,
security, and operational settings.
"""

import os
from typing import Optional, List, Dict, Any
from pydantic import BaseSettings, validator, Field
from pydantic_settings import SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    # PostgreSQL Primary Database
    postgres_host: str = Field(default="localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")
    postgres_user: str = Field(default="imanipay", env="POSTGRES_USER")
    postgres_password: str = Field(default="", env="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="imanipay", env="POSTGRES_DB")
    postgres_ssl_mode: str = Field(default="prefer", env="POSTGRES_SSL_MODE")
    
    # Redis Cache
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")
    
    # Connection Pool Settings
    db_pool_size: int = Field(default=20, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=30, env="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, env="DB_POOL_TIMEOUT")
    
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
    algod_address: str = Field(default="https://testnet-api.algonode.cloud", env="ALGOD_ADDRESS")
    algod_token: str = Field(default="", env="ALGOD_TOKEN")
    indexer_address: str = Field(default="https://testnet-idx.algonode.cloud", env="INDEXER_ADDRESS")
    indexer_token: str = Field(default="", env="INDEXER_TOKEN")
    
    # Network Type
    network: str = Field(default="testnet", env="ALGORAND_NETWORK")  # testnet, mainnet
    
    # Asset Configuration
    usdc_asset_id: int = Field(default=10458941, env="USDC_ASSET_ID")  # Testnet USDC
    platform_token_id: Optional[int] = Field(default=None, env="PLATFORM_TOKEN_ID")
    
    # Transaction Configuration
    default_fee: int = Field(default=1000, env="ALGORAND_DEFAULT_FEE")  # microAlgos
    confirmation_rounds: int = Field(default=4, env="ALGORAND_CONFIRMATION_ROUNDS")
    
    # Wallet Configuration
    master_wallet_mnemonic: Optional[str] = Field(default=None, env="MASTER_WALLET_MNEMONIC")
    hot_wallet_mnemonic: Optional[str] = Field(default=None, env="HOT_WALLET_MNEMONIC")
    
    @validator('network')
    def validate_network(cls, v):
        if v not in ['testnet', 'mainnet']:
            raise ValueError('Network must be either testnet or mainnet')
        return v


class SecuritySettings(BaseSettings):
    """Security and authentication configuration."""
    
    # JWT Configuration
    secret_key: str = Field(default="", env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # Password Security
    password_min_length: int = Field(default=8, env="PASSWORD_MIN_LENGTH")
    password_require_uppercase: bool = Field(default=True, env="PASSWORD_REQUIRE_UPPERCASE")
    password_require_lowercase: bool = Field(default=True, env="PASSWORD_REQUIRE_LOWERCASE")
    password_require_numbers: bool = Field(default=True, env="PASSWORD_REQUIRE_NUMBERS")
    password_require_symbols: bool = Field(default=True, env="PASSWORD_REQUIRE_SYMBOLS")
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=3600, env="RATE_LIMIT_WINDOW")  # seconds
    
    # CORS Configuration
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    cors_methods: List[str] = Field(default=["*"], env="CORS_METHODS")
    cors_headers: List[str] = Field(default=["*"], env="CORS_HEADERS")
    
    # Encryption
    encryption_key: Optional[str] = Field(default=None, env="ENCRYPTION_KEY")
    
    @validator('secret_key')
    def validate_secret_key(cls, v):
        if not v or len(v) < 32:
            raise ValueError('SECRET_KEY must be at least 32 characters long')
        return v


class PaymentProcessorSettings(BaseSettings):
    """External payment processor configuration."""
    
    # Circle API Configuration
    circle_api_key: Optional[str] = Field(default=None, env="CIRCLE_API_KEY")
    circle_base_url: str = Field(default="https://api-sandbox.circle.com", env="CIRCLE_BASE_URL")
    circle_webhook_secret: Optional[str] = Field(default=None, env="CIRCLE_WEBHOOK_SECRET")
    
    # Yellow Card Configuration
    yellowcard_api_key: Optional[str] = Field(default=None, env="YELLOWCARD_API_KEY")
    yellowcard_base_url: str = Field(default="https://api.yellowcard.io", env="YELLOWCARD_BASE_URL")
    yellowcard_webhook_secret: Optional[str] = Field(default=None, env="YELLOWCARD_WEBHOOK_SECRET")
    
    # Transak Configuration
    transak_api_key: Optional[str] = Field(default=None, env="TRANSAK_API_KEY")
    transak_base_url: str = Field(default="https://api.transak.com", env="TRANSAK_BASE_URL")
    transak_webhook_secret: Optional[str] = Field(default=None, env="TRANSAK_WEBHOOK_SECRET")
    
    # Coinbase Configuration
    coinbase_api_key: Optional[str] = Field(default=None, env="COINBASE_API_KEY")
    coinbase_api_secret: Optional[str] = Field(default=None, env="COINBASE_API_SECRET")
    coinbase_base_url: str = Field(default="https://api.coinbase.com", env="COINBASE_BASE_URL")


class ComplianceSettings(BaseSettings):
    """Compliance and KYC/AML configuration."""
    
    # KYC Provider Configuration
    kyc_provider: str = Field(default="jumio", env="KYC_PROVIDER")  # jumio, onfido, etc.
    kyc_api_key: Optional[str] = Field(default=None, env="KYC_API_KEY")
    kyc_api_secret: Optional[str] = Field(default=None, env="KYC_API_SECRET")
    kyc_base_url: Optional[str] = Field(default=None, env="KYC_BASE_URL")
    
    # AML Configuration
    aml_provider: str = Field(default="chainalysis", env="AML_PROVIDER")
    aml_api_key: Optional[str] = Field(default=None, env="AML_API_KEY")
    aml_base_url: Optional[str] = Field(default=None, env="AML_BASE_URL")
    
    # Transaction Limits
    daily_transaction_limit: float = Field(default=10000.0, env="DAILY_TRANSACTION_LIMIT")
    monthly_transaction_limit: float = Field(default=50000.0, env="MONTHLY_TRANSACTION_LIMIT")
    single_transaction_limit: float = Field(default=5000.0, env="SINGLE_TRANSACTION_LIMIT")
    
    # Risk Scoring
    high_risk_threshold: int = Field(default=80, env="HIGH_RISK_THRESHOLD")
    medium_risk_threshold: int = Field(default=50, env="MEDIUM_RISK_THRESHOLD")
    
    # Reporting
    suspicious_activity_threshold: float = Field(default=10000.0, env="SUSPICIOUS_ACTIVITY_THRESHOLD")
    large_transaction_threshold: float = Field(default=3000.0, env="LARGE_TRANSACTION_THRESHOLD")


class MonitoringSettings(BaseSettings):
    """Monitoring and observability configuration."""
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")  # json, text
    
    # Sentry Configuration
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")
    sentry_environment: str = Field(default="development", env="SENTRY_ENVIRONMENT")
    
    # Metrics
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=8001, env="METRICS_PORT")
    
    # Health Checks
    health_check_interval: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")  # seconds


class ApplicationSettings(BaseSettings):
    """Main application configuration."""
    
    # Application Info
    app_name: str = Field(default="ImaniPay Blockchain Service", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    app_description: str = Field(default="Cross-border payment platform for Africa", env="APP_DESCRIPTION")
    
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    workers: int = Field(default=1, env="WORKERS")
    
    # API Configuration
    api_v1_prefix: str = Field(default="/api/v1", env="API_V1_PREFIX")
    docs_url: str = Field(default="/docs", env="DOCS_URL")
    redoc_url: str = Field(default="/redoc", env="REDOC_URL")
    
    # Feature Flags
    enable_registration: bool = Field(default=True, env="ENABLE_REGISTRATION")
    enable_kyc: bool = Field(default=True, env="ENABLE_KYC")
    enable_cross_border: bool = Field(default=True, env="ENABLE_CROSS_BORDER")
    enable_fiat_onramp: bool = Field(default=True, env="ENABLE_FIAT_ONRAMP")
    
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


"""
Simplified configuration settings for ImaniPay Blockchain Service.

This module provides configuration management focused on blockchain operations
without authentication or complex external integrations.
"""

import os
from typing import Optional, List, Dict, Any
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from decimal import Decimal


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Direct database URL (overrides PostgreSQL settings if provided)
    database_url: Optional[str] = Field(default=None, description="Direct database URL")
    
    # PostgreSQL Database
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_user: str = Field(default="imanipay", description="PostgreSQL username")
    postgres_password: str = Field(default="", description="PostgreSQL password")
    postgres_db: str = Field(default="imanipay_blockchain", description="PostgreSQL database name")
    postgres_ssl_mode: str = Field(default="prefer", description="PostgreSQL SSL mode")
    
    # Connection Pool Settings
    db_pool_size: int = Field(default=10, description="Database connection pool size")
    db_max_overflow: int = Field(default=20, description="Database max overflow connections")
    db_pool_timeout: int = Field(default=30, description="Database pool timeout in seconds")
    
    @property
    def postgres_url(self) -> str:
        """Generate PostgreSQL connection URL."""
        # Use direct database URL if provided
        if self.database_url:
            return self.database_url
            
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            f"?sslmode={self.postgres_ssl_mode}"
        )


class AlgorandSettings(BaseSettings):
    """Algorand blockchain configuration settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="ALGORAND_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Network Configuration
    algod_address: str = Field(
        default="https://testnet-api.algonode.cloud", 
        description="Algorand node address"
    )
    algod_token: str = Field(default="", description="Algorand node token")
    indexer_address: str = Field(
        default="https://testnet-idx.algonode.cloud", 
        description="Algorand indexer address"
    )
    indexer_token: str = Field(default="", description="Algorand indexer token")
    
    # Network Type
    network: str = Field(default="testnet", description="Algorand network (testnet, mainnet, localnet)")
    
    # Asset Configuration
    usdc_asset_id: int = Field(default=10458941, description="USDC Asset ID (testnet)")
    
    # Wallet Configuration
    master_wallet_mnemonic: str = Field(default="", description="Master wallet mnemonic phrase")
    hot_wallet_mnemonic: str = Field(default="", description="Hot wallet mnemonic phrase")
    platform_token_id: int = Field(default=0, description="Platform token/application ID")
    
    # Transaction Configuration
    default_fee: int = Field(default=1000, description="Default transaction fee in microAlgos")
    confirmation_rounds: int = Field(default=4, description="Number of confirmation rounds to wait")
    
    # LocalNet Configuration (for AlgoKit)
    localnet_algod_address: str = Field(default="http://localhost:4001", description="LocalNet algod address")
    localnet_algod_token: str = Field(default="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", description="LocalNet algod token")
    localnet_indexer_address: str = Field(default="http://localhost:8980", description="LocalNet indexer address")
    localnet_indexer_token: str = Field(default="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", description="LocalNet indexer token")
    
    @field_validator('network')
    @classmethod
    def validate_network(cls, v: str) -> str:
        """Validate network type."""
        allowed_networks = ['testnet', 'mainnet', 'localnet']
        if v.lower() not in allowed_networks:
            raise ValueError(f'Network must be one of: {", ".join(allowed_networks)}')
        return v.lower()
    
    @property
    def is_localnet(self) -> bool:
        """Check if using LocalNet."""
        return self.network == "localnet"
    
    @property
    def is_testnet(self) -> bool:
        """Check if using TestNet."""
        return self.network == "testnet"
    
    @property
    def is_mainnet(self) -> bool:
        """Check if using MainNet."""
        return self.network == "mainnet"
    
    @property
    def current_algod_address(self) -> str:
        """Get current algod address based on network."""
        if self.is_localnet:
            return self.localnet_algod_address
        return self.algod_address
    
    @property
    def current_algod_token(self) -> str:
        """Get current algod token based on network."""
        if self.is_localnet:
            return self.localnet_algod_token
        return self.algod_token
    
    @property
    def current_indexer_address(self) -> str:
        """Get current indexer address based on network."""
        if self.is_localnet:
            return self.localnet_indexer_address
        return self.indexer_address
    
    @property
    def current_indexer_token(self) -> str:
        """Get current indexer token based on network."""
        if self.is_localnet:
            return self.localnet_indexer_token
        return self.indexer_token


class AppSettings(BaseSettings):
    """Application configuration settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application Info
    name: str = Field(default="ImaniPay Blockchain Service", description="Application name")
    version: str = Field(default="2.0.0", description="Application version")
    description: str = Field(
        default="Blockchain-focused service for Algorand smart contracts and wallet operations",
        description="Application description"
    )
    
    # Environment
    environment: str = Field(default="development", description="Application environment")
    debug: bool = Field(default=True, description="Debug mode")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    
    # API Configuration
    api_prefix: str = Field(default="/api/v1", description="API prefix")
    docs_url: Optional[str] = Field(default="/docs", description="Documentation URL")
    redoc_url: Optional[str] = Field(default="/redoc", description="ReDoc URL")

    enable_registration: bool = Field(default=True)
    enable_kyc: bool = Field(default=True)
    enable_cross_border: bool = Field(default=True)
    enable_fiat_onramp: bool = Field(default=True)
    
    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment."""
        allowed_envs = ['development', 'testing', 'staging', 'production']
        if v.lower() not in allowed_envs:
            raise ValueError(f'Environment must be one of: {", ".join(allowed_envs)}')
        return v.lower()
    
    @property
    def is_development(self) -> bool:
        """Check if in development mode."""
        return self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if in production mode."""
        return self.environment == "production"


class SecuritySettings(BaseSettings):
    """Basic security configuration settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="SECURITY_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Encryption
    encryption_key: str = Field(
        default="your-32-character-encryption-key",
        description="Encryption key for sensitive data"
    )
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    default_rate_limit: str = Field(default="1000/minute", description="Default rate limit")
    
    # CORS
    allowed_origins: List[str] = Field(
        default=["*"], 
        description="Allowed CORS origins"
    )
    
    # Request Validation
    max_request_size: int = Field(default=10 * 1024 * 1024, description="Max request size in bytes (10MB)")


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Logging Level
    level: str = Field(default="INFO", description="Logging level")
    
    # Log Format
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )
    
    # File Logging
    file_enabled: bool = Field(default=False, description="Enable file logging")
    file_path: str = Field(default="logs/app.log", description="Log file path")
    
    @field_validator('level')
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate logging level."""
        allowed_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed_levels:
            raise ValueError(f'Log level must be one of: {", ".join(allowed_levels)}')
        return v.upper()


class ComplianceSettings(BaseSettings):
    """Compliance configuration settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="COMPLIANCE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # KYC Configuration
    kyc_provider: str = Field(default="mock", description="KYC provider")
    kyc_enabled: bool = Field(default=True, description="Enable KYC verification")
    
    # AML Configuration
    aml_provider: str = Field(default="mock", description="AML provider")
    aml_enabled: bool = Field(default=True, description="Enable AML screening")
    
    # Risk Thresholds
    high_risk_threshold: int = Field(default=80, description="High risk threshold")
    medium_risk_threshold: int = Field(default=50, description="Medium risk threshold")
    
    # Transaction Limits
    single_transaction_limit: Decimal = Field(default=Decimal("10000"), description="Single transaction limit")
    daily_transaction_limit: Decimal = Field(default=Decimal("50000"), description="Daily transaction limit")
    monthly_transaction_limit: Decimal = Field(default=Decimal("500000"), description="Monthly transaction limit")
    
    # Suspicious Activity
    suspicious_activity_threshold: Decimal = Field(default=Decimal("5000"), description="Suspicious activity threshold")
    large_transaction_threshold: Decimal = Field(default=Decimal("10000"), description="Large transaction threshold")


class PaymentProcessorsSettings(BaseSettings):
    """Payment processors configuration settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="PAYMENT_PROCESSORS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Circle Configuration
    circle_api_key: str = Field(default="", description="Circle API key")
    circle_base_url: str = Field(default="https://api-sandbox.circle.com", description="Circle API base URL")
    circle_webhook_secret: str = Field(default="", description="Circle webhook secret")
    
    # YellowCard Configuration
    yellowcard_api_key: str = Field(default="", description="YellowCard API key")
    yellowcard_base_url: str = Field(default="https://api.yellowcard.io", description="YellowCard API base URL")
    yellowcard_webhook_secret: str = Field(default="", description="YellowCard webhook secret")
    
    # Transak Configuration
    transak_api_key: str = Field(default="", description="Transak API key")
    transak_base_url: str = Field(default="https://api.transak.com", description="Transak API base URL")
    transak_webhook_secret: str = Field(default="", description="Transak webhook secret")
    
    # Coinbase Configuration
    coinbase_api_key: str = Field(default="", description="Coinbase API key")
    coinbase_base_url: str = Field(default="https://api.coinbase.com", description="Coinbase API base URL")
    coinbase_webhook_secret: str = Field(default="", description="Coinbase webhook secret")


class Settings(BaseSettings):
    """Main settings class combining all configuration sections."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore extra fields from environment
    )
    
    # Configuration sections
    app: AppSettings = Field(default_factory=AppSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    algorand: AlgorandSettings = Field(default_factory=AlgorandSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    compliance: ComplianceSettings = Field(default_factory=ComplianceSettings)
    payment_processors: PaymentProcessorsSettings = Field(default_factory=PaymentProcessorsSettings)
    
    def __init__(self, **kwargs):
        """Initialize settings with nested configuration."""
        super().__init__(**kwargs)
        
        # Initialize nested settings with environment variables
        self.app = AppSettings()
        self.database = DatabaseSettings()
        self.algorand = AlgorandSettings()
        self.security = SecuritySettings()
        self.logging = LoggingSettings()
        self.compliance = ComplianceSettings()
        self.payment_processors = PaymentProcessorsSettings()


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment."""
    global _settings
    _settings = Settings()
    return _settings


# Export settings classes for direct use
__all__ = [
    "Settings",
    "AppSettings", 
    "DatabaseSettings",
    "AlgorandSettings",
    "SecuritySettings",
    "LoggingSettings",
    "ComplianceSettings",
    "PaymentProcessorsSettings",
    "get_settings",
    "reload_settings"
]


"""
Simplified SQLAlchemy database models for ImaniPay Blockchain Service.

This module defines blockchain-focused database models without authentication.
"""

import enum
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum, ForeignKey, Integer, 
    Numeric, String, Text, JSON, Index, CheckConstraint,
    UniqueConstraint, BigInteger
)
from sqlalchemy.dialects.postgresql import UUID, INET
# Use JSON instead of JSON for SQLite compatibility
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func


# ============================================================================
# Base Model and Mixins
# ============================================================================

Base = declarative_base()


class TimestampMixin:
    """Mixin for timestamp fields."""
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


# ============================================================================
# Enumerations
# ============================================================================

class TransactionTypeEnum(enum.Enum):
    """Transaction type enumeration."""
    ALGORAND_TRANSFER = "algorand_transfer"
    ASSET_TRANSFER = "asset_transfer"
    SMART_CONTRACT_CALL = "smart_contract_call"
    ESCROW_PAYMENT = "escrow_payment"
    MULTISIG_TRANSACTION = "multisig_transaction"
    BATCH_TRANSACTION = "batch_transaction"


class TransactionStatusEnum(enum.Enum):
    """Transaction status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WalletTypeEnum(enum.Enum):
    """Wallet type enumeration."""
    STANDARD = "standard"
    MULTISIG = "multisig"
    SMART_CONTRACT = "smart_contract"
    ESCROW = "escrow"


class WalletStatusEnum(enum.Enum):
    """Wallet status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    FROZEN = "frozen"


class ContractTypeEnum(enum.Enum):
    """Smart contract type enumeration."""
    ESCROW = "escrow"
    MULTISIG = "multisig"
    BATCH_PROCESSOR = "batch_processor"
    PAYMENT_SPLITTER = "payment_splitter"


class ContractStatusEnum(enum.Enum):
    """Smart contract status enumeration."""
    DEPLOYED = "deployed"
    ACTIVE = "active"
    PAUSED = "paused"
    TERMINATED = "terminated"


class NetworkEnum(enum.Enum):
    """Blockchain network enumeration."""
    MAINNET = "mainnet"
    TESTNET = "testnet"
    BETANET = "betanet"
    LOCALNET = "localnet"


# ============================================================================
# Wallet Management Models
# ============================================================================

class Wallet(Base, TimestampMixin):
    """Simplified wallet model focused on blockchain operations."""
    
    __tablename__ = "wallets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Wallet identification
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    wallet_type = Column(Enum(WalletTypeEnum), default=WalletTypeEnum.STANDARD, nullable=False)
    status = Column(Enum(WalletStatusEnum), default=WalletStatusEnum.ACTIVE, nullable=False)
    
    # Algorand-specific fields
    algorand_address = Column(String(58), unique=True, nullable=False, index=True)
    encrypted_private_key = Column(Text, nullable=True)  # Encrypted with app key
    public_key = Column(String(64), nullable=False)
    
    # Multi-signature configuration
    multisig_threshold = Column(Integer, nullable=True)
    multisig_addresses = Column(JSON, nullable=True)  # Use JSON instead of ARRAY for SQLite compatibility
    
    # Network and configuration
    network = Column(Enum(NetworkEnum), default=NetworkEnum.TESTNET, nullable=False)
    wallet_metadata = Column(JSON, default={}, nullable=False)
    
    # Relationships
    transactions = relationship("Transaction", back_populates="wallet")
    contracts = relationship("SmartContract", back_populates="wallet")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("length(algorand_address) = 58", name="wallets_address_check"),
        CheckConstraint("multisig_threshold IS NULL OR multisig_threshold > 0", name="wallets_threshold_check"),
        Index('idx_wallets_address', 'algorand_address'),
        Index('idx_wallets_type_status', 'wallet_type', 'status'),
    )


# ============================================================================
# Transaction Models
# ============================================================================

class Transaction(Base, TimestampMixin):
    """Simplified transaction model for blockchain operations."""
    
    __tablename__ = "transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey('wallets.id', ondelete='CASCADE'), nullable=False)
    
    # Transaction identification
    transaction_type = Column(Enum(TransactionTypeEnum), nullable=False)
    status = Column(Enum(TransactionStatusEnum), default=TransactionStatusEnum.PENDING, nullable=False)
    
    # Algorand transaction details
    algorand_tx_id = Column(String(52), unique=True, nullable=True, index=True)
    algorand_tx_hash = Column(String(64), nullable=True)
    block_number = Column(BigInteger, nullable=True)
    round_number = Column(BigInteger, nullable=True)
    
    # Transaction amounts and fees
    amount = Column(Numeric(20, 6), nullable=False)
    fee = Column(Numeric(20, 6), default=0, nullable=False)
    asset_id = Column(BigInteger, nullable=True)  # Algorand Asset ID (0 for ALGO)
    
    # Addresses
    from_address = Column(String(58), nullable=False)
    to_address = Column(String(58), nullable=False)
    
    # Transaction data
    note = Column(Text, nullable=True)
    application_args = Column(JSON, nullable=True)  # For smart contract calls
    
    # Network and confirmation
    network = Column(Enum(NetworkEnum), default=NetworkEnum.TESTNET, nullable=False)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    confirmation_count = Column(Integer, default=0, nullable=False)
    
    # Metadata
    transaction_metadata = Column(JSON, default={}, nullable=False)
    
    # Relationships
    wallet = relationship("Wallet", back_populates="transactions")
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint("amount >= 0", name="transactions_amount_check"),
        CheckConstraint("fee >= 0", name="transactions_fee_check"),
        CheckConstraint("length(from_address) = 58", name="transactions_from_address_check"),
        CheckConstraint("length(to_address) = 58", name="transactions_to_address_check"),
        Index('idx_transactions_wallet_id', 'wallet_id'),
        Index('idx_transactions_algorand_tx_id', 'algorand_tx_id'),
        Index('idx_transactions_status', 'status'),
        Index('idx_transactions_type', 'transaction_type'),
        Index('idx_transactions_addresses', 'from_address', 'to_address'),
    )


# ============================================================================
# Smart Contract Models
# ============================================================================

class SmartContract(Base, TimestampMixin):
    """Smart contract model for Algorand applications."""
    
    __tablename__ = "smart_contracts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey('wallets.id', ondelete='CASCADE'), nullable=False)
    
    # Contract identification
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    contract_type = Column(Enum(ContractTypeEnum), nullable=False)
    status = Column(Enum(ContractStatusEnum), default=ContractStatusEnum.DEPLOYED, nullable=False)
    
    # Algorand application details
    app_id = Column(BigInteger, unique=True, nullable=True, index=True)
    app_address = Column(String(58), nullable=True)
    creator_address = Column(String(58), nullable=False)
    
    # Contract code and state
    approval_program = Column(Text, nullable=True)  # TEAL code
    clear_program = Column(Text, nullable=True)     # TEAL code
    global_state_schema = Column(JSON, nullable=True)
    local_state_schema = Column(JSON, nullable=True)
    
    # Contract configuration
    global_state = Column(JSON, default={}, nullable=False)
    local_state = Column(JSON, default={}, nullable=False)
    
    # Network and deployment
    network = Column(Enum(NetworkEnum), default=NetworkEnum.TESTNET, nullable=False)
    deployed_at = Column(DateTime(timezone=True), nullable=True)
    deployment_tx_id = Column(String(52), nullable=True)
    
    # Metadata
    transaction_metadata = Column(JSON, default={}, nullable=False)
    
    # Relationships
    wallet = relationship("Wallet", back_populates="contracts")
    executions = relationship("ContractExecution", back_populates="contract")
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint("length(creator_address) = 58", name="contracts_creator_address_check"),
        CheckConstraint("app_address IS NULL OR length(app_address) = 58", name="contracts_app_address_check"),
        Index('idx_smart_contracts_app_id', 'app_id'),
        Index('idx_smart_contracts_type_status', 'contract_type', 'status'),
        Index('idx_smart_contracts_creator', 'creator_address'),
    )


class ContractExecution(Base, TimestampMixin):
    """Smart contract execution tracking."""
    
    __tablename__ = "contract_executions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    contract_id = Column(UUID(as_uuid=True), ForeignKey('smart_contracts.id', ondelete='CASCADE'), nullable=False)
    
    # Execution details
    transaction_id = Column(String(52), nullable=False, index=True)
    method_name = Column(String(100), nullable=False)
    arguments = Column(JSON, default=[], nullable=False)
    
    # Execution results
    success = Column(Boolean, nullable=False)
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Gas and fees
    gas_used = Column(BigInteger, nullable=True)
    execution_fee = Column(Numeric(20, 6), nullable=True)
    
    # Network and confirmation
    network = Column(Enum(NetworkEnum), default=NetworkEnum.TESTNET, nullable=False)
    block_number = Column(BigInteger, nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    transaction_metadata = Column(JSON, default={}, nullable=False)
    
    # Relationships
    contract = relationship("SmartContract", back_populates="executions")
    
    # Constraints and indexes
    __table_args__ = (
        Index('idx_contract_executions_contract_id', 'contract_id'),
        Index('idx_contract_executions_tx_id', 'transaction_id'),
        Index('idx_contract_executions_method', 'method_name'),
        Index('idx_contract_executions_success', 'success'),
    )


# ============================================================================
# Asset Management Models
# ============================================================================

class AlgorandAsset(Base, TimestampMixin):
    """Algorand Standard Asset (ASA) model."""
    
    __tablename__ = "algorand_assets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Asset identification
    asset_id = Column(BigInteger, unique=True, nullable=False, index=True)
    asset_name = Column(String(32), nullable=False)
    unit_name = Column(String(8), nullable=False)
    
    # Asset details
    total_supply = Column(Numeric(20, 6), nullable=False)
    decimals = Column(Integer, default=0, nullable=False)
    default_frozen = Column(Boolean, default=False, nullable=False)
    
    # Asset URLs and metadata
    url = Column(String(96), nullable=True)
    metadata_hash = Column(String(64), nullable=True)
    
    # Asset addresses
    manager_address = Column(String(58), nullable=True)
    reserve_address = Column(String(58), nullable=True)
    freeze_address = Column(String(58), nullable=True)
    clawback_address = Column(String(58), nullable=True)
    creator_address = Column(String(58), nullable=False)
    
    # Network and status
    network = Column(Enum(NetworkEnum), default=NetworkEnum.TESTNET, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    transaction_metadata = Column(JSON, default={}, nullable=False)
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint("total_supply > 0", name="assets_total_supply_check"),
        CheckConstraint("decimals >= 0 AND decimals <= 19", name="assets_decimals_check"),
        CheckConstraint("length(creator_address) = 58", name="assets_creator_address_check"),
        Index('idx_algorand_assets_asset_id', 'asset_id'),
        Index('idx_algorand_assets_name', 'asset_name'),
        Index('idx_algorand_assets_creator', 'creator_address'),
    )


class WalletAsset(Base, TimestampMixin):
    """Wallet asset balance tracking."""
    
    __tablename__ = "wallet_assets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey('wallets.id', ondelete='CASCADE'), nullable=False)
    asset_id = Column(BigInteger, nullable=False)  # 0 for ALGO
    
    # Balance information
    balance = Column(Numeric(20, 6), default=0, nullable=False)
    frozen = Column(Boolean, default=False, nullable=False)
    
    # Opt-in information
    opted_in = Column(Boolean, default=False, nullable=False)
    opted_in_at = Column(DateTime(timezone=True), nullable=True)
    opt_in_tx_id = Column(String(52), nullable=True)
    
    # Network
    network = Column(Enum(NetworkEnum), default=NetworkEnum.TESTNET, nullable=False)
    
    # Metadata
    transaction_metadata = Column(JSON, default={}, nullable=False)
    
    # Relationships
    wallet = relationship("Wallet")
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint("balance >= 0", name="wallet_assets_balance_check"),
        CheckConstraint("asset_id >= 0", name="wallet_assets_asset_id_check"),
        UniqueConstraint('wallet_id', 'asset_id', name='wallet_assets_unique'),
        Index('idx_wallet_assets_wallet_id', 'wallet_id'),
        Index('idx_wallet_assets_asset_id', 'asset_id'),
        Index('idx_wallet_assets_balance', 'balance'),
    )


# ============================================================================
# Network and Configuration Models
# ============================================================================

class NetworkConfiguration(Base, TimestampMixin):
    """Network configuration for different Algorand networks."""
    
    __tablename__ = "network_configurations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Network identification
    network = Column(Enum(NetworkEnum), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Network endpoints
    algod_url = Column(String(255), nullable=False)
    algod_token = Column(String(255), nullable=True)
    indexer_url = Column(String(255), nullable=True)
    indexer_token = Column(String(255), nullable=True)
    
    # Network parameters
    genesis_id = Column(String(100), nullable=True)
    genesis_hash = Column(String(64), nullable=True)
    
    # Configuration
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    
    # Metadata
    transaction_metadata = Column(JSON, default={}, nullable=False)
    
    # Constraints and indexes
    __table_args__ = (
        Index('idx_network_configurations_network', 'network'),
        Index('idx_network_configurations_active', 'is_active'),
    )


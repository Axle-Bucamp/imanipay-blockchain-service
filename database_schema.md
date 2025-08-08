# ImaniPay Database Schema Design

**Author:** Manus AI  
**Date:** January 2025  
**Version:** 1.0  

## Overview

This document provides comprehensive database schema design for the ImaniPay Blockchain Service. The schema is designed to support high-performance, scalable operations while maintaining data integrity, security, and compliance requirements. The design implements best practices for financial services applications including audit trails, data encryption, and regulatory compliance.

## Database Architecture Strategy

### Multi-Database Approach

The ImaniPay platform implements a multi-database architecture that optimizes different data types and access patterns for maximum performance and scalability.

#### Primary Transactional Database (PostgreSQL)
- **Purpose**: Core transactional data requiring ACID compliance
- **Data Types**: User accounts, transactions, wallets, compliance records
- **Features**: Strong consistency, complex queries, referential integrity
- **Scaling**: Read replicas, connection pooling, query optimization

#### Document Database (MongoDB)
- **Purpose**: Flexible schema data and configuration management
- **Data Types**: User preferences, API logs, configuration data
- **Features**: Flexible schema, horizontal scaling, fast reads
- **Scaling**: Sharding, replica sets, aggregation pipelines

#### Cache Layer (Redis)
- **Purpose**: High-performance caching and session management
- **Data Types**: Session data, rate limiting, real-time calculations
- **Features**: In-memory performance, pub/sub messaging, data structures
- **Scaling**: Clustering, persistence, failover

#### Analytics Database (ClickHouse)
- **Purpose**: High-performance analytics and reporting
- **Data Types**: Transaction analytics, user behavior, compliance reporting
- **Features**: Columnar storage, real-time analytics, compression
- **Scaling**: Distributed queries, materialized views, partitioning

## Core Schema Design

### User Management Schema

#### users Table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(50),
    password_hash VARCHAR(255) NOT NULL,
    salt VARCHAR(255) NOT NULL,
    status user_status_enum NOT NULL DEFAULT 'pending',
    kyc_status kyc_status_enum NOT NULL DEFAULT 'not_started',
    risk_score INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,
    email_verified BOOLEAN DEFAULT FALSE,
    phone_verified BOOLEAN DEFAULT FALSE,
    two_factor_enabled BOOLEAN DEFAULT FALSE,
    two_factor_secret VARCHAR(255),
    backup_codes TEXT[],
    preferred_language VARCHAR(10) DEFAULT 'en',
    timezone VARCHAR(50) DEFAULT 'UTC',
    metadata JSONB DEFAULT '{}',
    
    -- Audit fields
    created_by UUID,
    updated_by UUID,
    version INTEGER DEFAULT 1,
    
    -- Indexes
    CONSTRAINT users_email_check CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT users_phone_check CHECK (phone IS NULL OR phone ~* '^\+[1-9]\d{1,14}$')
);

-- Indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_kyc_status ON users(kyc_status);
CREATE INDEX idx_users_created_at ON users(created_at);
CREATE INDEX idx_users_last_login ON users(last_login_at);

-- Partial indexes for active users
CREATE INDEX idx_users_active ON users(id) WHERE status = 'active';
```

#### user_profiles Table
```sql
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    middle_name VARCHAR(100),
    date_of_birth DATE,
    gender gender_enum,
    nationality VARCHAR(3), -- ISO 3166-1 alpha-3
    country_of_residence VARCHAR(3), -- ISO 3166-1 alpha-3
    address_line_1 VARCHAR(255),
    address_line_2 VARCHAR(255),
    city VARCHAR(100),
    state_province VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(3), -- ISO 3166-1 alpha-3
    occupation VARCHAR(100),
    employer VARCHAR(255),
    annual_income DECIMAL(15,2),
    source_of_funds TEXT,
    purpose_of_account TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Audit fields
    created_by UUID,
    updated_by UUID,
    version INTEGER DEFAULT 1,
    
    CONSTRAINT user_profiles_user_id_unique UNIQUE(user_id)
);

CREATE INDEX idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX idx_user_profiles_country ON user_profiles(country);
CREATE INDEX idx_user_profiles_nationality ON user_profiles(nationality);
```

#### user_sessions Table
```sql
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    refresh_token VARCHAR(255) UNIQUE,
    device_id VARCHAR(255),
    device_type device_type_enum,
    device_name VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    location_country VARCHAR(3),
    location_city VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Security fields
    login_method login_method_enum,
    mfa_verified BOOLEAN DEFAULT FALSE,
    risk_score INTEGER DEFAULT 0,
    
    CONSTRAINT user_sessions_expires_check CHECK (expires_at > created_at)
);

CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX idx_user_sessions_active ON user_sessions(user_id, is_active) WHERE is_active = TRUE;
CREATE INDEX idx_user_sessions_expires ON user_sessions(expires_at);
```

### KYC and Compliance Schema

#### kyc_verifications Table
```sql
CREATE TABLE kyc_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    verification_level kyc_level_enum NOT NULL,
    status kyc_verification_status_enum NOT NULL DEFAULT 'pending',
    provider VARCHAR(100) NOT NULL,
    provider_reference VARCHAR(255),
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    approved_at TIMESTAMP WITH TIME ZONE,
    rejected_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    
    -- Verification data
    documents_submitted JSONB DEFAULT '[]',
    verification_data JSONB DEFAULT '{}',
    rejection_reasons TEXT[],
    reviewer_notes TEXT,
    
    -- Risk assessment
    risk_score INTEGER,
    risk_factors JSONB DEFAULT '{}',
    
    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    version INTEGER DEFAULT 1
);

CREATE INDEX idx_kyc_verifications_user_id ON kyc_verifications(user_id);
CREATE INDEX idx_kyc_verifications_status ON kyc_verifications(status);
CREATE INDEX idx_kyc_verifications_provider ON kyc_verifications(provider);
CREATE INDEX idx_kyc_verifications_submitted ON kyc_verifications(submitted_at);
```

#### aml_screenings Table
```sql
CREATE TABLE aml_screenings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    transaction_id UUID REFERENCES transactions(id) ON DELETE CASCADE,
    screening_type aml_screening_type_enum NOT NULL,
    status aml_screening_status_enum NOT NULL DEFAULT 'pending',
    provider VARCHAR(100) NOT NULL,
    provider_reference VARCHAR(255),
    
    -- Screening data
    screening_data JSONB NOT NULL DEFAULT '{}',
    matches JSONB DEFAULT '[]',
    risk_score INTEGER,
    risk_level risk_level_enum,
    
    -- Resolution
    resolution aml_resolution_enum,
    resolution_notes TEXT,
    resolved_by UUID,
    resolved_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT aml_screenings_entity_check CHECK (
        (user_id IS NOT NULL AND transaction_id IS NULL) OR
        (user_id IS NULL AND transaction_id IS NOT NULL)
    )
);

CREATE INDEX idx_aml_screenings_user_id ON aml_screenings(user_id);
CREATE INDEX idx_aml_screenings_transaction_id ON aml_screenings(transaction_id);
CREATE INDEX idx_aml_screenings_status ON aml_screenings(status);
CREATE INDEX idx_aml_screenings_risk_level ON aml_screenings(risk_level);
```

### Wallet Management Schema

#### wallets Table
```sql
CREATE TABLE wallets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    address VARCHAR(58) UNIQUE NOT NULL, -- Algorand address
    wallet_type wallet_type_enum NOT NULL DEFAULT 'standard',
    status wallet_status_enum NOT NULL DEFAULT 'active',
    
    -- Security configuration
    is_multisig BOOLEAN DEFAULT FALSE,
    multisig_threshold INTEGER,
    multisig_addresses TEXT[],
    
    -- Key management
    encrypted_private_key TEXT, -- Encrypted with user's key
    key_derivation_path VARCHAR(255),
    public_key VARCHAR(64),
    
    -- Wallet metadata
    name VARCHAR(100),
    description TEXT,
    tags TEXT[],
    
    -- Balance tracking (cached for performance)
    algo_balance BIGINT DEFAULT 0, -- In microAlgos
    last_balance_update TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE,
    
    -- Audit fields
    created_by UUID,
    updated_by UUID,
    version INTEGER DEFAULT 1,
    
    CONSTRAINT wallets_address_check CHECK (length(address) = 58),
    CONSTRAINT wallets_multisig_check CHECK (
        (is_multisig = FALSE) OR 
        (is_multisig = TRUE AND multisig_threshold > 0 AND array_length(multisig_addresses, 1) >= multisig_threshold)
    )
);

CREATE INDEX idx_wallets_user_id ON wallets(user_id);
CREATE INDEX idx_wallets_address ON wallets(address);
CREATE INDEX idx_wallets_status ON wallets(status);
CREATE INDEX idx_wallets_type ON wallets(wallet_type);
CREATE INDEX idx_wallets_last_used ON wallets(last_used_at);
```

#### wallet_assets Table
```sql
CREATE TABLE wallet_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id UUID NOT NULL REFERENCES wallets(id) ON DELETE CASCADE,
    asset_id BIGINT NOT NULL, -- Algorand Asset ID (0 for ALGO)
    asset_name VARCHAR(32),
    asset_unit_name VARCHAR(8),
    asset_decimals INTEGER DEFAULT 6,
    
    -- Balance information
    balance BIGINT DEFAULT 0, -- In smallest unit
    frozen BOOLEAN DEFAULT FALSE,
    opted_in BOOLEAN DEFAULT TRUE,
    
    -- Asset metadata
    asset_url VARCHAR(255),
    asset_metadata_hash VARCHAR(64),
    manager_address VARCHAR(58),
    reserve_address VARCHAR(58),
    freeze_address VARCHAR(58),
    clawback_address VARCHAR(58),
    
    -- Tracking
    first_opted_in_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_transaction_at TIMESTAMP WITH TIME ZONE,
    last_balance_update TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT wallet_assets_unique UNIQUE(wallet_id, asset_id),
    CONSTRAINT wallet_assets_balance_check CHECK (balance >= 0)
);

CREATE INDEX idx_wallet_assets_wallet_id ON wallet_assets(wallet_id);
CREATE INDEX idx_wallet_assets_asset_id ON wallet_assets(asset_id);
CREATE INDEX idx_wallet_assets_balance ON wallet_assets(wallet_id, balance) WHERE balance > 0;
```

### Transaction Management Schema

#### transactions Table
```sql
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    transaction_type transaction_type_enum NOT NULL,
    status transaction_status_enum NOT NULL DEFAULT 'pending',
    
    -- Amount and currency information
    amount DECIMAL(20,8) NOT NULL,
    currency VARCHAR(10) NOT NULL,
    fee_amount DECIMAL(20,8) DEFAULT 0,
    fee_currency VARCHAR(10),
    
    -- Exchange rate information (for conversions)
    exchange_rate DECIMAL(20,8),
    exchange_rate_source VARCHAR(100),
    exchange_rate_timestamp TIMESTAMP WITH TIME ZONE,
    
    -- Source and destination
    source_wallet_id UUID REFERENCES wallets(id),
    destination_wallet_id UUID REFERENCES wallets(id),
    source_external_id VARCHAR(255), -- External system reference
    destination_external_id VARCHAR(255), -- External system reference
    
    -- Blockchain information
    blockchain_network VARCHAR(50),
    blockchain_transaction_id VARCHAR(255),
    block_number BIGINT,
    block_timestamp TIMESTAMP WITH TIME ZONE,
    gas_used BIGINT,
    gas_price BIGINT,
    
    -- Payment processor information
    payment_processor VARCHAR(100),
    processor_transaction_id VARCHAR(255),
    processor_reference VARCHAR(255),
    processor_status VARCHAR(50),
    
    -- Risk and compliance
    risk_score INTEGER DEFAULT 0,
    compliance_status compliance_status_enum DEFAULT 'pending',
    aml_screening_required BOOLEAN DEFAULT TRUE,
    
    -- Metadata
    description TEXT,
    reference VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    initiated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    confirmed_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE,
    
    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    version INTEGER DEFAULT 1,
    
    CONSTRAINT transactions_amount_check CHECK (amount > 0),
    CONSTRAINT transactions_fee_check CHECK (fee_amount >= 0),
    CONSTRAINT transactions_wallet_check CHECK (
        source_wallet_id IS NOT NULL OR source_external_id IS NOT NULL
    )
);

-- Primary indexes
CREATE INDEX idx_transactions_user_id ON transactions(user_id);
CREATE INDEX idx_transactions_status ON transactions(status);
CREATE INDEX idx_transactions_type ON transactions(transaction_type);
CREATE INDEX idx_transactions_created_at ON transactions(created_at);
CREATE INDEX idx_transactions_blockchain_tx ON transactions(blockchain_transaction_id);
CREATE INDEX idx_transactions_processor_tx ON transactions(processor_transaction_id);

-- Composite indexes for common queries
CREATE INDEX idx_transactions_user_status ON transactions(user_id, status);
CREATE INDEX idx_transactions_user_type ON transactions(user_id, transaction_type);
CREATE INDEX idx_transactions_status_created ON transactions(status, created_at);
```

#### transaction_steps Table
```sql
CREATE TABLE transaction_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    step_type transaction_step_type_enum NOT NULL,
    status transaction_step_status_enum NOT NULL DEFAULT 'pending',
    
    -- Step details
    description TEXT,
    processor VARCHAR(100),
    external_reference VARCHAR(255),
    
    -- Amount information
    amount DECIMAL(20,8),
    currency VARCHAR(10),
    fee_amount DECIMAL(20,8) DEFAULT 0,
    
    -- Execution details
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    -- Error information
    error_code VARCHAR(100),
    error_message TEXT,
    error_details JSONB,
    
    -- Metadata
    step_data JSONB DEFAULT '{}',
    
    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT transaction_steps_unique UNIQUE(transaction_id, step_number),
    CONSTRAINT transaction_steps_retry_check CHECK (retry_count <= max_retries)
);

CREATE INDEX idx_transaction_steps_transaction_id ON transaction_steps(transaction_id);
CREATE INDEX idx_transaction_steps_status ON transaction_steps(status);
CREATE INDEX idx_transaction_steps_type ON transaction_steps(step_type);
```

### Payment Processing Schema

#### payment_methods Table
```sql
CREATE TABLE payment_methods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    method_type payment_method_type_enum NOT NULL,
    status payment_method_status_enum NOT NULL DEFAULT 'active',
    
    -- Method details
    name VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- Bank account details (encrypted)
    encrypted_account_number TEXT,
    encrypted_routing_number TEXT,
    bank_name VARCHAR(255),
    bank_country VARCHAR(3),
    account_type bank_account_type_enum,
    
    -- Card details (encrypted, PCI compliant)
    encrypted_card_number TEXT,
    card_last_four VARCHAR(4),
    card_brand VARCHAR(50),
    card_type card_type_enum,
    expiry_month INTEGER,
    expiry_year INTEGER,
    
    -- Mobile money details
    mobile_provider VARCHAR(100),
    mobile_number VARCHAR(50),
    mobile_country VARCHAR(3),
    
    -- Verification status
    is_verified BOOLEAN DEFAULT FALSE,
    verification_method VARCHAR(100),
    verified_at TIMESTAMP WITH TIME ZONE,
    
    -- Usage tracking
    last_used_at TIMESTAMP WITH TIME ZONE,
    usage_count INTEGER DEFAULT 0,
    
    -- Limits
    daily_limit DECIMAL(15,2),
    monthly_limit DECIMAL(15,2),
    
    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    version INTEGER DEFAULT 1,
    
    CONSTRAINT payment_methods_card_check CHECK (
        method_type != 'card' OR (
            encrypted_card_number IS NOT NULL AND
            card_last_four IS NOT NULL AND
            expiry_month BETWEEN 1 AND 12 AND
            expiry_year >= EXTRACT(YEAR FROM NOW())
        )
    )
);

CREATE INDEX idx_payment_methods_user_id ON payment_methods(user_id);
CREATE INDEX idx_payment_methods_type ON payment_methods(method_type);
CREATE INDEX idx_payment_methods_status ON payment_methods(status);
CREATE INDEX idx_payment_methods_verified ON payment_methods(user_id, is_verified) WHERE is_verified = TRUE;
```

#### exchange_rates Table
```sql
CREATE TABLE exchange_rates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    base_currency VARCHAR(10) NOT NULL,
    quote_currency VARCHAR(10) NOT NULL,
    rate DECIMAL(20,8) NOT NULL,
    source VARCHAR(100) NOT NULL,
    
    -- Rate metadata
    bid_rate DECIMAL(20,8),
    ask_rate DECIMAL(20,8),
    spread DECIMAL(10,6),
    volume_24h DECIMAL(20,2),
    
    -- Validity
    valid_from TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT exchange_rates_rate_check CHECK (rate > 0),
    CONSTRAINT exchange_rates_validity_check CHECK (valid_until IS NULL OR valid_until > valid_from)
);

CREATE INDEX idx_exchange_rates_pair ON exchange_rates(base_currency, quote_currency);
CREATE INDEX idx_exchange_rates_active ON exchange_rates(base_currency, quote_currency, is_active) WHERE is_active = TRUE;
CREATE INDEX idx_exchange_rates_valid_from ON exchange_rates(valid_from);
CREATE INDEX idx_exchange_rates_source ON exchange_rates(source);
```

### Audit and Compliance Schema

#### audit_logs Table
```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    session_id UUID REFERENCES user_sessions(id),
    
    -- Action details
    action audit_action_enum NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id UUID,
    
    -- Request details
    ip_address INET,
    user_agent TEXT,
    request_method VARCHAR(10),
    request_path VARCHAR(500),
    request_body JSONB,
    
    -- Response details
    response_status INTEGER,
    response_body JSONB,
    
    -- Change tracking
    old_values JSONB,
    new_values JSONB,
    
    -- Risk and compliance
    risk_score INTEGER,
    compliance_flags TEXT[],
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Timestamp (immutable)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    -- Partitioning key
    partition_date DATE GENERATED ALWAYS AS (created_at::DATE) STORED
);

-- Partitioned by date for performance
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id, created_at);
CREATE INDEX idx_audit_logs_action ON audit_logs(action, created_at);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_ip ON audit_logs(ip_address, created_at);
```

#### compliance_reports Table
```sql
CREATE TABLE compliance_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_type compliance_report_type_enum NOT NULL,
    jurisdiction VARCHAR(3) NOT NULL, -- ISO 3166-1 alpha-3
    reporting_period_start DATE NOT NULL,
    reporting_period_end DATE NOT NULL,
    
    -- Report status
    status compliance_report_status_enum NOT NULL DEFAULT 'draft',
    generated_at TIMESTAMP WITH TIME ZONE,
    submitted_at TIMESTAMP WITH TIME ZONE,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    
    -- Report data
    report_data JSONB NOT NULL DEFAULT '{}',
    file_path VARCHAR(500),
    file_hash VARCHAR(64),
    
    -- Submission details
    submission_reference VARCHAR(255),
    submission_method VARCHAR(100),
    
    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID NOT NULL,
    updated_by UUID,
    version INTEGER DEFAULT 1,
    
    CONSTRAINT compliance_reports_period_check CHECK (reporting_period_end >= reporting_period_start)
);

CREATE INDEX idx_compliance_reports_type ON compliance_reports(report_type);
CREATE INDEX idx_compliance_reports_jurisdiction ON compliance_reports(jurisdiction);
CREATE INDEX idx_compliance_reports_period ON compliance_reports(reporting_period_start, reporting_period_end);
CREATE INDEX idx_compliance_reports_status ON compliance_reports(status);
```

## Enumeration Types

### User and Authentication Enums
```sql
CREATE TYPE user_status_enum AS ENUM (
    'pending', 'active', 'suspended', 'closed', 'banned'
);

CREATE TYPE kyc_status_enum AS ENUM (
    'not_started', 'in_progress', 'pending_review', 'approved', 'rejected', 'expired'
);

CREATE TYPE kyc_level_enum AS ENUM (
    'basic', 'standard', 'enhanced', 'institutional'
);

CREATE TYPE gender_enum AS ENUM (
    'male', 'female', 'other', 'prefer_not_to_say'
);

CREATE TYPE device_type_enum AS ENUM (
    'web', 'mobile_ios', 'mobile_android', 'api', 'other'
);

CREATE TYPE login_method_enum AS ENUM (
    'password', 'sso', 'biometric', 'hardware_key', 'magic_link'
);
```

### Transaction and Payment Enums
```sql
CREATE TYPE transaction_type_enum AS ENUM (
    'fiat_to_crypto', 'crypto_to_fiat', 'crypto_to_crypto', 
    'cross_border_payment', 'wallet_transfer', 'fee_payment'
);

CREATE TYPE transaction_status_enum AS ENUM (
    'pending', 'processing', 'confirmed', 'completed', 'failed', 'cancelled', 'refunded'
);

CREATE TYPE transaction_step_type_enum AS ENUM (
    'fiat_collection', 'crypto_conversion', 'blockchain_transfer', 
    'fiat_delivery', 'compliance_check', 'risk_assessment'
);

CREATE TYPE transaction_step_status_enum AS ENUM (
    'pending', 'processing', 'completed', 'failed', 'skipped'
);

CREATE TYPE payment_method_type_enum AS ENUM (
    'bank_account', 'card', 'mobile_money', 'cash_pickup', 'crypto_wallet'
);

CREATE TYPE payment_method_status_enum AS ENUM (
    'active', 'inactive', 'expired', 'blocked'
);

CREATE TYPE bank_account_type_enum AS ENUM (
    'checking', 'savings', 'business', 'other'
);

CREATE TYPE card_type_enum AS ENUM (
    'debit', 'credit', 'prepaid'
);
```

### Wallet and Asset Enums
```sql
CREATE TYPE wallet_type_enum AS ENUM (
    'standard', 'multisig', 'hardware', 'custodial', 'smart_contract'
);

CREATE TYPE wallet_status_enum AS ENUM (
    'active', 'inactive', 'frozen', 'closed'
);
```

### Compliance and Risk Enums
```sql
CREATE TYPE kyc_verification_status_enum AS ENUM (
    'pending', 'in_review', 'approved', 'rejected', 'expired'
);

CREATE TYPE aml_screening_type_enum AS ENUM (
    'user_onboarding', 'transaction_monitoring', 'periodic_review', 'enhanced_due_diligence'
);

CREATE TYPE aml_screening_status_enum AS ENUM (
    'pending', 'processing', 'completed', 'failed'
);

CREATE TYPE aml_resolution_enum AS ENUM (
    'cleared', 'false_positive', 'escalated', 'blocked'
);

CREATE TYPE risk_level_enum AS ENUM (
    'low', 'medium', 'high', 'critical'
);

CREATE TYPE compliance_status_enum AS ENUM (
    'pending', 'approved', 'rejected', 'requires_review'
);

CREATE TYPE compliance_report_type_enum AS ENUM (
    'suspicious_activity', 'large_transaction', 'cross_border', 'regulatory_filing'
);

CREATE TYPE compliance_report_status_enum AS ENUM (
    'draft', 'pending_review', 'approved', 'submitted', 'acknowledged'
);

CREATE TYPE audit_action_enum AS ENUM (
    'create', 'read', 'update', 'delete', 'login', 'logout', 
    'transaction_initiate', 'transaction_approve', 'transaction_reject',
    'kyc_submit', 'kyc_approve', 'kyc_reject',
    'wallet_create', 'wallet_backup', 'wallet_recover',
    'payment_method_add', 'payment_method_verify', 'payment_method_remove'
);
```

## Data Relationships and Constraints

### Primary Relationships

#### User-Centric Relationships
```sql
-- One user can have multiple wallets
ALTER TABLE wallets ADD CONSTRAINT fk_wallets_user 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- One user can have multiple payment methods
ALTER TABLE payment_methods ADD CONSTRAINT fk_payment_methods_user 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- One user can have multiple transactions
ALTER TABLE transactions ADD CONSTRAINT fk_transactions_user 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT;

-- One user has one profile
ALTER TABLE user_profiles ADD CONSTRAINT fk_user_profiles_user 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
```

#### Transaction Relationships
```sql
-- Transactions can reference source and destination wallets
ALTER TABLE transactions ADD CONSTRAINT fk_transactions_source_wallet 
    FOREIGN KEY (source_wallet_id) REFERENCES wallets(id) ON DELETE SET NULL;

ALTER TABLE transactions ADD CONSTRAINT fk_transactions_destination_wallet 
    FOREIGN KEY (destination_wallet_id) REFERENCES wallets(id) ON DELETE SET NULL;

-- Transaction steps belong to transactions
ALTER TABLE transaction_steps ADD CONSTRAINT fk_transaction_steps_transaction 
    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE;
```

#### Compliance Relationships
```sql
-- KYC verifications belong to users
ALTER TABLE kyc_verifications ADD CONSTRAINT fk_kyc_verifications_user 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- AML screenings can reference users or transactions
ALTER TABLE aml_screenings ADD CONSTRAINT fk_aml_screenings_user 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE aml_screenings ADD CONSTRAINT fk_aml_screenings_transaction 
    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE;
```

### Data Integrity Constraints

#### Business Logic Constraints
```sql
-- Ensure transaction amounts are positive
ALTER TABLE transactions ADD CONSTRAINT chk_transaction_amount_positive 
    CHECK (amount > 0);

-- Ensure wallet balances are non-negative
ALTER TABLE wallet_assets ADD CONSTRAINT chk_wallet_balance_non_negative 
    CHECK (balance >= 0);

-- Ensure exchange rates are positive
ALTER TABLE exchange_rates ADD CONSTRAINT chk_exchange_rate_positive 
    CHECK (rate > 0);

-- Ensure multisig configuration is valid
ALTER TABLE wallets ADD CONSTRAINT chk_multisig_configuration 
    CHECK (
        (is_multisig = FALSE) OR 
        (is_multisig = TRUE AND multisig_threshold > 0 AND 
         array_length(multisig_addresses, 1) >= multisig_threshold)
    );
```

#### Temporal Constraints
```sql
-- Ensure valid date ranges
ALTER TABLE compliance_reports ADD CONSTRAINT chk_reporting_period_valid 
    CHECK (reporting_period_end >= reporting_period_start);

-- Ensure session expiry is in the future
ALTER TABLE user_sessions ADD CONSTRAINT chk_session_expiry_future 
    CHECK (expires_at > created_at);

-- Ensure KYC verification expiry is after approval
ALTER TABLE kyc_verifications ADD CONSTRAINT chk_kyc_expiry_after_approval 
    CHECK (expires_at IS NULL OR approved_at IS NULL OR expires_at > approved_at);
```

## Performance Optimization

### Indexing Strategy

#### Composite Indexes for Common Query Patterns
```sql
-- User transaction history queries
CREATE INDEX idx_transactions_user_date_status 
    ON transactions(user_id, created_at DESC, status);

-- Wallet asset balance queries
CREATE INDEX idx_wallet_assets_wallet_balance 
    ON wallet_assets(wallet_id, asset_id) 
    WHERE balance > 0;

-- Compliance screening queries
CREATE INDEX idx_aml_screenings_status_created 
    ON aml_screenings(status, created_at) 
    WHERE status IN ('pending', 'processing');

-- Audit log queries by user and date
CREATE INDEX idx_audit_logs_user_date 
    ON audit_logs(user_id, created_at DESC);
```

#### Partial Indexes for Filtered Queries
```sql
-- Active user sessions
CREATE INDEX idx_user_sessions_active_user 
    ON user_sessions(user_id, last_activity_at DESC) 
    WHERE is_active = TRUE;

-- Pending transactions
CREATE INDEX idx_transactions_pending 
    ON transactions(created_at DESC) 
    WHERE status = 'pending';

-- Failed transaction steps for retry processing
CREATE INDEX idx_transaction_steps_failed 
    ON transaction_steps(transaction_id, step_number) 
    WHERE status = 'failed' AND retry_count < max_retries;
```

### Partitioning Strategy

#### Time-Based Partitioning for Large Tables
```sql
-- Partition audit_logs by month
CREATE TABLE audit_logs_y2025m01 PARTITION OF audit_logs 
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE audit_logs_y2025m02 PARTITION OF audit_logs 
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

-- Partition transactions by quarter for historical data
CREATE TABLE transactions_y2025q1 PARTITION OF transactions 
    FOR VALUES FROM ('2025-01-01') TO ('2025-04-01');
```

#### Hash Partitioning for User Data
```sql
-- Partition user_sessions by user_id hash for load distribution
CREATE TABLE user_sessions_p0 PARTITION OF user_sessions 
    FOR VALUES WITH (MODULUS 4, REMAINDER 0);

CREATE TABLE user_sessions_p1 PARTITION OF user_sessions 
    FOR VALUES WITH (MODULUS 4, REMAINDER 1);
```

## Security Considerations

### Data Encryption

#### Column-Level Encryption for Sensitive Data
```sql
-- Encrypt sensitive payment method data
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Function to encrypt sensitive data
CREATE OR REPLACE FUNCTION encrypt_sensitive_data(data TEXT, key TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN encode(pgp_sym_encrypt(data, key), 'base64');
END;
$$ LANGUAGE plpgsql;

-- Function to decrypt sensitive data
CREATE OR REPLACE FUNCTION decrypt_sensitive_data(encrypted_data TEXT, key TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN pgp_sym_decrypt(decode(encrypted_data, 'base64'), key);
END;
$$ LANGUAGE plpgsql;
```

#### Row-Level Security (RLS)
```sql
-- Enable RLS on sensitive tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE wallets ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;

-- Policy for users to access only their own data
CREATE POLICY user_data_policy ON users 
    FOR ALL TO application_role 
    USING (id = current_setting('app.current_user_id')::UUID);

CREATE POLICY user_profile_policy ON user_profiles 
    FOR ALL TO application_role 
    USING (user_id = current_setting('app.current_user_id')::UUID);

CREATE POLICY wallet_policy ON wallets 
    FOR ALL TO application_role 
    USING (user_id = current_setting('app.current_user_id')::UUID);

CREATE POLICY transaction_policy ON transactions 
    FOR ALL TO application_role 
    USING (user_id = current_setting('app.current_user_id')::UUID);
```

### Access Control

#### Database Roles and Permissions
```sql
-- Create application roles
CREATE ROLE app_read_only;
CREATE ROLE app_read_write;
CREATE ROLE app_admin;

-- Grant appropriate permissions
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_read_only;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO app_read_write;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_admin;

-- Restrict sensitive operations
REVOKE DELETE ON users FROM app_read_write;
REVOKE DELETE ON transactions FROM app_read_write;
REVOKE DELETE ON audit_logs FROM app_read_write;
```

## Backup and Recovery

### Backup Strategy

#### Automated Backup Configuration
```sql
-- Configure continuous archiving
ALTER SYSTEM SET wal_level = 'replica';
ALTER SYSTEM SET archive_mode = 'on';
ALTER SYSTEM SET archive_command = 'cp %p /backup/archive/%f';

-- Configure backup retention
ALTER SYSTEM SET wal_keep_segments = 100;
```

#### Point-in-Time Recovery Setup
```sql
-- Create base backup script
-- pg_basebackup -D /backup/base -Ft -z -P -U backup_user

-- Recovery configuration
-- restore_command = 'cp /backup/archive/%f %p'
-- recovery_target_time = '2025-01-15 14:30:00'
```

### Disaster Recovery

#### Cross-Region Replication
```sql
-- Configure streaming replication
ALTER SYSTEM SET max_wal_senders = 10;
ALTER SYSTEM SET wal_sender_timeout = 60000;

-- Create replication user
CREATE USER replication_user REPLICATION LOGIN ENCRYPTED PASSWORD 'secure_password';
```

## Monitoring and Maintenance

### Performance Monitoring

#### Query Performance Tracking
```sql
-- Enable query statistics
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Monitor slow queries
SELECT query, calls, total_time, mean_time, rows
FROM pg_stat_statements
WHERE mean_time > 1000
ORDER BY mean_time DESC
LIMIT 10;
```

#### Index Usage Analysis
```sql
-- Monitor index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY schemaname, tablename;
```

### Maintenance Procedures

#### Automated Maintenance Tasks
```sql
-- Create maintenance procedures
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM user_sessions 
    WHERE expires_at < NOW() - INTERVAL '7 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Schedule maintenance tasks
SELECT cron.schedule('cleanup-sessions', '0 2 * * *', 'SELECT cleanup_expired_sessions();');
```

#### Data Archival Strategy
```sql
-- Archive old audit logs
CREATE OR REPLACE FUNCTION archive_old_audit_logs()
RETURNS INTEGER AS $$
DECLARE
    archived_count INTEGER;
BEGIN
    -- Move logs older than 2 years to archive table
    INSERT INTO audit_logs_archive 
    SELECT * FROM audit_logs 
    WHERE created_at < NOW() - INTERVAL '2 years';
    
    GET DIAGNOSTICS archived_count = ROW_COUNT;
    
    DELETE FROM audit_logs 
    WHERE created_at < NOW() - INTERVAL '2 years';
    
    RETURN archived_count;
END;
$$ LANGUAGE plpgsql;
```

---

This comprehensive database schema design provides a robust foundation for the ImaniPay Blockchain Service, incorporating best practices for financial services applications including security, compliance, performance, and scalability. The schema is designed to support the complex requirements of cross-border payments while maintaining data integrity and regulatory compliance.


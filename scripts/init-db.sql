-- Auto-generated init-db.sql from SQLAlchemy models


CREATE TABLE algorand_assets (
	id VARCHAR(36) NOT NULL, 
	asset_id BIGINT NOT NULL, 
	asset_name VARCHAR(32) NOT NULL, 
	unit_name VARCHAR(8) NOT NULL, 
	total_supply NUMERIC(20, 6) NOT NULL, 
	decimals INTEGER NOT NULL, 
	default_frozen BOOLEAN NOT NULL, 
	url VARCHAR(96), 
	metadata_hash VARCHAR(64), 
	manager_address VARCHAR(58), 
	reserve_address VARCHAR(58), 
	freeze_address VARCHAR(58), 
	clawback_address VARCHAR(58), 
	creator_address VARCHAR(58) NOT NULL, 
	network VARCHAR NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	transaction_metadata JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT assets_total_supply_check CHECK (total_supply > 0), 
	CONSTRAINT assets_decimals_check CHECK (decimals >= 0 AND decimals <= 19), 
	CONSTRAINT assets_creator_address_check CHECK (length(creator_address) = 58)
)

;


CREATE TABLE exchange_rates (
	id VARCHAR(36) NOT NULL, 
	base_currency VARCHAR(10) NOT NULL, 
	quote_currency VARCHAR(10) NOT NULL, 
	rate NUMERIC(20, 8) NOT NULL, 
	source VARCHAR(100) NOT NULL, 
	bid_rate NUMERIC(20, 8), 
	ask_rate NUMERIC(20, 8), 
	spread NUMERIC(10, 6), 
	volume_24h NUMERIC(20, 2), 
	valid_from TIMESTAMP WITH TIME ZONE NOT NULL, 
	valid_until TIMESTAMP WITH TIME ZONE, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT exchange_rates_rate_check CHECK (rate > 0), 
	CONSTRAINT exchange_rates_validity_check CHECK (valid_until IS NULL OR valid_until > valid_from)
)

;


CREATE TABLE network_configurations (
	id VARCHAR(36) NOT NULL, 
	network VARCHAR NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	description TEXT, 
	algod_url VARCHAR(255) NOT NULL, 
	algod_token VARCHAR(255), 
	indexer_url VARCHAR(255), 
	indexer_token VARCHAR(255), 
	genesis_id VARCHAR(100), 
	genesis_hash VARCHAR(64), 
	is_active BOOLEAN NOT NULL, 
	is_default BOOLEAN NOT NULL, 
	transaction_metadata JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (network)
)

;


CREATE TABLE users (
	id VARCHAR(36) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	phone VARCHAR(50), 
	password_hash VARCHAR(255) NOT NULL, 
	salt VARCHAR(255) NOT NULL, 
	status VARCHAR NOT NULL, 
	kyc_status VARCHAR NOT NULL, 
	risk_score INTEGER NOT NULL, 
	last_login_at TIMESTAMP WITH TIME ZONE, 
	failed_login_attempts INTEGER NOT NULL, 
	locked_until TIMESTAMP WITH TIME ZONE, 
	email_verified BOOLEAN NOT NULL, 
	phone_verified BOOLEAN NOT NULL, 
	two_factor_enabled BOOLEAN NOT NULL, 
	two_factor_secret VARCHAR(255), 
	backup_codes VARCHAR[], 
	preferred_language VARCHAR(10) NOT NULL, 
	timezone VARCHAR(50) NOT NULL, 
	usr_metadata JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT users_email_check CHECK (email ~* '^[A-Za-z0-9._%%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'), 
	CONSTRAINT users_phone_check CHECK (phone IS NULL OR phone ~* '^\+[1-9]\d{1,14}$')
)

;


CREATE TABLE wallets (
	id VARCHAR(36) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	description TEXT, 
	wallet_type VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	algorand_address VARCHAR(58) NOT NULL, 
	encrypted_private_key TEXT, 
	public_key VARCHAR(64) NOT NULL, 
	multisig_threshold INTEGER, 
	multisig_addresses JSON, 
	network VARCHAR NOT NULL, 
	wallet_metadata JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT wallets_address_check CHECK (length(algorand_address) = 58), 
	CONSTRAINT wallets_threshold_check CHECK (multisig_threshold IS NULL OR multisig_threshold > 0)
)

;


CREATE TABLE kyc_verifications (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	verification_level VARCHAR(50) NOT NULL, 
	status VARCHAR NOT NULL, 
	provider VARCHAR(100) NOT NULL, 
	provider_reference VARCHAR(255), 
	submitted_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	reviewed_at TIMESTAMP WITH TIME ZONE, 
	approved_at TIMESTAMP WITH TIME ZONE, 
	rejected_at TIMESTAMP WITH TIME ZONE, 
	expires_at TIMESTAMP WITH TIME ZONE, 
	documents_submitted JSON NOT NULL, 
	verification_data JSON NOT NULL, 
	rejection_reasons VARCHAR[], 
	reviewer_notes TEXT, 
	risk_score INTEGER, 
	risk_factors JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)

;


CREATE TABLE payment_methods (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	method_type VARCHAR NOT NULL, 
	status VARCHAR(10), 
	name VARCHAR(100) NOT NULL, 
	description TEXT, 
	encrypted_account_number TEXT, 
	encrypted_routing_number TEXT, 
	bank_name VARCHAR(255), 
	bank_country VARCHAR(3), 
	account_type VARCHAR(50), 
	encrypted_card_number TEXT, 
	card_last_four VARCHAR(4), 
	card_brand VARCHAR(50), 
	card_type VARCHAR(50), 
	expiry_month INTEGER, 
	expiry_year INTEGER, 
	mobile_provider VARCHAR(100), 
	mobile_number VARCHAR(50), 
	mobile_country VARCHAR(3), 
	is_verified BOOLEAN NOT NULL, 
	verification_method VARCHAR(100), 
	verified_at TIMESTAMP WITH TIME ZONE, 
	last_used_at TIMESTAMP WITH TIME ZONE, 
	usage_count INTEGER NOT NULL, 
	daily_limit NUMERIC(15, 2), 
	monthly_limit NUMERIC(15, 2), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT payment_methods_card_check CHECK (method_type != 'card' OR (encrypted_card_number IS NOT NULL AND card_last_four IS NOT NULL AND expiry_month BETWEEN 1 AND 12 AND expiry_year >= EXTRACT(YEAR FROM NOW()))), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)

;


CREATE TABLE smart_contracts (
	id VARCHAR(36) NOT NULL, 
	wallet_id VARCHAR(36) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	description TEXT, 
	contract_type VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	app_id BIGINT, 
	app_address VARCHAR(58), 
	creator_address VARCHAR(58) NOT NULL, 
	approval_program TEXT, 
	clear_program TEXT, 
	global_state_schema JSON, 
	local_state_schema JSON, 
	global_state JSON NOT NULL, 
	local_state JSON NOT NULL, 
	network VARCHAR NOT NULL, 
	deployed_at TIMESTAMP WITH TIME ZONE, 
	deployment_tx_id VARCHAR(52), 
	transaction_metadata JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT contracts_creator_address_check CHECK (length(creator_address) = 58), 
	CONSTRAINT contracts_app_address_check CHECK (app_address IS NULL OR length(app_address) = 58), 
	FOREIGN KEY(wallet_id) REFERENCES wallets (id) ON DELETE CASCADE
)

;


CREATE TABLE transactions (
	id VARCHAR(36) NOT NULL, 
	wallet_id VARCHAR(36) NOT NULL, 
	transaction_type VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	algorand_tx_id VARCHAR(36), 
	algorand_tx_hash VARCHAR(64), 
	block_number BIGINT, 
	round_number BIGINT, 
	amount NUMERIC(20, 6) NOT NULL, 
	fee NUMERIC(20, 6) NOT NULL, 
	asset_id BIGINT, 
	from_address VARCHAR(58) NOT NULL, 
	to_address VARCHAR(58) NOT NULL, 
	note TEXT, 
	application_args JSON, 
	network VARCHAR NOT NULL, 
	confirmed_at TIMESTAMP WITH TIME ZONE, 
	confirmation_count INTEGER NOT NULL, 
	transaction_metadata JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT transactions_amount_check CHECK (amount >= 0), 
	CONSTRAINT transactions_fee_check CHECK (fee >= 0), 
	CONSTRAINT transactions_from_address_check CHECK (length(from_address) = 58), 
	CONSTRAINT transactions_to_address_check CHECK (length(to_address) = 58), 
	FOREIGN KEY(wallet_id) REFERENCES wallets (id) ON DELETE CASCADE
)

;


CREATE TABLE user_profiles (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	first_name VARCHAR(100), 
	last_name VARCHAR(100), 
	middle_name VARCHAR(100), 
	date_of_birth DATE, 
	gender VARCHAR, 
	nationality VARCHAR(3), 
	country_of_residence VARCHAR(3), 
	address_line_1 VARCHAR(255), 
	address_line_2 VARCHAR(255), 
	city VARCHAR(100), 
	state_province VARCHAR(100), 
	postal_code VARCHAR(20), 
	country VARCHAR(3), 
	occupation VARCHAR(100), 
	employer VARCHAR(255), 
	annual_income NUMERIC(15, 2), 
	source_of_funds TEXT, 
	purpose_of_account TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)

;


CREATE TABLE user_sessions (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	session_token VARCHAR(255) NOT NULL, 
	refresh_token VARCHAR(255), 
	device_id VARCHAR(36), 
	device_type VARCHAR, 
	device_name VARCHAR(255), 
	ip_address INET, 
	user_agent TEXT, 
	location_country VARCHAR(3), 
	location_city VARCHAR(100), 
	is_active BOOLEAN NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	last_activity_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	login_method VARCHAR, 
	mfa_verified BOOLEAN NOT NULL, 
	risk_score INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT user_sessions_expires_check CHECK (expires_at > created_at), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	UNIQUE (refresh_token)
)

;


CREATE TABLE wallet_assets (
	id VARCHAR(36) NOT NULL, 
	wallet_id VARCHAR(36) NOT NULL, 
	asset_id BIGINT NOT NULL, 
	balance NUMERIC(20, 6) NOT NULL, 
	frozen BOOLEAN NOT NULL, 
	opted_in BOOLEAN NOT NULL, 
	opted_in_at TIMESTAMP WITH TIME ZONE, 
	opt_in_tx_id VARCHAR(52), 
	network VARCHAR NOT NULL, 
	transaction_metadata JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT wallet_assets_balance_check CHECK (balance >= 0), 
	CONSTRAINT wallet_assets_asset_id_check CHECK (asset_id >= 0), 
	CONSTRAINT wallet_assets_unique UNIQUE (wallet_id, asset_id), 
	FOREIGN KEY(wallet_id) REFERENCES wallets (id) ON DELETE CASCADE
)

;


CREATE TABLE aml_screenings (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36), 
	transaction_id VARCHAR, 
	screening_type VARCHAR(50) NOT NULL, 
	status VARCHAR(50) NOT NULL, 
	provider VARCHAR(100) NOT NULL, 
	provider_reference VARCHAR(255), 
	screening_data JSON NOT NULL, 
	matches JSON NOT NULL, 
	risk_score INTEGER, 
	risk_level VARCHAR, 
	resolution VARCHAR(50), 
	resolution_notes TEXT, 
	resolved_by VARCHAR(36), 
	resolved_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT aml_screenings_entity_check CHECK ((user_id IS NOT NULL AND transaction_id IS NULL) OR (user_id IS NULL AND transaction_id IS NOT NULL)), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(transaction_id) REFERENCES transactions (id) ON DELETE CASCADE
)

;


CREATE TABLE contract_executions (
	id VARCHAR(36) NOT NULL, 
	contract_id VARCHAR(36) NOT NULL, 
	transaction_id VARCHAR(52) NOT NULL, 
	method_name VARCHAR(100) NOT NULL, 
	arguments JSON NOT NULL, 
	success BOOLEAN NOT NULL, 
	result JSON, 
	error_message TEXT, 
	gas_used BIGINT, 
	execution_fee NUMERIC(20, 6), 
	network VARCHAR NOT NULL, 
	block_number BIGINT, 
	confirmed_at TIMESTAMP WITH TIME ZONE, 
	transaction_metadata JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(contract_id) REFERENCES smart_contracts (id) ON DELETE CASCADE
)

;


CREATE TABLE transaction_steps (
	id VARCHAR(36) NOT NULL, 
	transaction_id VARCHAR(36) NOT NULL, 
	step_number INTEGER NOT NULL, 
	step_type VARCHAR(50) NOT NULL, 
	status VARCHAR(50) NOT NULL, 
	description TEXT, 
	processor VARCHAR(100), 
	external_reference VARCHAR(255), 
	amount NUMERIC(20, 8), 
	currency VARCHAR(10), 
	fee_amount NUMERIC(20, 8), 
	started_at TIMESTAMP WITH TIME ZONE, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	failed_at TIMESTAMP WITH TIME ZONE, 
	retry_count INTEGER NOT NULL, 
	max_retries INTEGER NOT NULL, 
	error_code VARCHAR(100), 
	error_message TEXT, 
	error_details JSON, 
	step_data JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT transaction_steps_unique UNIQUE (transaction_id, step_number), 
	CONSTRAINT transaction_steps_retry_check CHECK (retry_count <= max_retries), 
	FOREIGN KEY(transaction_id) REFERENCES transactions (id) ON DELETE CASCADE
)

;

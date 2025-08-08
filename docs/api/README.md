# ImaniPay Blockchain Service API Documentation

## Overview

The ImaniPay Blockchain Service API provides comprehensive endpoints for cross-border payment processing, wallet management, and blockchain interactions. This RESTful API is built with FastAPI and follows OpenAPI 3.0 specifications.

## Base URL

- **Development**: `http://localhost:8000`
- **Staging**: `https://api-staging.imanipay.com`
- **Production**: `https://api.imanipay.com`

## Authentication

The API uses OAuth2 with JWT Bearer tokens for authentication. All protected endpoints require a valid access token in the Authorization header.

### Authentication Flow

1. **Register or Login** to obtain access and refresh tokens
2. **Include Bearer token** in the Authorization header for protected endpoints
3. **Refresh tokens** when access tokens expire
4. **Logout** to invalidate tokens

```http
Authorization: Bearer <access_token>
```

## API Endpoints

### Authentication Endpoints

#### POST /auth/register
Register a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "phone": "+1234567890",
  "first_name": "John",
  "last_name": "Doe",
  "country_code": "US"
}
```

**Response:**
```json
{
  "message": "User registered successfully",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "requires_verification": true
}
```

#### POST /auth/login
Authenticate user and obtain access tokens.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "mfa_code": "123456"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "is_verified": true
  }
}
```

#### POST /auth/refresh
Refresh access token using refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### GET /auth/me
Get current user profile information.

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "phone": "+1234567890",
  "first_name": "John",
  "last_name": "Doe",
  "is_active": true,
  "email_verified": true,
  "phone_verified": true,
  "kyc_verified": false,
  "mfa_enabled": true,
  "created_at": "2024-01-01T00:00:00Z",
  "last_login": "2024-01-01T12:00:00Z"
}
```

### Wallet Management Endpoints

#### POST /wallets
Create a new wallet for the authenticated user.

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "name": "My Primary Wallet",
  "currency": "USDC",
  "wallet_type": "standard"
}
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "My Primary Wallet",
  "address": "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567890ABCDEFGHIJKLMNOP",
  "currency": "USDC",
  "wallet_type": "standard",
  "balance": "0.00",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### GET /wallets
List all wallets for the authenticated user.

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `skip` (integer): Number of records to skip (default: 0)
- `limit` (integer): Maximum number of records to return (default: 100)
- `currency` (string): Filter by currency
- `is_active` (boolean): Filter by active status

**Response:**
```json
{
  "wallets": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "name": "My Primary Wallet",
      "address": "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567890ABCDEFGHIJKLMNOP",
      "currency": "USDC",
      "wallet_type": "standard",
      "balance": "1000.50",
      "is_active": true,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 100
}
```

#### GET /wallets/{wallet_id}
Get detailed information about a specific wallet.

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Path Parameters:**
- `wallet_id` (UUID): Wallet identifier

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "My Primary Wallet",
  "address": "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567890ABCDEFGHIJKLMNOP",
  "currency": "USDC",
  "wallet_type": "standard",
  "balance": "1000.50",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "last_transaction": "2024-01-01T11:30:00Z",
  "transaction_count": 25
}
```

#### GET /wallets/{wallet_id}/balance
Get current balance for a specific wallet.

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Path Parameters:**
- `wallet_id` (UUID): Wallet identifier

**Response:**
```json
{
  "wallet_id": "123e4567-e89b-12d3-a456-426614174000",
  "currency": "USDC",
  "balance": "1000.50",
  "pending_balance": "50.00",
  "available_balance": "950.50",
  "last_updated": "2024-01-01T12:00:00Z"
}
```

### Payment Processing Endpoints

#### POST /payments/fiat-to-crypto
Convert fiat currency to cryptocurrency.

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "amount": 100.00,
  "from_currency": "USD",
  "to_currency": "USDC",
  "wallet_id": "123e4567-e89b-12d3-a456-426614174000",
  "payment_method": "bank_transfer",
  "processor": "circle"
}
```

**Response:**
```json
{
  "payment_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "pending",
  "amount": 100.00,
  "from_currency": "USD",
  "to_currency": "USDC",
  "exchange_rate": 1.0,
  "fees": {
    "processor_fee": 2.50,
    "network_fee": 0.10,
    "total_fee": 2.60
  },
  "estimated_completion": "2024-01-01T12:30:00Z",
  "created_at": "2024-01-01T12:00:00Z"
}
```

#### POST /payments/crypto-to-fiat
Convert cryptocurrency to fiat currency.

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "amount": 100.00,
  "from_currency": "USDC",
  "to_currency": "USD",
  "wallet_id": "123e4567-e89b-12d3-a456-426614174000",
  "bank_account_id": "123e4567-e89b-12d3-a456-426614174000",
  "processor": "circle"
}
```

**Response:**
```json
{
  "payment_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "pending",
  "amount": 100.00,
  "from_currency": "USDC",
  "to_currency": "USD",
  "exchange_rate": 0.99,
  "fees": {
    "processor_fee": 1.50,
    "network_fee": 0.05,
    "total_fee": 1.55
  },
  "estimated_completion": "2024-01-01T14:00:00Z",
  "created_at": "2024-01-01T12:00:00Z"
}
```

#### POST /payments/cross-border
Initiate a cross-border payment.

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "amount": 500.00,
  "from_currency": "USD",
  "to_currency": "NGN",
  "recipient": {
    "email": "recipient@example.com",
    "phone": "+2348012345678",
    "name": "Jane Doe",
    "bank_account": {
      "account_number": "1234567890",
      "bank_code": "044",
      "account_name": "Jane Doe"
    }
  },
  "purpose": "family_support",
  "reference": "Monthly allowance"
}
```

**Response:**
```json
{
  "payment_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "pending",
  "amount": 500.00,
  "from_currency": "USD",
  "to_currency": "NGN",
  "exchange_rate": 750.00,
  "total_amount": 375000.00,
  "fees": {
    "transfer_fee": 5.00,
    "exchange_fee": 2.50,
    "total_fee": 7.50
  },
  "estimated_completion": "2024-01-01T16:00:00Z",
  "tracking_reference": "IMP-2024-001234",
  "created_at": "2024-01-01T12:00:00Z"
}
```

#### GET /payments/{payment_id}
Get payment status and details.

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Path Parameters:**
- `payment_id` (UUID): Payment identifier

**Response:**
```json
{
  "payment_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "payment_type": "cross_border",
  "amount": 500.00,
  "from_currency": "USD",
  "to_currency": "NGN",
  "exchange_rate": 750.00,
  "total_amount": 375000.00,
  "fees": {
    "transfer_fee": 5.00,
    "exchange_fee": 2.50,
    "total_fee": 7.50
  },
  "tracking_reference": "IMP-2024-001234",
  "created_at": "2024-01-01T12:00:00Z",
  "completed_at": "2024-01-01T15:30:00Z",
  "steps": [
    {
      "step": "payment_initiated",
      "status": "completed",
      "timestamp": "2024-01-01T12:00:00Z"
    },
    {
      "step": "funds_converted",
      "status": "completed",
      "timestamp": "2024-01-01T12:15:00Z"
    },
    {
      "step": "transfer_sent",
      "status": "completed",
      "timestamp": "2024-01-01T15:30:00Z"
    }
  ]
}
```

### Transaction Management Endpoints

#### POST /transactions/send
Send a blockchain transaction.

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "from_wallet_id": "123e4567-e89b-12d3-a456-426614174000",
  "to_address": "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567890ABCDEFGHIJKLMNOP",
  "amount": 100.00,
  "currency": "USDC",
  "note": "Payment for services",
  "fee_level": "standard"
}
```

**Response:**
```json
{
  "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
  "blockchain_tx_id": "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",
  "status": "pending",
  "from_address": "SENDER_ADDRESS_HERE",
  "to_address": "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567890ABCDEFGHIJKLMNOP",
  "amount": 100.00,
  "currency": "USDC",
  "network_fee": 0.001,
  "created_at": "2024-01-01T12:00:00Z",
  "estimated_confirmation": "2024-01-01T12:05:00Z"
}
```

#### GET /transactions/{transaction_id}
Get transaction details and status.

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Path Parameters:**
- `transaction_id` (UUID): Transaction identifier

**Response:**
```json
{
  "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
  "blockchain_tx_id": "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",
  "status": "confirmed",
  "from_address": "SENDER_ADDRESS_HERE",
  "to_address": "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567890ABCDEFGHIJKLMNOP",
  "amount": 100.00,
  "currency": "USDC",
  "network_fee": 0.001,
  "confirmations": 12,
  "block_number": 12345678,
  "created_at": "2024-01-01T12:00:00Z",
  "confirmed_at": "2024-01-01T12:04:30Z"
}
```

#### GET /transactions/history
Get transaction history for the authenticated user.

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `skip` (integer): Number of records to skip (default: 0)
- `limit` (integer): Maximum number of records to return (default: 100)
- `wallet_id` (UUID): Filter by wallet
- `currency` (string): Filter by currency
- `status` (string): Filter by status
- `from_date` (datetime): Filter from date
- `to_date` (datetime): Filter to date

**Response:**
```json
{
  "transactions": [
    {
      "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
      "blockchain_tx_id": "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",
      "status": "confirmed",
      "type": "send",
      "amount": 100.00,
      "currency": "USDC",
      "created_at": "2024-01-01T12:00:00Z"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 100
}
```

## Error Handling

The API uses standard HTTP status codes and returns detailed error information in JSON format.

### Error Response Format

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "The request is invalid",
    "details": "Email address is required",
    "timestamp": "2024-01-01T12:00:00Z",
    "request_id": "123e4567-e89b-12d3-a456-426614174000"
  }
}
```

### Common Error Codes

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 400 | INVALID_REQUEST | Request validation failed |
| 401 | UNAUTHORIZED | Authentication required |
| 403 | FORBIDDEN | Insufficient permissions |
| 404 | NOT_FOUND | Resource not found |
| 409 | CONFLICT | Resource already exists |
| 422 | VALIDATION_ERROR | Input validation failed |
| 429 | RATE_LIMITED | Too many requests |
| 500 | INTERNAL_ERROR | Server error |

## Rate Limiting

The API implements rate limiting to ensure fair usage and system stability.

### Rate Limits

| Endpoint Category | Requests per Minute | Burst Limit |
|-------------------|---------------------|-------------|
| Authentication | 5 | 10 |
| Wallet Operations | 60 | 120 |
| Payment Processing | 10 | 20 |
| Transaction Queries | 100 | 200 |
| General API | 100 | 200 |

### Rate Limit Headers

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## Webhooks

The API supports webhooks for real-time notifications of payment and transaction events.

### Webhook Events

- `payment.created` - Payment initiated
- `payment.completed` - Payment completed successfully
- `payment.failed` - Payment failed
- `transaction.confirmed` - Transaction confirmed on blockchain
- `wallet.balance_updated` - Wallet balance changed

### Webhook Payload Example

```json
{
  "event": "payment.completed",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    "payment_id": "123e4567-e89b-12d3-a456-426614174000",
    "status": "completed",
    "amount": 100.00,
    "currency": "USD"
  }
}
```

## SDKs and Libraries

Official SDKs are available for popular programming languages:

- **Python**: `pip install imanipay-python`
- **JavaScript/Node.js**: `npm install imanipay-js`
- **PHP**: `composer require imanipay/php-sdk`
- **Java**: Available on Maven Central
- **Go**: `go get github.com/imanipay/go-sdk`

## Testing

### Sandbox Environment

Use the sandbox environment for testing:

- **Base URL**: `https://api-sandbox.imanipay.com`
- **Test API Keys**: Available in the developer dashboard
- **Test Data**: Pre-populated test accounts and wallets

### Postman Collection

Import our Postman collection for easy API testing:

```bash
curl -o imanipay-api.postman_collection.json \
  https://api.imanipay.com/docs/postman/collection.json
```

## Support

For API support and questions:

- **Documentation**: [https://docs.imanipay.com](https://docs.imanipay.com)
- **Developer Portal**: [https://developers.imanipay.com](https://developers.imanipay.com)
- **Support Email**: [api-support@imanipay.com](mailto:api-support@imanipay.com)
- **Status Page**: [https://status.imanipay.com](https://status.imanipay.com)


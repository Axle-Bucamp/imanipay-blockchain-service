# ImaniPay Blockchain Service 🌍

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Algorand](https://img.shields.io/badge/Algorand-Blockchain-blue.svg)](https://algorand.com/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

[![CI/CD Pipeline](https://github.com/imanipay-africa/imanipay-blockchain-service/workflows/CI%2FCD%20Pipeline/badge.svg)](https://github.com/imanipay-africa/imanipay-blockchain-service/actions)
[![Coverage](https://codecov.io/gh/imanipay-africa/imanipay-blockchain-service/branch/main/graph/badge.svg)](https://codecov.io/gh/imanipay-africa/imanipay-blockchain-service)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=imanipay-africa_imanipay-blockchain-service&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=imanipay-africa_imanipay-blockchain-service)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=imanipay-africa_imanipay-blockchain-service&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=imanipay-africa_imanipay-blockchain-service)

> **Enterprise-grade blockchain payment service enabling seamless cross-border transactions for African workers and businesses.**

## 🚀 Overview

ImaniPay Blockchain Service is a comprehensive Python-based API built with FastAPI, designed to revolutionize cross-border payments in Africa. By leveraging the Algorand blockchain and USDC stablecoin, the platform provides secure, efficient, and cost-effective payment solutions that bypass traditional banking limitations and excessive local taxes.

### 🎯 Mission

Empower African workers and businesses with accessible, transparent, and affordable cross-border payment solutions that preserve the value of their hard-earned money.

### ✨ Key Features

#### 💰 **Multi-Currency Payment Flows**
- **Fiat-to-USDC Conversion**: Seamlessly convert local African currencies (NGN, KES, GHS, ZAR) to USDC
- **USDC-to-Algorand Bridge**: Efficient blockchain transfers using Algorand's fast and low-cost network
- **Crypto-to-Fiat Off-ramps**: Convert digital assets back to local currencies with multiple provider options
- **Cross-Border Remittances**: Direct peer-to-peer transfers bypassing traditional banking intermediaries

#### 🔐 **Enterprise Security**
- **OAuth2 + JWT Authentication**: Industry-standard authentication with access and refresh tokens
- **Multi-Factor Authentication (MFA)**: TOTP-based 2FA with QR code setup and backup codes
- **API Key Management**: Scoped API keys with expiration and usage tracking
- **Advanced Rate Limiting**: IP-based and user-based rate limiting with threat detection
- **Security Middleware**: Comprehensive protection against common web vulnerabilities
- **Encryption at Rest**: AES-256-GCM encryption for sensitive data storage

#### 🏦 **Financial Compliance**
- **KYC/AML Integration**: Comprehensive identity verification and anti-money laundering checks
- **Risk Assessment**: 7-factor risk scoring algorithm for transaction monitoring
- **Regulatory Compliance**: GDPR, PCI DSS, and international financial regulation adherence
- **Audit Logging**: Complete transaction trails for compliance and forensic analysis
- **Transaction Limits**: Configurable limits based on verification levels

#### ⛓️ **Blockchain Integration**
- **Algorand SDK**: Full integration with Algorand blockchain for fast, secure transactions
- **Smart Contracts**: Advanced escrow, multi-signature, and batch transaction contracts
- **Asset Management**: Comprehensive wallet and asset tracking capabilities
- **Transaction Monitoring**: Real-time transaction status and confirmation tracking

#### 🔧 **Developer Experience**
- **FastAPI Framework**: Modern, fast web framework with automatic API documentation
- **Async/Await Support**: High-performance asynchronous request handling
- **OpenAPI Documentation**: Interactive API documentation with Swagger UI
- **Type Safety**: Full type hints and validation with Pydantic
- **Comprehensive Testing**: Unit, integration, and end-to-end test coverage
- **CI/CD Pipeline**: Automated testing, security scanning, and deployment

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [API Documentation](#-api-documentation)
- [Payment Flows](#-payment-flows)
- [Security Features](#-security-features)
- [Development](#-development)
- [Deployment](#-deployment)
- [Contributing](#-contributing)
- [License](#-license)

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- PostgreSQL 15+
- Redis 7+
- Docker (optional, for containerized deployment)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/imanipay-africa/imanipay-blockchain-service.git
   cd imanipay-blockchain-service
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize database**
   ```bash
   alembic upgrade head
   ```

6. **Start the development server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

7. **Access the API**
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root with the following configuration:

```bash
# Application Settings
ENVIRONMENT=development
DEBUG=true
APP_NAME=ImaniPay Blockchain Service
APP_VERSION=1.0.0

# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/imanipay_db
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_POOL_SIZE=20

# Security Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key-here
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
ENCRYPTION_KEY=your-32-character-encryption-key

# Algorand Configuration
ALGORAND_NODE_URL=https://testnet-api.algonode.cloud
ALGORAND_INDEXER_URL=https://testnet-idx.algonode.cloud
ALGORAND_NETWORK=testnet

# Payment Processor Configuration
CIRCLE_API_KEY=your-circle-api-key
YELLOWCARD_API_KEY=your-yellowcard-api-key
TRANSAK_API_KEY=your-transak-api-key
COINBASE_API_KEY=your-coinbase-api-key

# External Services
EXCHANGE_RATE_API_KEY=your-exchange-rate-api-key
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
SENDGRID_API_KEY=your-sendgrid-key

# Monitoring and Observability
PROMETHEUS_ENABLED=true
OPENTELEMETRY_ENABLED=true
LOG_LEVEL=INFO
```

### Database Setup

1. **Create PostgreSQL database**
   ```sql
   CREATE DATABASE imanipay_db;
   CREATE USER imanipay_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE imanipay_db TO imanipay_user;
   ```

2. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

3. **Create initial admin user (optional)**
   ```bash
   python scripts/create_admin_user.py
   ```

## 📚 API Documentation

### Interactive Documentation

The API provides comprehensive interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

### Core API Endpoints

#### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - User authentication
- `POST /auth/refresh` - Token refresh
- `POST /auth/logout` - User logout
- `GET /auth/me` - Get current user profile

#### Wallet Management
- `POST /wallets` - Create new wallet
- `GET /wallets` - List user wallets
- `GET /wallets/{wallet_id}` - Get wallet details
- `GET /wallets/{wallet_id}/balance` - Get wallet balance
- `POST /wallets/{wallet_id}/backup` - Backup wallet

#### Payment Processing
- `POST /payments/fiat-to-crypto` - Convert fiat to cryptocurrency
- `POST /payments/crypto-to-fiat` - Convert cryptocurrency to fiat
- `POST /payments/cross-border` - Cross-border payment
- `GET /payments/{payment_id}` - Get payment status
- `GET /payments/history` - Payment history

#### Transaction Management
- `POST /transactions/send` - Send transaction
- `GET /transactions/{tx_id}` - Get transaction details
- `GET /transactions/history` - Transaction history
- `POST /transactions/batch` - Batch transactions

### Authentication

The API uses OAuth2 with JWT tokens for authentication:

```bash
# Login to get access token
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "your_password"
  }'

# Use access token in subsequent requests
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 💳 Payment Flows

### Fiat-to-Crypto Flow

```mermaid
sequenceDiagram
    participant User
    participant API
    participant PaymentProcessor
    participant Algorand
    participant Database

    User->>API: POST /payments/fiat-to-crypto
    API->>Database: Validate user and limits
    API->>PaymentProcessor: Initiate fiat payment
    PaymentProcessor-->>API: Payment confirmation
    API->>Algorand: Create USDC transaction
    Algorand-->>API: Transaction confirmed
    API->>Database: Update payment status
    API-->>User: Payment completed
```

### Cross-Border Payment Flow

```mermaid
sequenceDiagram
    participant Sender
    participant API
    participant Algorand
    participant Recipient
    participant OffRamp

    Sender->>API: Initiate cross-border payment
    API->>Algorand: Create escrow contract
    Algorand-->>API: Escrow created
    API->>Algorand: Transfer to escrow
    Algorand-->>API: Transfer confirmed
    API->>Recipient: Notify payment received
    Recipient->>API: Confirm receipt
    API->>OffRamp: Convert to local currency
    OffRamp-->>Recipient: Fiat payment
    API->>Algorand: Release escrow
```

## 🔒 Security Features

### Multi-Layer Security Architecture

1. **Application Layer Security**
   - Input validation and sanitization
   - SQL injection prevention
   - XSS protection
   - CSRF protection
   - Rate limiting and DDoS protection

2. **Authentication & Authorization**
   - OAuth2 with PKCE
   - JWT tokens with rotation
   - Multi-factor authentication
   - Role-based access control
   - API key management

3. **Data Protection**
   - Encryption at rest (AES-256-GCM)
   - Encryption in transit (TLS 1.3)
   - Key derivation (PBKDF2)
   - Secure password hashing (bcrypt)

4. **Blockchain Security**
   - Private key encryption
   - Multi-signature wallets
   - Transaction signing
   - Smart contract auditing

### Security Headers

The API automatically includes comprehensive security headers:

```http
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self'
Referrer-Policy: strict-origin-when-cross-origin
```

## 🛠️ Development

### Development Setup

1. **Install development dependencies**
   ```bash
   pip install -r requirements-dev.txt
   ```

2. **Set up pre-commit hooks**
   ```bash
   pre-commit install
   ```

3. **Run tests**
   ```bash
   pytest
   ```

4. **Run with coverage**
   ```bash
   pytest --cov=app --cov-report=html
   ```

5. **Code formatting**
   ```bash
   black app/ tests/
   isort app/ tests/
   ```

6. **Linting**
   ```bash
   flake8 app/ tests/
   mypy app/
   ```

### Project Structure

```
imanipay-blockchain-service/
├── app/                          # Application source code
│   ├── api/                      # API route handlers
│   │   ├── auth.py              # Authentication endpoints
│   │   ├── wallets.py           # Wallet management endpoints
│   │   ├── payments.py          # Payment processing endpoints
│   │   └── transactions.py      # Transaction endpoints
│   ├── core/                     # Core application components
│   │   ├── config.py            # Configuration management
│   │   └── startup.py           # Application startup
│   ├── services/                 # Business logic services
│   │   ├── auth.py              # Authentication service
│   │   ├── payment_processor.py # Payment processing
│   │   ├── algorand_client.py   # Algorand integration
│   │   └── encryption.py        # Encryption utilities
│   ├── models/                   # Database models
│   ├── schemas/                  # Pydantic schemas
│   ├── middleware/               # Custom middleware
│   ├── dependencies/             # FastAPI dependencies
│   └── contracts/                # Smart contracts
├── tests/                        # Test suite
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   └── e2e/                     # End-to-end tests
├── docs/                         # Documentation
├── scripts/                      # Utility scripts
├── migrations/                   # Database migrations
└── docker/                       # Docker configurations
```

### Testing

The project includes comprehensive test coverage:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **End-to-End Tests**: Test complete user workflows
- **Security Tests**: Test security vulnerabilities
- **Performance Tests**: Load and stress testing

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m security
pytest -m performance

# Run with coverage
pytest --cov=app --cov-report=html --cov-report=term

# Run specific test file
pytest tests/unit/test_auth.py -v
```

### Code Quality

The project maintains high code quality standards:

- **Code Formatting**: Black, isort
- **Linting**: flake8, pylint, ruff
- **Type Checking**: mypy
- **Security Analysis**: bandit, safety
- **Dependency Scanning**: pip-audit
- **Pre-commit Hooks**: Automated quality checks

## 🚢 Deployment

### Docker Deployment

1. **Build Docker image**
   ```bash
   docker build -t imanipay-blockchain-service .
   ```

2. **Run with Docker Compose**
   ```bash
   docker-compose up -d
   ```

3. **Environment-specific deployment**
   ```bash
   # Development
   docker-compose -f docker-compose.dev.yml up -d
   
   # Production
   docker-compose -f docker-compose.prod.yml up -d
   ```

### Kubernetes Deployment

1. **Apply Kubernetes manifests**
   ```bash
   kubectl apply -f k8s/
   ```

2. **Check deployment status**
   ```bash
   kubectl get pods -l app=imanipay-blockchain-service
   ```

3. **View logs**
   ```bash
   kubectl logs -f deployment/imanipay-blockchain-service
   ```

### Production Considerations

- **Load Balancing**: Use NGINX or cloud load balancers
- **SSL/TLS**: Implement proper certificate management
- **Monitoring**: Set up Prometheus and Grafana
- **Logging**: Configure centralized logging with ELK stack
- **Backup**: Implement database and key backup strategies
- **Scaling**: Configure horizontal pod autoscaling

## 🤝 Contributing

We welcome contributions from the community! Please read our [Contributing Guidelines](CONTRIBUTING.md) for details on how to get started.

### Development Workflow

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**
4. **Run tests and quality checks**
   ```bash
   pytest
   pre-commit run --all-files
   ```
5. **Commit your changes**
   ```bash
   git commit -m "feat: add your feature description"
   ```
6. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```
7. **Create a Pull Request**

### Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [https://docs.imanipay.com](https://docs.imanipay.com)
- **Issues**: [GitHub Issues](https://github.com/imanipay-africa/imanipay-blockchain-service/issues)
- **Discussions**: [GitHub Discussions](https://github.com/imanipay-africa/imanipay-blockchain-service/discussions)
- **Email**: [support@imanipay.com](mailto:support@imanipay.com)

## 🙏 Acknowledgments

- [Algorand Foundation](https://algorand.com) for blockchain infrastructure
- [FastAPI](https://fastapi.tiangolo.com) for the excellent web framework
- [Circle](https://circle.com) for USDC infrastructure
- The African fintech community for inspiration and feedback

---

**Made with ❤️ for Africa by the ImaniPay Team**


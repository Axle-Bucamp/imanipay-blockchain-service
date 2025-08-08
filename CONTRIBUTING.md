# Contributing to ImaniPay Blockchain Service

Thank you for your interest in contributing to ImaniPay Blockchain Service! This document provides guidelines and information for contributors to help maintain code quality and ensure smooth collaboration.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Process](#contributing-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Security Considerations](#security-considerations)
- [Review Process](#review-process)
- [Community](#community)

## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to [conduct@imanipay.com](mailto:conduct@imanipay.com).

### Our Pledge

We pledge to make participation in our project a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity and expression, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

## Getting Started

### Prerequisites

Before contributing, ensure you have:

- **Python 3.11+** installed
- **Git** for version control
- **Docker** for containerized development (optional)
- **PostgreSQL 15+** for database
- **Redis 7+** for caching
- Basic understanding of **FastAPI**, **SQLAlchemy**, and **Algorand**

### First-Time Contributors

If you're new to open source or this project:

1. **Read the documentation** in the `docs/` directory
2. **Browse existing issues** labeled `good first issue`
3. **Join our community** on Discord or GitHub Discussions
4. **Start small** with documentation improvements or bug fixes

### Finding Issues to Work On

Look for issues labeled:
- `good first issue` - Perfect for newcomers
- `help wanted` - Community contributions welcome
- `bug` - Bug fixes needed
- `enhancement` - New features or improvements
- `documentation` - Documentation improvements

## Development Setup

### Local Development Environment

1. **Clone the repository**
   ```bash
   git clone https://github.com/imanipay-africa/imanipay-blockchain-service.git
   cd imanipay-blockchain-service
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Set up pre-commit hooks**
   ```bash
   pre-commit install
   ```

5. **Configure environment**
   ```bash
   cp .env.example .env.development
   # Edit .env.development with your configuration
   ```

6. **Start services**
   ```bash
   # Option 1: Using Docker Compose
   docker-compose -f docker-compose.dev.yml up -d postgres redis
   
   # Option 2: Local installation
   # Start PostgreSQL and Redis manually
   ```

7. **Initialize database**
   ```bash
   alembic upgrade head
   ```

8. **Run the application**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Docker Development

For a fully containerized development environment:

```bash
# Build and start all services
docker-compose -f docker-compose.dev.yml up --build

# Run tests in container
docker-compose -f docker-compose.dev.yml exec api pytest

# Access container shell
docker-compose -f docker-compose.dev.yml exec api bash
```

### IDE Configuration

#### VS Code

Recommended extensions:
- Python
- Pylance
- Black Formatter
- isort
- GitLens
- Docker

Settings (`.vscode/settings.json`):
```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

#### PyCharm

1. Set Python interpreter to `./venv/bin/python`
2. Enable Black formatter in settings
3. Configure isort for import sorting
4. Enable mypy type checking

## Contributing Process

### Workflow Overview

1. **Fork** the repository
2. **Create** a feature branch
3. **Make** your changes
4. **Test** your changes
5. **Submit** a pull request
6. **Respond** to review feedback
7. **Merge** after approval

### Detailed Steps

#### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/imanipay-blockchain-service.git
cd imanipay-blockchain-service

# Add upstream remote
git remote add upstream https://github.com/imanipay-africa/imanipay-blockchain-service.git
```

#### 2. Create Feature Branch

```bash
# Update your main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/issue-description
```

#### 3. Make Changes

- Follow the [coding standards](#coding-standards)
- Write tests for new functionality
- Update documentation as needed
- Ensure all tests pass

#### 4. Commit Changes

Use conventional commit messages:

```bash
# Feature
git commit -m "feat: add cross-border payment validation"

# Bug fix
git commit -m "fix: resolve wallet balance calculation error"

# Documentation
git commit -m "docs: update API documentation for payments"

# Test
git commit -m "test: add unit tests for payment processor"

# Refactor
git commit -m "refactor: improve error handling in auth service"
```

#### 5. Push and Create PR

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create pull request on GitHub
```

### Pull Request Guidelines

**PR Title Format:**
```
type(scope): description

Examples:
feat(payments): add multi-currency support
fix(auth): resolve JWT token expiration issue
docs(api): update endpoint documentation
```

**PR Description Template:**
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
```

## Coding Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with some modifications:

- **Line length**: 100 characters (not 79)
- **String quotes**: Use double quotes for strings
- **Import order**: Follow isort configuration
- **Type hints**: Required for all functions and methods

### Code Formatting

We use automated formatting tools:

```bash
# Format code
black app/ tests/
isort app/ tests/

# Check formatting
black --check app/ tests/
isort --check-only app/ tests/
```

### Linting

Run linting tools before committing:

```bash
# Linting
flake8 app/ tests/
mypy app/
pylint app/

# Security checks
bandit -r app/
safety check
```

### Naming Conventions

**Variables and Functions:**
```python
# Good
user_email = "user@example.com"
def calculate_transaction_fee():
    pass

# Bad
userEmail = "user@example.com"
def CalculateTransactionFee():
    pass
```

**Classes:**
```python
# Good
class PaymentProcessor:
    pass

class UserAccount:
    pass

# Bad
class payment_processor:
    pass

class userAccount:
    pass
```

**Constants:**
```python
# Good
MAX_TRANSACTION_AMOUNT = 10000
DEFAULT_CURRENCY = "USD"

# Bad
max_transaction_amount = 10000
defaultCurrency = "USD"
```

### File Organization

```
app/
├── api/                 # API route handlers
│   ├── __init__.py
│   ├── auth.py
│   ├── payments.py
│   └── wallets.py
├── core/                # Core application components
│   ├── __init__.py
│   ├── config.py
│   └── startup.py
├── models/              # Database models
│   ├── __init__.py
│   ├── user.py
│   └── transaction.py
├── schemas/             # Pydantic schemas
│   ├── __init__.py
│   ├── auth.py
│   └── payment.py
├── services/            # Business logic
│   ├── __init__.py
│   ├── auth.py
│   └── payment_processor.py
└── utils/               # Utility functions
    ├── __init__.py
    └── helpers.py
```

## Testing Guidelines

### Test Structure

We use pytest for testing with the following structure:

```
tests/
├── unit/                # Unit tests
│   ├── test_auth.py
│   ├── test_payments.py
│   └── test_wallets.py
├── integration/         # Integration tests
│   ├── test_api.py
│   └── test_database.py
├── e2e/                 # End-to-end tests
│   └── test_payment_flow.py
├── fixtures/            # Test fixtures
│   └── conftest.py
└── utils/               # Test utilities
    └── helpers.py
```

### Writing Tests

#### Unit Tests

```python
import pytest
from app.services.auth import AuthService
from app.schemas.auth import UserCreate

class TestAuthService:
    def test_create_user_success(self):
        """Test successful user creation."""
        auth_service = AuthService()
        user_data = UserCreate(
            email="test@example.com",
            password="SecurePassword123!"
        )
        
        user = auth_service.create_user(user_data)
        
        assert user.email == "test@example.com"
        assert user.is_active is True

    def test_create_user_duplicate_email(self):
        """Test user creation with duplicate email."""
        auth_service = AuthService()
        user_data = UserCreate(
            email="existing@example.com",
            password="SecurePassword123!"
        )
        
        with pytest.raises(ValueError, match="Email already exists"):
            auth_service.create_user(user_data)
```

#### Integration Tests

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestPaymentAPI:
    def test_create_payment_success(self, auth_headers):
        """Test successful payment creation."""
        payment_data = {
            "amount": 100.00,
            "currency": "USD",
            "recipient": "test@example.com"
        }
        
        response = client.post(
            "/payments",
            json=payment_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        assert response.json()["amount"] == 100.00
```

### Test Coverage

Maintain minimum 80% test coverage:

```bash
# Run tests with coverage
pytest --cov=app --cov-report=html --cov-report=term

# View coverage report
open htmlcov/index.html
```

### Test Categories

Use pytest markers to categorize tests:

```python
@pytest.mark.unit
def test_unit_function():
    pass

@pytest.mark.integration
def test_integration_function():
    pass

@pytest.mark.slow
def test_slow_function():
    pass

@pytest.mark.security
def test_security_function():
    pass
```

Run specific test categories:

```bash
# Run only unit tests
pytest -m unit

# Run all except slow tests
pytest -m "not slow"

# Run security tests
pytest -m security
```

## Documentation

### Code Documentation

#### Docstrings

Use Google-style docstrings:

```python
def calculate_transaction_fee(amount: float, currency: str) -> float:
    """Calculate transaction fee based on amount and currency.
    
    Args:
        amount: Transaction amount in the specified currency
        currency: Currency code (e.g., 'USD', 'EUR')
        
    Returns:
        Transaction fee amount
        
    Raises:
        ValueError: If amount is negative or currency is invalid
        
    Example:
        >>> calculate_transaction_fee(100.0, 'USD')
        2.5
    """
    if amount < 0:
        raise ValueError("Amount must be positive")
    
    # Implementation here
    return amount * 0.025
```

#### Type Hints

Use comprehensive type hints:

```python
from typing import List, Optional, Dict, Any
from decimal import Decimal

def process_payments(
    payments: List[Dict[str, Any]],
    user_id: str,
    options: Optional[Dict[str, str]] = None
) -> List[str]:
    """Process multiple payments for a user."""
    # Implementation here
    pass
```

### API Documentation

API documentation is automatically generated from FastAPI route definitions:

```python
from fastapi import APIRouter, Depends, HTTPException
from app.schemas.payment import PaymentCreate, PaymentResponse

router = APIRouter()

@router.post("/payments", response_model=PaymentResponse)
async def create_payment(
    payment: PaymentCreate,
    current_user: User = Depends(get_current_user)
) -> PaymentResponse:
    """Create a new payment.
    
    This endpoint allows authenticated users to create new payments.
    The payment will be processed asynchronously.
    
    - **amount**: Payment amount (must be positive)
    - **currency**: Currency code (ISO 4217)
    - **recipient**: Recipient email or wallet address
    """
    # Implementation here
    pass
```

### README Updates

When adding new features, update the README:

- Add feature to the features list
- Update installation instructions if needed
- Add usage examples
- Update configuration documentation

## Security Considerations

### Security Review Process

All contributions undergo security review:

1. **Automated Security Scanning**: Bandit, safety checks
2. **Code Review**: Security-focused review by maintainers
3. **Penetration Testing**: For significant changes
4. **Compliance Review**: For regulatory compliance

### Security Guidelines

#### Input Validation

```python
from pydantic import BaseModel, validator
from typing import Optional

class PaymentCreate(BaseModel):
    amount: float
    currency: str
    recipient: str
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        if v > 1000000:  # $1M limit
            raise ValueError('Amount exceeds maximum limit')
        return v
    
    @validator('currency')
    def validate_currency(cls, v):
        allowed_currencies = ['USD', 'EUR', 'NGN', 'KES']
        if v not in allowed_currencies:
            raise ValueError('Invalid currency')
        return v
```

#### SQL Injection Prevention

```python
# Good - Using SQLAlchemy ORM
user = session.query(User).filter(User.email == email).first()

# Good - Using parameterized queries
result = session.execute(
    text("SELECT * FROM users WHERE email = :email"),
    {"email": email}
)

# Bad - String concatenation
query = f"SELECT * FROM users WHERE email = '{email}'"
```

#### Authentication

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(token: str = Depends(security)):
    """Get current authenticated user."""
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        return get_user(user_id)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
```

### Sensitive Data Handling

- **Never commit secrets** to version control
- **Use environment variables** for configuration
- **Encrypt sensitive data** at rest
- **Log carefully** to avoid exposing sensitive information

```python
import logging

# Good
logger.info(f"Payment created for user {user_id}")

# Bad - exposes sensitive data
logger.info(f"Payment created: {payment_data}")
```

## Review Process

### Code Review Checklist

**Functionality:**
- [ ] Code works as intended
- [ ] Edge cases are handled
- [ ] Error handling is appropriate
- [ ] Performance is acceptable

**Code Quality:**
- [ ] Code follows style guidelines
- [ ] Code is readable and maintainable
- [ ] Appropriate comments and documentation
- [ ] No code duplication

**Testing:**
- [ ] Tests are included
- [ ] Tests cover edge cases
- [ ] All tests pass
- [ ] Coverage is maintained

**Security:**
- [ ] Input validation is present
- [ ] No security vulnerabilities
- [ ] Sensitive data is protected
- [ ] Authentication/authorization is correct

### Review Timeline

- **Initial Review**: Within 2 business days
- **Follow-up Reviews**: Within 1 business day
- **Final Approval**: Within 1 business day after all feedback addressed

### Addressing Feedback

1. **Read feedback carefully** and ask questions if unclear
2. **Make requested changes** in separate commits
3. **Respond to comments** explaining your changes
4. **Request re-review** when ready

## Community

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and discussions
- **Discord**: Real-time chat and community support
- **Email**: [community@imanipay.com](mailto:community@imanipay.com)

### Getting Help

If you need help:

1. **Check existing documentation** and issues
2. **Search GitHub Discussions** for similar questions
3. **Ask in Discord** for quick help
4. **Create a GitHub Discussion** for detailed questions
5. **Email the team** for private matters

### Recognition

We recognize contributors through:

- **Contributors file**: Listed in CONTRIBUTORS.md
- **Release notes**: Mentioned in release announcements
- **Social media**: Highlighted on our social channels
- **Swag**: ImaniPay merchandise for significant contributions

## License

By contributing to ImaniPay Blockchain Service, you agree that your contributions will be licensed under the [MIT License](LICENSE).

---

Thank you for contributing to ImaniPay Blockchain Service! Your contributions help make cross-border payments more accessible for everyone in Africa. 🌍


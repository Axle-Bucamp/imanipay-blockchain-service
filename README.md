# 🚀 ImaniPay Blockchain Service

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![UV](https://img.shields.io/badge/UV-0.8.11+-purple.svg)](https://github.com/astral-sh/uv)
[![Pydantic](https://img.shields.io/badge/Pydantic-v2-red.svg)](https://pydantic.dev)
[![Algorand](https://img.shields.io/badge/Algorand-SDK-orange.svg)](https://algorand.com)
[![AlgoKit](https://img.shields.io/badge/AlgoKit-2.8.0+-teal.svg)](https://github.com/algorandfoundation/algokit-cli)

> **Service blockchain moderne pour les paiements cross-border africains**  
> Focus contrats intelligents • Sans authentification • UV Python • Pydantic v2

## 🎯 **Vue d'ensemble**

ImaniPay Blockchain Service est un service **FastAPI moderne** spécialisé dans les **contrats intelligents Algorand** et les **opérations blockchain**. Conçu pour s'intégrer avec un backend externe gérant l'authentification, ce service se concentre exclusivement sur :

- 🔗 **Gestion des wallets Algorand**
- ⛓️ **Contrats intelligents** (Escrow, Multi-sig, Batch)
- 💸 **Transactions blockchain** sécurisées
- 🌐 **Support multi-réseaux** (TestNet/MainNet/LocalNet)
- 🛠️ **Intégration AlgoKit** pour développement

## ✨ **Fonctionnalités principales**

### 🔐 **Contrats intelligents avancés**
- **Escrow contracts** - Transactions sécurisées avec arbitrage
- **Multi-signature wallets** - Signatures multiples avec seuils
- **Batch transactions** - Traitement atomique de lots
- **Asset management** - Gestion Algorand Standard Assets (ASA)

### 🌍 **Multi-réseaux Algorand**
- **TestNet** - Tests et développement
- **MainNet** - Production
- **LocalNet** - Développement local avec AlgoKit

### 🚀 **Architecture moderne**
- **UV Python** - Gestion packages ultra-rapide
- **Pydantic v2** - Validation et configuration
- **SQLite/PostgreSQL** - Base de données flexible
- **FastAPI** - API REST haute performance

## 🛠️ **Installation rapide**

### **Prérequis**
```bash
# Python 3.11+
python --version

# UV Python (recommandé)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env

# AlgoKit (optionnel pour LocalNet)
pipx install algokit
```

### **Installation**
```bash
# Cloner le projet
git clone -b manus https://github.com/Axle-Bucamp/imanipay-blockchain-service.git
cd imanipay-blockchain-service

# Créer l'environnement virtuel
uv venv
source .venv/bin/activate

# Installer les dépendances
uv pip install -e .

# Configurer l'environnement
cp .env.example .env
# Éditer .env avec vos paramètres
```

### **Démarrage**
```bash
# Démarrer le serveur
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Accéder à la documentation
open http://localhost:8000/docs
```

## ⚙️ **Configuration**

### **Variables d'environnement (.env)**
```bash
# Application
APP_NAME=ImaniPay Blockchain Service
APP_VERSION=2.0.0-simplified
APP_ENVIRONMENT=development

# Base de données
DATABASE_URL=sqlite+aiosqlite:///./imanipay_blockchain.db

# Algorand - Basculement automatique
ALGORAND_NETWORK=testnet  # testnet | mainnet | localnet

# TestNet (par défaut)
ALGORAND_ALGOD_ADDRESS=https://testnet-api.algonode.cloud
ALGORAND_INDEXER_ADDRESS=https://testnet-idx.algonode.cloud

# LocalNet (AlgoKit)
# ALGORAND_NETWORK=localnet active automatiquement localhost:4001

# Sécurité
SECRET_KEY=your-secret-key-here
```

### **Basculement de réseaux**
```bash
# Développement local
ALGORAND_NETWORK=localnet

# Tests
ALGORAND_NETWORK=testnet

# Production
ALGORAND_NETWORK=mainnet
```

## 📡 **API Endpoints**

### **🏥 Health & Info**
```http
GET /                    # Informations service
GET /health/             # Health check basique
GET /health/detailed     # Health check complet
GET /docs                # Documentation Swagger
```

### **👛 Wallets**
```http
POST /api/v1/wallets/wallets/create     # Créer wallet
POST /api/v1/wallets/wallets/balance    # Consulter solde
POST /api/v1/wallets/wallets/validate   # Valider wallet
```

### **💸 Transactions**
```http
POST /api/v1/transactions/transactions/send  # Envoyer transaction
```

### **🛠️ AlgoKit**
```http
GET  /api/v1/algokit/status              # Status réseau
POST /api/v1/algokit/localnet/start      # Démarrer LocalNet
POST /api/v1/algokit/localnet/stop       # Arrêter LocalNet
POST /api/v1/algokit/accounts/create-test # Créer compte test
```

## 🔧 **Développement**

### **Structure du projet**
```
imanipay-blockchain-service/
├── app/
│   ├── api/                    # Endpoints API
│   ├── contracts/              # Contrats intelligents
│   │   └── templates/          # Templates (escrow, multisig, batch)
│   ├── services/               # Services blockchain
│   ├── core/                   # Configuration
│   ├── models.py               # Modèles SQLAlchemy
│   └── schemas.py              # Schémas Pydantic
├── pyproject.toml              # Configuration UV
├── .env                        # Variables d'environnement
└── main.py                     # Point d'entrée
```

### **Commandes utiles**
```bash
# Tests
uv run pytest

# Linting
uv run ruff check .
uv run black .

# Type checking
uv run mypy .

# Démarrage avec AlgoKit LocalNet
algokit localnet start
ALGORAND_NETWORK=localnet uvicorn main:app --reload
```

## 🌍 **Cas d'usage - Paiements africains**

### **Remittances familiales**
```python
# Escrow pour transferts sécurisés
POST /api/v1/contracts/escrow/create
{
  "sender": "SENDER_ADDRESS",
  "receiver": "RECEIVER_ADDRESS", 
  "amount": 1000000,  # microAlgos
  "deadline": "2024-12-31T23:59:59Z"
}
```

### **Paiements d'entreprise**
```python
# Multi-signature pour approbations
POST /api/v1/contracts/multisig/create
{
  "signers": ["CFO_ADDRESS", "CEO_ADDRESS", "TREASURER_ADDRESS"],
  "threshold": 2,  # 2 sur 3 signatures requises
  "amount": 5000000
}
```

### **Salaires en lot**
```python
# Batch transactions pour efficacité
POST /api/v1/contracts/batch/create
{
  "transactions": [
    {"to": "EMPLOYEE1", "amount": 500000},
    {"to": "EMPLOYEE2", "amount": 750000},
    {"to": "EMPLOYEE3", "amount": 600000}
  ]
}
```

## 🔒 **Sécurité**

### **Architecture sans authentification**
- ✅ **Authentification externalisée** - Géré par backend principal
- ✅ **CORS permissif** - Intégration multi-domaines
- ✅ **Rate limiting** - Protection contre abus
- ✅ **Validation Pydantic** - Sécurité des données
- ✅ **Logging complet** - Traçabilité des opérations

### **Bonnes pratiques**
- 🔐 **Clés privées chiffrées** en base de données
- 🌐 **HTTPS obligatoire** en production
- 📝 **Audit trail** complet des transactions
- 🛡️ **Validation stricte** des adresses Algorand

## 📚 **Documentation**

- **API Documentation** : `http://localhost:8000/docs`
- **OpenAPI Spec** : `http://localhost:8000/openapi.json`
- **Algorand SDK** : [py-algorand-sdk](https://github.com/algorand/py-algorand-sdk)
- **AlgoKit** : [Documentation officielle](https://github.com/algorandfoundation/algokit-cli)

## 🤝 **Contribution**

### **Développement local**
```bash
# Fork et clone
git clone https://github.com/votre-username/imanipay-blockchain-service.git

# Installation développement
uv pip install -e ".[dev]"

# Pre-commit hooks
pre-commit install

# Tests
uv run pytest --cov=app
```

### **Standards de code**
- **Black** - Formatage automatique
- **Ruff** - Linting moderne
- **mypy** - Type checking
- **pytest** - Tests unitaires

## 📄 **Licence**

Ce projet est sous licence MIT. Voir [LICENSE](LICENSE) pour plus de détails.

## 🌟 **Remerciements**

- **Algorand Foundation** - Blockchain infrastructure
- **FastAPI** - Framework web moderne
- **Astral** - UV Python package manager
- **Pydantic** - Data validation

---

**🌍 Révolutionnez les paiements africains avec ImaniPay ! 💫**

> *Construit avec ❤️ pour l'inclusion financière en Afrique*


# Deployment Guide

This guide provides comprehensive instructions for deploying the ImaniPay Blockchain Service in various environments, from development to production.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Configuration](#environment-configuration)
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Cloud Deployment](#cloud-deployment)
- [Production Considerations](#production-considerations)
- [Monitoring and Observability](#monitoring-and-observability)
- [Backup and Recovery](#backup-and-recovery)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

**Minimum Requirements:**
- CPU: 2 cores
- RAM: 4GB
- Storage: 20GB SSD
- Network: 100 Mbps

**Recommended for Production:**
- CPU: 4+ cores
- RAM: 8GB+
- Storage: 100GB+ SSD
- Network: 1 Gbps
- Load Balancer
- CDN

### Software Dependencies

- **Python**: 3.11 or higher
- **PostgreSQL**: 15 or higher
- **Redis**: 7 or higher
- **Docker**: 20.10+ (for containerized deployment)
- **Kubernetes**: 1.25+ (for K8s deployment)

### External Services

- **Algorand Node**: Access to Algorand network
- **Payment Processors**: Circle, YellowCard, Transak, Coinbase
- **Email Service**: SendGrid or similar
- **SMS Service**: Twilio or similar
- **Monitoring**: Prometheus, Grafana (optional)

## Environment Configuration

### Environment Variables

Create environment-specific configuration files:

#### Development (.env.development)

```bash
# Application Settings
ENVIRONMENT=development
DEBUG=true
APP_NAME=ImaniPay Blockchain Service
APP_VERSION=1.0.0
LOG_LEVEL=DEBUG

# Database Configuration
DATABASE_URL=postgresql://dev_user:dev_pass@localhost:5432/imanipay_dev
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_POOL_SIZE=5

# Security Configuration (Development Only)
JWT_SECRET_KEY=dev-secret-key-not-for-production
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
ENCRYPTION_KEY=dev-encryption-key-32-chars-long

# Algorand Configuration (Testnet)
ALGORAND_NODE_URL=https://testnet-api.algonode.cloud
ALGORAND_INDEXER_URL=https://testnet-idx.algonode.cloud
ALGORAND_NETWORK=testnet

# External Services (Test Keys)
CIRCLE_API_KEY=test_api_key_circle
YELLOWCARD_API_KEY=test_api_key_yellowcard
TRANSAK_API_KEY=test_api_key_transak
COINBASE_API_KEY=test_api_key_coinbase

# Monitoring
PROMETHEUS_ENABLED=false
OPENTELEMETRY_ENABLED=false
```

#### Staging (.env.staging)

```bash
# Application Settings
ENVIRONMENT=staging
DEBUG=false
APP_NAME=ImaniPay Blockchain Service
APP_VERSION=1.0.0
LOG_LEVEL=INFO

# Database Configuration
DATABASE_URL=postgresql://staging_user:${DB_PASSWORD}@staging-db:5432/imanipay_staging
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Redis Configuration
REDIS_URL=redis://staging-redis:6379/0
REDIS_POOL_SIZE=10

# Security Configuration
JWT_SECRET_KEY=${JWT_SECRET_KEY}
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
ENCRYPTION_KEY=${ENCRYPTION_KEY}

# Algorand Configuration (Testnet)
ALGORAND_NODE_URL=https://testnet-api.algonode.cloud
ALGORAND_INDEXER_URL=https://testnet-idx.algonode.cloud
ALGORAND_NETWORK=testnet

# External Services (Sandbox)
CIRCLE_API_KEY=${CIRCLE_SANDBOX_API_KEY}
YELLOWCARD_API_KEY=${YELLOWCARD_SANDBOX_API_KEY}
TRANSAK_API_KEY=${TRANSAK_SANDBOX_API_KEY}
COINBASE_API_KEY=${COINBASE_SANDBOX_API_KEY}

# Monitoring
PROMETHEUS_ENABLED=true
OPENTELEMETRY_ENABLED=true
```

#### Production (.env.production)

```bash
# Application Settings
ENVIRONMENT=production
DEBUG=false
APP_NAME=ImaniPay Blockchain Service
APP_VERSION=1.0.0
LOG_LEVEL=WARNING

# Database Configuration
DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:5432/${DB_NAME}
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30
DATABASE_SSL_MODE=require

# Redis Configuration
REDIS_URL=redis://${REDIS_HOST}:6379/0
REDIS_POOL_SIZE=20
REDIS_SSL=true

# Security Configuration
JWT_SECRET_KEY=${JWT_SECRET_KEY}
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
ENCRYPTION_KEY=${ENCRYPTION_KEY}

# Algorand Configuration (Mainnet)
ALGORAND_NODE_URL=${ALGORAND_MAINNET_URL}
ALGORAND_INDEXER_URL=${ALGORAND_INDEXER_URL}
ALGORAND_NETWORK=mainnet

# External Services (Production)
CIRCLE_API_KEY=${CIRCLE_PROD_API_KEY}
YELLOWCARD_API_KEY=${YELLOWCARD_PROD_API_KEY}
TRANSAK_API_KEY=${TRANSAK_PROD_API_KEY}
COINBASE_API_KEY=${COINBASE_PROD_API_KEY}

# Monitoring
PROMETHEUS_ENABLED=true
OPENTELEMETRY_ENABLED=true
SENTRY_DSN=${SENTRY_DSN}
```

## Local Development

### Quick Start

1. **Clone and setup**
   ```bash
   git clone https://github.com/imanipay-africa/imanipay-blockchain-service.git
   cd imanipay-blockchain-service
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

2. **Setup database**
   ```bash
   # Start PostgreSQL and Redis
   docker-compose -f docker-compose.dev.yml up -d postgres redis
   
   # Run migrations
   alembic upgrade head
   ```

3. **Start development server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Development with Docker

```bash
# Build and start all services
docker-compose -f docker-compose.dev.yml up --build

# Start specific services
docker-compose -f docker-compose.dev.yml up postgres redis

# View logs
docker-compose -f docker-compose.dev.yml logs -f api

# Run tests
docker-compose -f docker-compose.dev.yml exec api pytest
```

## Docker Deployment

### Single Container Deployment

1. **Build the image**
   ```bash
   docker build -t imanipay-blockchain-service:latest .
   ```

2. **Run with environment file**
   ```bash
   docker run -d \
     --name imanipay-api \
     --env-file .env.production \
     -p 8000:8000 \
     imanipay-blockchain-service:latest
   ```

### Docker Compose Deployment

#### Production Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  api:
    image: imanipay-blockchain-service:latest
    restart: unless-stopped
    env_file:
      - .env.production
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - imanipay-network

  postgres:
    image: postgres:15
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    ports:
      - "5432:5432"
    networks:
      - imanipay-network

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    networks:
      - imanipay-network

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - api
    networks:
      - imanipay-network

volumes:
  postgres_data:
  redis_data:

networks:
  imanipay-network:
    driver: bridge
```

#### Deploy with Docker Compose

```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Scale API instances
docker-compose -f docker-compose.prod.yml up -d --scale api=3
```

## Kubernetes Deployment

### Namespace and ConfigMap

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: imanipay
  labels:
    name: imanipay

---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: imanipay-config
  namespace: imanipay
data:
  ENVIRONMENT: "production"
  APP_NAME: "ImaniPay Blockchain Service"
  LOG_LEVEL: "INFO"
  DATABASE_POOL_SIZE: "20"
  REDIS_POOL_SIZE: "20"
  PROMETHEUS_ENABLED: "true"
```

### Secrets

```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: imanipay-secrets
  namespace: imanipay
type: Opaque
data:
  DATABASE_URL: <base64-encoded-database-url>
  JWT_SECRET_KEY: <base64-encoded-jwt-secret>
  ENCRYPTION_KEY: <base64-encoded-encryption-key>
  CIRCLE_API_KEY: <base64-encoded-circle-key>
  REDIS_PASSWORD: <base64-encoded-redis-password>
```

### Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: imanipay-api
  namespace: imanipay
  labels:
    app: imanipay-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: imanipay-api
  template:
    metadata:
      labels:
        app: imanipay-api
    spec:
      containers:
      - name: api
        image: imanipay-blockchain-service:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: imanipay-config
        - secretRef:
            name: imanipay-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Service and Ingress

```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: imanipay-api-service
  namespace: imanipay
spec:
  selector:
    app: imanipay-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP

---
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: imanipay-api-ingress
  namespace: imanipay
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
spec:
  tls:
  - hosts:
    - api.imanipay.com
    secretName: imanipay-tls
  rules:
  - host: api.imanipay.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: imanipay-api-service
            port:
              number: 80
```

### Deploy to Kubernetes

```bash
# Apply all manifests
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -n imanipay
kubectl get services -n imanipay
kubectl get ingress -n imanipay

# View logs
kubectl logs -f deployment/imanipay-api -n imanipay

# Scale deployment
kubectl scale deployment imanipay-api --replicas=5 -n imanipay
```

## Cloud Deployment

### AWS Deployment

#### Using AWS ECS

1. **Create ECR repository**
   ```bash
   aws ecr create-repository --repository-name imanipay-blockchain-service
   ```

2. **Build and push image**
   ```bash
   # Get login token
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com
   
   # Build and tag
   docker build -t imanipay-blockchain-service .
   docker tag imanipay-blockchain-service:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/imanipay-blockchain-service:latest
   
   # Push
   docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/imanipay-blockchain-service:latest
   ```

3. **Create ECS task definition**
   ```json
   {
     "family": "imanipay-api",
     "networkMode": "awsvpc",
     "requiresCompatibilities": ["FARGATE"],
     "cpu": "512",
     "memory": "1024",
     "executionRoleArn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
     "containerDefinitions": [
       {
         "name": "imanipay-api",
         "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/imanipay-blockchain-service:latest",
         "portMappings": [
           {
             "containerPort": 8000,
             "protocol": "tcp"
           }
         ],
         "environment": [
           {
             "name": "ENVIRONMENT",
             "value": "production"
           }
         ],
         "secrets": [
           {
             "name": "DATABASE_URL",
             "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:imanipay/database-url"
           }
         ],
         "logConfiguration": {
           "logDriver": "awslogs",
           "options": {
             "awslogs-group": "/ecs/imanipay-api",
             "awslogs-region": "us-east-1",
             "awslogs-stream-prefix": "ecs"
           }
         }
       }
     ]
   }
   ```

#### Using AWS EKS

```bash
# Create EKS cluster
eksctl create cluster --name imanipay-cluster --region us-east-1 --nodegroup-name standard-workers --node-type t3.medium --nodes 3

# Configure kubectl
aws eks update-kubeconfig --region us-east-1 --name imanipay-cluster

# Deploy application
kubectl apply -f k8s/
```

### Google Cloud Platform

#### Using Google Cloud Run

```bash
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/imanipay-blockchain-service

# Deploy to Cloud Run
gcloud run deploy imanipay-api \
  --image gcr.io/PROJECT_ID/imanipay-blockchain-service \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars ENVIRONMENT=production \
  --memory 1Gi \
  --cpu 1 \
  --max-instances 10
```

#### Using GKE

```bash
# Create GKE cluster
gcloud container clusters create imanipay-cluster \
  --zone us-central1-a \
  --num-nodes 3 \
  --machine-type n1-standard-2

# Get credentials
gcloud container clusters get-credentials imanipay-cluster --zone us-central1-a

# Deploy application
kubectl apply -f k8s/
```

### Microsoft Azure

#### Using Azure Container Instances

```bash
# Create resource group
az group create --name imanipay-rg --location eastus

# Create container instance
az container create \
  --resource-group imanipay-rg \
  --name imanipay-api \
  --image imanipay-blockchain-service:latest \
  --cpu 1 \
  --memory 2 \
  --ports 8000 \
  --environment-variables ENVIRONMENT=production \
  --secure-environment-variables DATABASE_URL=$DATABASE_URL
```

## Production Considerations

### Security

1. **SSL/TLS Configuration**
   ```nginx
   # nginx/nginx.conf
   server {
       listen 443 ssl http2;
       server_name api.imanipay.com;
       
       ssl_certificate /etc/nginx/ssl/cert.pem;
       ssl_certificate_key /etc/nginx/ssl/key.pem;
       ssl_protocols TLSv1.2 TLSv1.3;
       ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
       
       location / {
           proxy_pass http://api:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

2. **Firewall Rules**
   ```bash
   # Allow only necessary ports
   ufw allow 22/tcp    # SSH
   ufw allow 80/tcp    # HTTP
   ufw allow 443/tcp   # HTTPS
   ufw deny 8000/tcp   # Block direct API access
   ufw enable
   ```

3. **Database Security**
   ```sql
   -- Create dedicated database user
   CREATE USER imanipay_api WITH PASSWORD 'strong_password';
   GRANT CONNECT ON DATABASE imanipay_prod TO imanipay_api;
   GRANT USAGE ON SCHEMA public TO imanipay_api;
   GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO imanipay_api;
   ```

### Performance Optimization

1. **Database Optimization**
   ```sql
   -- Add indexes for frequently queried columns
   CREATE INDEX idx_users_email ON users(email);
   CREATE INDEX idx_transactions_user_id ON transactions(user_id);
   CREATE INDEX idx_transactions_created_at ON transactions(created_at);
   CREATE INDEX idx_wallets_user_id ON wallets(user_id);
   ```

2. **Redis Configuration**
   ```conf
   # redis.conf
   maxmemory 2gb
   maxmemory-policy allkeys-lru
   save 900 1
   save 300 10
   save 60 10000
   ```

3. **Application Tuning**
   ```bash
   # Environment variables for production
   UVICORN_WORKERS=4
   UVICORN_WORKER_CLASS=uvicorn.workers.UvicornWorker
   DATABASE_POOL_SIZE=20
   DATABASE_MAX_OVERFLOW=30
   REDIS_POOL_SIZE=20
   ```

### High Availability

1. **Load Balancer Configuration**
   ```yaml
   # HAProxy configuration
   global
       daemon
   
   defaults
       mode http
       timeout connect 5000ms
       timeout client 50000ms
       timeout server 50000ms
   
   frontend api_frontend
       bind *:80
       bind *:443 ssl crt /etc/ssl/certs/imanipay.pem
       redirect scheme https if !{ ssl_fc }
       default_backend api_backend
   
   backend api_backend
       balance roundrobin
       option httpchk GET /health
       server api1 10.0.1.10:8000 check
       server api2 10.0.1.11:8000 check
       server api3 10.0.1.12:8000 check
   ```

2. **Database Replication**
   ```yaml
   # PostgreSQL streaming replication
   # Master configuration
   wal_level = replica
   max_wal_senders = 3
   wal_keep_segments = 64
   
   # Slave configuration
   hot_standby = on
   ```

## Monitoring and Observability

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'imanipay-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: /metrics
    scrape_interval: 5s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

### Grafana Dashboards

```json
{
  "dashboard": {
    "title": "ImaniPay API Metrics",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      }
    ]
  }
}
```

### Logging Configuration

```yaml
# logging.yml
version: 1
disable_existing_loggers: false

formatters:
  standard:
    format: '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
  json:
    format: '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: json
    stream: ext://sys.stdout

  file:
    class: logging.handlers.RotatingFileHandler
    level: INFO
    formatter: json
    filename: /var/log/imanipay/api.log
    maxBytes: 10485760  # 10MB
    backupCount: 5

loggers:
  app:
    level: INFO
    handlers: [console, file]
    propagate: false

root:
  level: INFO
  handlers: [console]
```

## Backup and Recovery

### Database Backup

```bash
#!/bin/bash
# backup-db.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/postgres"
DB_NAME="imanipay_prod"

# Create backup directory
mkdir -p $BACKUP_DIR

# Create database backup
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME | gzip > $BACKUP_DIR/backup_$DATE.sql.gz

# Upload to S3
aws s3 cp $BACKUP_DIR/backup_$DATE.sql.gz s3://imanipay-backups/postgres/

# Clean up old backups (keep last 7 days)
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete
```

### Redis Backup

```bash
#!/bin/bash
# backup-redis.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/redis"

# Create backup directory
mkdir -p $BACKUP_DIR

# Create Redis backup
redis-cli --rdb $BACKUP_DIR/dump_$DATE.rdb

# Upload to S3
aws s3 cp $BACKUP_DIR/dump_$DATE.rdb s3://imanipay-backups/redis/

# Clean up old backups
find $BACKUP_DIR -name "dump_*.rdb" -mtime +7 -delete
```

### Automated Backup with Cron

```bash
# Add to crontab
0 2 * * * /scripts/backup-db.sh
0 3 * * * /scripts/backup-redis.sh
```

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
   ```bash
   # Check database connectivity
   psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT 1;"
   
   # Check connection pool
   curl http://localhost:8000/health/db
   ```

2. **Redis Connection Issues**
   ```bash
   # Check Redis connectivity
   redis-cli -h $REDIS_HOST ping
   
   # Check Redis memory usage
   redis-cli info memory
   ```

3. **High Memory Usage**
   ```bash
   # Check memory usage
   docker stats
   
   # Check application metrics
   curl http://localhost:8000/metrics | grep memory
   ```

4. **Slow API Responses**
   ```bash
   # Check database slow queries
   SELECT query, mean_time, calls 
   FROM pg_stat_statements 
   ORDER BY mean_time DESC 
   LIMIT 10;
   
   # Check API response times
   curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health
   ```

### Health Checks

```bash
# Application health
curl http://localhost:8000/health

# Database health
curl http://localhost:8000/health/db

# Redis health
curl http://localhost:8000/health/redis

# External services health
curl http://localhost:8000/health/external
```

### Log Analysis

```bash
# View application logs
docker logs -f imanipay-api

# Search for errors
docker logs imanipay-api 2>&1 | grep ERROR

# Monitor real-time logs
tail -f /var/log/imanipay/api.log | jq '.'
```

## Support

For deployment support:

- **Documentation**: [https://docs.imanipay.com/deployment](https://docs.imanipay.com/deployment)
- **DevOps Support**: [devops@imanipay.com](mailto:devops@imanipay.com)
- **Emergency Support**: [emergency@imanipay.com](mailto:emergency@imanipay.com)
- **Status Page**: [https://status.imanipay.com](https://status.imanipay.com)


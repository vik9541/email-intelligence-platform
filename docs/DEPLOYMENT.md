# Deployment Guide

Comprehensive guide for deploying email-service to various environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [CI/CD Pipeline](#cicd-pipeline)
6. [Configuration](#configuration)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)
9. [Rollback Procedures](#rollback-procedures)

---

## Prerequisites

### Required Tools

```bash
# Docker
docker --version  # >= 20.10

# Kubernetes CLI
kubectl version --client  # >= 1.25

# Helm (optional, for chart deployments)
helm version  # >= 3.0

# Python (for local development)
python --version  # >= 3.11
```

### Required Access

- Docker Registry credentials
- Kubernetes cluster access (kubeconfig)
- GitHub repository access (for CI/CD)

---

## Local Development

### 1. Clone and Setup

```bash
# Clone repository
git clone https://github.com/your-org/email-service.git
cd email-service

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit with your settings
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/email_service
# KAFKA_BOOTSTRAP_SERVERS=localhost:29092
```

### 3. Run Locally

```bash
# Start dependencies with docker-compose
docker-compose up -d postgres kafka redis

# Run database migrations
alembic upgrade head

# Start the application
uvicorn app.main:app --reload --port 8000

# Verify
curl http://localhost:8000/health
```

### 4. Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test file
pytest tests/test_erp_action_executor.py -v
```

---

## Docker Deployment

### 1. Build Image

```bash
# Build production image
docker build -t email-service:latest .

# Build with specific tag
docker build -t email-service:v1.0.0 .

# Build for specific platform
docker build --platform linux/amd64 -t email-service:latest .
```

### 2. Run Container

```bash
# Run with environment file
docker run -d \
  --name email-service \
  -p 8000:8000 \
  --env-file .env \
  email-service:latest

# Run with explicit environment variables
docker run -d \
  --name email-service \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db" \
  -e KAFKA_BOOTSTRAP_SERVERS="kafka:29092" \
  email-service:latest

# Verify
curl http://localhost:8000/health
curl http://localhost:8000/health/ready
```

### 3. Push to Registry

```bash
# Tag for registry
docker tag email-service:latest your-registry.com/email-service:latest
docker tag email-service:latest your-registry.com/email-service:v1.0.0

# Login to registry
docker login your-registry.com

# Push
docker push your-registry.com/email-service:latest
docker push your-registry.com/email-service:v1.0.0
```

### 4. Docker Compose (Full Stack)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f email-service

# Stop all services
docker-compose down
```

---

## Kubernetes Deployment

### 1. Cluster Setup (Minikube)

```bash
# Start minikube
minikube start --memory=4096 --cpus=4

# Enable addons
minikube addons enable ingress
minikube addons enable metrics-server

# Verify
kubectl cluster-info
```

### 2. Deploy Application

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Apply ConfigMap
kubectl apply -f k8s/configmap.yaml

# Create secrets (edit first!)
# Option 1: From file
kubectl create secret generic email-service-secrets \
  --from-env-file=.env \
  -n email-service

# Option 2: Apply template (edit values first)
kubectl apply -f k8s/secrets.yaml

# Apply network policies
kubectl apply -f k8s/networkpolicy.yaml

# Deploy application
kubectl apply -f k8s/deployment.yaml

# Create service
kubectl apply -f k8s/service.yaml

# Create ingress
kubectl apply -f k8s/ingress.yaml

# Setup autoscaling
kubectl apply -f k8s/hpa.yaml
```

### 3. Verify Deployment

```bash
# Check deployment status
kubectl get deployments -n email-service

# Check pods
kubectl get pods -n email-service

# Check services
kubectl get svc -n email-service

# Check HPA
kubectl get hpa -n email-service

# View logs
kubectl logs -f deployment/email-service -n email-service

# Describe pod (for troubleshooting)
kubectl describe pod <pod-name> -n email-service
```

### 4. Access Application

```bash
# Port forward for local access
kubectl port-forward svc/email-service 8000:8000 -n email-service

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/health/ready

# For minikube with ingress
minikube ip  # Get IP
# Add to /etc/hosts: <minikube-ip> email-api.example.com
curl http://email-api.example.com/health
```

### 5. Scale Application

```bash
# Manual scale
kubectl scale deployment email-service --replicas=5 -n email-service

# Check HPA status
kubectl get hpa email-service-hpa -n email-service

# Describe HPA for details
kubectl describe hpa email-service-hpa -n email-service
```

---

## CI/CD Pipeline

### GitHub Actions Workflows

#### Build Pipeline (build.yml)

Triggers on:
- Push to `main` or `develop` branches
- Pull requests
- Version tags (`v*`)

Steps:
1. **Lint**: Ruff linter and formatter
2. **Test**: Pytest with coverage
3. **Security**: Bandit and Safety checks
4. **Build**: Docker multi-arch build
5. **Push**: Push to registry (main branch only)
6. **Validate**: Kubernetes manifest validation

#### Deploy Pipeline (deploy.yml)

Triggers on:
- Manual dispatch (workflow_dispatch)
- Release published

Inputs:
- `environment`: staging or production
- `image_tag`: Docker image tag to deploy
- `dry_run`: Preview changes without applying

### Required Secrets

Configure in GitHub repository settings:

```
DOCKER_REGISTRY      # e.g., ghcr.io/your-org
DOCKER_USERNAME      # Registry username
DOCKER_PASSWORD      # Registry password/token
KUBECONFIG           # Base64-encoded kubeconfig
SLACK_WEBHOOK_URL    # (optional) Slack notifications
```

### Manual Deployment

```bash
# Via GitHub Actions
# Go to Actions > Deploy to Kubernetes > Run workflow

# Via kubectl
kubectl set image deployment/email-service \
  email-service=your-registry/email-service:v1.0.0 \
  -n email-service

# Watch rollout
kubectl rollout status deployment/email-service -n email-service
```

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENV` | Environment (dev/staging/production) | `production` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka brokers | Required |
| `REDIS_HOST` | Redis host | `localhost` |
| `ERP_API_BASE_URL` | ERP API endpoint | Required |
| `ERP_API_KEY` | ERP API key | Required |

### Resource Limits

Default limits in deployment:

```yaml
resources:
  requests:
    cpu: "500m"
    memory: "1Gi"
  limits:
    cpu: "1000m"
    memory: "2Gi"
```

Adjust based on workload:
- **Low traffic**: requests 250m/512Mi, limits 500m/1Gi
- **High traffic**: requests 1000m/2Gi, limits 2000m/4Gi

---

## Monitoring

### Health Endpoints

| Endpoint | Purpose | Used By |
|----------|---------|---------|
| `/health` | Liveness check | K8s liveness probe |
| `/health/ready` | Readiness check | K8s readiness probe |
| `/health/live` | Simple alive check | Load balancers |
| `/metrics` | Prometheus metrics | Prometheus scraper |

### Prometheus Metrics

Application exposes metrics at `/metrics`:
- `email_service_requests_total` - Request counter
- `email_service_request_duration_seconds` - Request latency histogram
- `email_service_up` - Service availability gauge

### Grafana Dashboard

Import dashboard from `dashboards/analysis-api-monitoring.json`

---

## Troubleshooting

### Common Issues

#### Pod CrashLoopBackOff

```bash
# Check logs
kubectl logs <pod-name> -n email-service --previous

# Common causes:
# - Missing environment variables
# - Database connection failure
# - Invalid configuration
```

#### Pod Pending

```bash
# Describe pod
kubectl describe pod <pod-name> -n email-service

# Check events
kubectl get events -n email-service --sort-by='.lastTimestamp'

# Common causes:
# - Insufficient resources
# - Image pull errors
# - PVC not bound
```

#### Readiness Probe Failing

```bash
# Test readiness endpoint
kubectl exec -it <pod-name> -n email-service -- curl http://localhost:8000/health/ready

# Check database connectivity
kubectl exec -it <pod-name> -n email-service -- nc -zv postgresql.database.svc.cluster.local 5432
```

#### High Memory Usage

```bash
# Check resource usage
kubectl top pods -n email-service

# Increase limits if needed
kubectl patch deployment email-service -n email-service \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"email-service","resources":{"limits":{"memory":"4Gi"}}}]}}}}'
```

### Debug Commands

```bash
# Shell into pod
kubectl exec -it <pod-name> -n email-service -- /bin/bash

# Check environment
kubectl exec -it <pod-name> -n email-service -- env | grep -E "DATABASE|KAFKA"

# Test DNS resolution
kubectl exec -it <pod-name> -n email-service -- nslookup postgresql.database.svc.cluster.local

# View all resources
kubectl get all -n email-service
```

---

## Rollback Procedures

### Kubernetes Rollback

```bash
# View rollout history
kubectl rollout history deployment/email-service -n email-service

# Rollback to previous version
kubectl rollout undo deployment/email-service -n email-service

# Rollback to specific revision
kubectl rollout undo deployment/email-service -n email-service --to-revision=2

# Verify rollback
kubectl rollout status deployment/email-service -n email-service
```

### Docker Image Rollback

```bash
# Pull previous version
docker pull your-registry/email-service:v1.0.0-previous

# Update deployment
kubectl set image deployment/email-service \
  email-service=your-registry/email-service:v1.0.0-previous \
  -n email-service
```

### Database Rollback

```bash
# Check current migration
alembic current

# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>
```

---

## Security Checklist

- [ ] All secrets stored in Kubernetes Secrets or external vault
- [ ] No hardcoded credentials in code or configs
- [ ] Container runs as non-root user
- [ ] Network policies restrict traffic
- [ ] TLS enabled for ingress
- [ ] Resource limits set
- [ ] Security scanning in CI/CD
- [ ] RBAC configured for service account

---

## Contact

- **Team**: Email Service Team
- **Slack**: #email-service
- **On-call**: PagerDuty rotation

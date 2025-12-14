# 📧 Email Intelligence Platform

[![CI/CD Pipeline](https://github.com/username/email-intelligence-platform/actions/workflows/build.yml/badge.svg)](https://github.com/username/email-intelligence-platform/actions/workflows/build.yml)
[![Deploy](https://github.com/username/email-intelligence-platform/actions/workflows/deploy.yml/badge.svg)](https://github.com/username/email-intelligence-platform/actions/workflows/deploy.yml)
[![codecov](https://codecov.io/gh/username/email-intelligence-platform/branch/main/graph/badge.svg)](https://codecov.io/gh/username/email-intelligence-platform)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

> 🚀 **Production-Ready** | Intelligent email processing platform with real-time analysis, classification, and ERP integration.

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [Deployment](#-deployment)
- [API Reference](#-api-reference)
- [Monitoring](#-monitoring)
- [Contributing](#-contributing)
- [Documentation](#-documentation)
- [License](#-license)

---

## 🎯 Overview

Email Intelligence Platform is an enterprise-grade solution for automated email processing that:

- 📧 **Analyzes** incoming emails for sentiment, urgency, and intent
- 📁 **Classifies** emails into actionable categories
- ⚡ **Executes** automated actions in ERP systems
- 📊 **Provides** real-time monitoring and analytics

### Key Metrics

| Metric | Value |
|--------|-------|
| Processing Speed | 1,000+ emails/minute |
| Response Time (p95) | < 200ms |
| Availability | 99.9% SLA |
| Test Coverage | 95%+ |

---

## ✨ Features

### Core Capabilities

- **🔍 Email Analysis Engine**
  - Sentiment analysis (positive/negative/neutral)
  - Urgency detection (low/medium/high/critical)
  - Intent extraction and classification
  - Multi-language support

- **📊 Smart Classification**
  - Rule-based + ML-enhanced classification
  - Categories: ORDER, SUPPORT, INVOICE, GENERAL
  - Confidence scoring
  - Custom category support

- **🔗 ERP Integration**
  - Create orders automatically
  - Update invoice status
  - Generate support tickets
  - Extensible action framework

- **📡 Real-time Processing**
  - Apache Kafka streaming
  - Event-driven architecture
  - Dead letter queue for failures
  - Exactly-once processing

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/username/email-intelligence-platform.git
cd email-intelligence-platform

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f email-service
```

Access the API at: http://localhost:8000/docs

### Option 2: Local Development

```bash
# Clone the repository
git clone https://github.com/username/email-intelligence-platform.git
cd email-intelligence-platform

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest --cov=app

# Start the application
uvicorn app.main:app --reload
```

### Option 3: Kubernetes

```bash
# Apply all manifests
kubectl apply -f k8s/

# Verify deployment
kubectl get pods -n email-service

# Check health
kubectl port-forward svc/email-service 8000:8000 -n email-service
curl http://localhost:8000/health
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL CLIENTS                               │
│                    (Email Systems, APIs, Webhooks)                       │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         INGRESS / LOAD BALANCER                          │
│                            (NGINX / Traefik)                             │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        EMAIL INTELLIGENCE PLATFORM                       │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      FastAPI Application                         │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │    │
│  │  │   Analyze   │  │  Classify   │  │    Execute Actions      │  │    │
│  │  │   Engine    │  │   Engine    │  │    (ERP Integration)    │  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                              (3+ replicas, HPA)                          │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│  PostgreSQL   │       │    Kafka      │       │    Redis      │
│  (Database)   │       │  (Messaging)  │       │   (Cache)     │
└───────────────┘       └───────────────┘       └───────────────┘
```

### Technology Stack

| Layer | Technology |
|-------|------------|
| **Language** | Python 3.11 |
| **Framework** | FastAPI + Uvicorn |
| **Database** | PostgreSQL 15 |
| **Cache** | Redis 7 |
| **Messaging** | Apache Kafka 3.5 |
| **Container** | Docker 24+ |
| **Orchestration** | Kubernetes 1.25+ |
| **CI/CD** | GitHub Actions |
| **Monitoring** | Prometheus + Grafana |

---

## 📦 Deployment

### Kubernetes Deployment

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Deploy configuration
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml  # Edit with real values first!

# Deploy application
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/networkpolicy.yaml

# Verify
kubectl get all -n email-service
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka broker addresses | Yes |
| `ERP_API_URL` | ERP system endpoint | Yes |
| `ERP_API_KEY` | ERP authentication key | Yes |
| `LOG_LEVEL` | Logging verbosity | No (INFO) |

### Production Checklist

- [ ] Secrets configured (not committed to repo!)
- [ ] TLS certificates installed
- [ ] Resource limits set
- [ ] HPA configured
- [ ] Network policies applied
- [ ] Monitoring enabled
- [ ] Alerting configured
- [ ] Backup strategy implemented

For detailed deployment instructions, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

---

## 📡 API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/analyze` | Analyze single email |
| `POST` | `/api/v1/batch` | Batch email processing |
| `GET` | `/api/v1/status/{id}` | Get analysis status |
| `GET` | `/health` | Liveness probe |
| `GET` | `/health/ready` | Readiness probe |
| `GET` | `/metrics` | Prometheus metrics |

### Example Request

```bash
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "subject": "Urgent: Order #12345 Issue",
    "body": "Please help with my order. It hasnt arrived yet.",
    "sender": "customer@example.com"
  }'
```

### Example Response

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "analysis": {
    "sentiment": "negative",
    "urgency": "high",
    "intent": "support_request",
    "category": "SUPPORT",
    "confidence": 0.92
  },
  "action": {
    "type": "create_ticket",
    "result": {
      "ticket_id": "TKT-2024-001234",
      "priority": "high"
    }
  },
  "processed_at": "2025-12-14T15:30:00Z"
}
```

Full API documentation available at `/docs` (Swagger UI) or `/redoc` (ReDoc).

---

## 📊 Monitoring

### Grafana Dashboard

Access: `http://grafana.example.com/d/email-analysis`

**Panels:**
1. 📈 Email Processing Rate
2. 📊 Classification Distribution
3. ⏱️ Response Time Percentiles
4. ❌ Error Rate
5. ✅ ERP Action Success Rate
6. 📉 Kafka Consumer Lag
7. 💻 Resource Utilization
8. 🏷️ Top Categories (Live)
9. 🏥 System Health Overview

### Health Endpoints

```bash
# Liveness (is the app running?)
curl http://localhost:8000/health
# Response: {"status": "healthy"}

# Readiness (is the app ready for traffic?)
curl http://localhost:8000/health/ready
# Response: {"status": "ready", "checks": {"database": "ok", "kafka": "ok", "redis": "ok"}}

# Metrics (Prometheus format)
curl http://localhost:8000/metrics
```

### Alerting

| Alert | Condition | Severity |
|-------|-----------|----------|
| High Error Rate | >1% for 5min | Critical |
| High Latency | p95 >1s for 5min | Warning |
| Kafka Lag | >10k messages | Warning |
| Pod Restarts | >3 in 1hr | Warning |

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Quick Start for Contributors

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/email-intelligence-platform.git
cd email-intelligence-platform

# Create branch
git checkout -b feature/your-feature

# Make changes and test
pytest --cov=app

# Commit with conventional commits
git commit -m "feat: add new feature"

# Push and create PR
git push origin feature/your-feature
```

### Development Standards

- **Code Style**: Ruff + Black
- **Type Hints**: Required (MyPy strict)
- **Tests**: Required for new features
- **Docs**: Update README/docstrings as needed
- **Commits**: Follow [Conventional Commits](https://www.conventionalcommits.org/)

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [00_START_HERE.md](docs/00_START_HERE.md) | Master entry point |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | Deployment guide |
| [EXECUTIVE_BRIEF.md](docs/EXECUTIVE_BRIEF.md) | Executive summary |
| [FINAL_DELIVERY_MANIFEST.md](docs/FINAL_DELIVERY_MANIFEST.md) | Technical overview |
| [GO_LIVE_CHECKLIST.md](docs/GO_LIVE_CHECKLIST.md) | Launch checklist |
| [WEEK7_PLAN.md](docs/WEEK7_PLAN.md) | Go-live schedule |
| [k8s/README.md](k8s/README.md) | Kubernetes guide |

---

## 📁 Project Structure

```
email-intelligence-platform/
├── 📂 app/                    # Application code
│   ├── main.py               # FastAPI entry point
│   ├── api/                  # API routes
│   ├── services/             # Business logic
│   └── models/               # Data models
├── 📂 tests/                  # Test suite
├── 📂 k8s/                    # Kubernetes manifests
├── 📂 .github/                # GitHub Actions & configs
│   ├── workflows/            # CI/CD pipelines
│   └── CODEOWNERS           # Code ownership
├── 📂 docs/                   # Documentation
├── 📂 grafana/                # Monitoring dashboards
├── 📂 scripts/                # Utility scripts
├── Dockerfile                # Container build
├── docker-compose.yml        # Local development
├── requirements.txt          # Python dependencies
├── pyproject.toml           # Project configuration
└── README.md                # This file
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- FastAPI team for the amazing framework
- All contributors who helped build this platform

---

## 📞 Support

- 📧 Email: support@example.com
- 💬 Slack: #email-intelligence-platform
- 🐛 Issues: [GitHub Issues](https://github.com/username/email-intelligence-platform/issues)

---

<p align="center">
  <b>Made with ❤️ by the Email Intelligence Team</b>
</p>

<p align="center">
  <a href="#-email-intelligence-platform">⬆️ Back to Top</a>
</p>

# Kubernetes Manifests

Kubernetes configuration files for deploying email-service.

## Directory Structure

```
k8s/
├── namespace.yaml      # Namespace definition
├── configmap.yaml      # Non-sensitive configuration
├── secrets.yaml        # Sensitive configuration (template)
├── deployment.yaml     # Application deployment + ServiceAccount
├── service.yaml        # ClusterIP, NodePort, Headless services
├── ingress.yaml        # HTTP/HTTPS routing
├── hpa.yaml            # Horizontal Pod Autoscaler + PDB
├── networkpolicy.yaml  # Network security policies
└── README.md           # This file
```

## Quick Start

### 1. Prerequisites

```bash
# Kubernetes cluster (minikube, kind, or cloud)
kubectl cluster-info

# Metrics server (for HPA)
kubectl top nodes
```

### 2. Deploy All Resources

```bash
# Apply all manifests in order
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml  # Edit first!
kubectl apply -f k8s/networkpolicy.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml

# Or apply all at once
kubectl apply -f k8s/
```

### 3. Verify Deployment

```bash
kubectl get all -n email-service
```

---

## Manifest Details

### namespace.yaml

Creates isolated namespace for all email-service resources.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: email-service
```

### configmap.yaml

Non-sensitive configuration values:

| Key | Description |
|-----|-------------|
| `APP_ENV` | Environment name |
| `LOG_LEVEL` | Logging verbosity |
| `DATABASE_HOST` | Database hostname |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka brokers |

**Updating ConfigMap:**
```bash
kubectl edit configmap email-service-config -n email-service
# or
kubectl apply -f k8s/configmap.yaml
# Then restart pods to pick up changes
kubectl rollout restart deployment/email-service -n email-service
```

### secrets.yaml

⚠️ **WARNING**: This is a TEMPLATE. Never commit real secrets!

**Production Secret Management Options:**

1. **kubectl from file:**
   ```bash
   kubectl create secret generic email-service-secrets \
     --from-env-file=.env \
     -n email-service
   ```

2. **Sealed Secrets:**
   ```bash
   kubeseal --format yaml < k8s/secrets.yaml > k8s/sealed-secrets.yaml
   kubectl apply -f k8s/sealed-secrets.yaml
   ```

3. **External Secrets Operator:**
   ```yaml
   apiVersion: external-secrets.io/v1beta1
   kind: ExternalSecret
   spec:
     secretStoreRef:
       name: vault-backend
     target:
       name: email-service-secrets
     data:
       - secretKey: DATABASE_PASSWORD
         remoteRef:
           key: email-service/database
           property: password
   ```

4. **HashiCorp Vault:**
   Use vault-injector sidecar or CSI driver.

### deployment.yaml

Key features:
- **Replicas**: 3 for high availability
- **Resource Limits**: CPU 1000m, Memory 2Gi
- **Probes**: Liveness, Readiness, Startup
- **Security**: Non-root user, read-only filesystem
- **Anti-affinity**: Spread pods across nodes

**Probe Configuration:**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  periodSeconds: 30
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  periodSeconds: 10
  failureThreshold: 2
```

**Updating Deployment:**
```bash
# Update image
kubectl set image deployment/email-service \
  email-service=your-registry/email-service:v1.1.0 \
  -n email-service

# Watch rollout
kubectl rollout status deployment/email-service -n email-service
```

### service.yaml

Three service types:

| Service | Type | Use Case |
|---------|------|----------|
| `email-service` | ClusterIP | In-cluster communication |
| `email-service-nodeport` | NodePort (30800) | Local testing |
| `email-service-headless` | ClusterIP (None) | Direct pod access |

### ingress.yaml

Routes external traffic:

| Path | Backend |
|------|---------|
| `/api/v1/analysis/*` | email-service:8000 |
| `/health/*` | email-service:8000 |
| `/metrics` | email-service:8000 |

**Key Annotations:**
- `nginx.ingress.kubernetes.io/ssl-redirect: "true"` - Force HTTPS
- `nginx.ingress.kubernetes.io/limit-rps: "100"` - Rate limiting
- `nginx.ingress.kubernetes.io/proxy-body-size: "50m"` - Max request size

**TLS Setup:**
```bash
# Generate self-signed cert (dev)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout tls.key -out tls.crt \
  -subj "/CN=email-api.example.com"

kubectl create secret tls email-service-tls \
  --cert=tls.crt --key=tls.key \
  -n email-service

# For production, use cert-manager with Let's Encrypt
```

### hpa.yaml

Autoscaling configuration:

| Setting | Value |
|---------|-------|
| Min Replicas | 2 |
| Max Replicas | 10 |
| Target CPU | 70% |
| Scale Up Cooldown | 60s |
| Scale Down Cooldown | 300s |

**Monitor HPA:**
```bash
# Current status
kubectl get hpa -n email-service

# Detailed info
kubectl describe hpa email-service-hpa -n email-service

# Watch scaling
kubectl get hpa -n email-service -w
```

**Pod Disruption Budget** ensures at least 1 pod during voluntary disruptions.

### networkpolicy.yaml

Zero-trust networking:

| Policy | Direction | Target |
|--------|-----------|--------|
| `default-deny-all` | Both | All pods |
| `allow-ingress-controller` | Ingress | Ingress namespace |
| `allow-prometheus-scrape` | Ingress | Monitoring namespace |
| `allow-egress-postgresql` | Egress | Database (5432) |
| `allow-egress-kafka` | Egress | Kafka (9092, 29092) |
| `allow-egress-redis` | Egress | Redis (6379) |
| `allow-egress-dns` | Egress | kube-system (53) |

---

## Common Operations

### Scaling

```bash
# Manual scale
kubectl scale deployment email-service --replicas=5 -n email-service

# Adjust HPA limits
kubectl patch hpa email-service-hpa -n email-service \
  -p '{"spec":{"maxReplicas":20}}'
```

### Rolling Update

```bash
# Update image with zero downtime
kubectl set image deployment/email-service \
  email-service=your-registry/email-service:v2.0.0 \
  -n email-service

# Monitor
kubectl rollout status deployment/email-service -n email-service
```

### Rollback

```bash
# View history
kubectl rollout history deployment/email-service -n email-service

# Rollback to previous
kubectl rollout undo deployment/email-service -n email-service

# Rollback to specific revision
kubectl rollout undo deployment/email-service \
  --to-revision=3 -n email-service
```

### Debugging

```bash
# Pod logs
kubectl logs -f deployment/email-service -n email-service

# Shell access
kubectl exec -it <pod-name> -n email-service -- /bin/bash

# Events
kubectl get events -n email-service --sort-by='.lastTimestamp'

# Resource usage
kubectl top pods -n email-service
```

### Cleanup

```bash
# Delete all resources
kubectl delete -f k8s/

# Or delete namespace (removes everything)
kubectl delete namespace email-service
```

---

## Validation

```bash
# Dry-run validation
kubectl apply --dry-run=client -f k8s/

# Kubeval (schema validation)
kubeval --strict k8s/*.yaml

# Kube-score (best practices)
kube-score score k8s/*.yaml
```

---

## Customization

### Different Environments

Create overlays with Kustomize:

```
k8s/
├── base/
│   ├── deployment.yaml
│   └── kustomization.yaml
├── overlays/
│   ├── staging/
│   │   ├── kustomization.yaml
│   │   └── replicas-patch.yaml
│   └── production/
│       ├── kustomization.yaml
│       └── resources-patch.yaml
```

```bash
# Deploy staging
kubectl apply -k k8s/overlays/staging/

# Deploy production
kubectl apply -k k8s/overlays/production/
```

### Helm Chart

For more complex deployments, consider creating a Helm chart:

```bash
helm create email-service-chart
# Customize templates and values.yaml
helm install email-service ./email-service-chart -n email-service
```

---

## Security Notes

1. **Never commit real secrets** to version control
2. **Use RBAC** to limit service account permissions
3. **Enable Pod Security Standards** in namespace
4. **Regularly update** base images for security patches
5. **Scan images** for vulnerabilities in CI/CD
6. **Rotate secrets** periodically

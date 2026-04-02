# Customer Success Digital FTE - Kubernetes Deployment Guide

## Prerequisites

- Kubernetes cluster (v1.25+)
- kubectl configured
- Helm (optional, for dependencies)
- Container registry access
- Storage class provisioned

## Quick Start

### 1. Build and Push Images

```bash
# Build API image
docker build -t your-registry/customer-success-fte-api:latest .

# Build Worker image
docker build -f Dockerfile.worker -t your-registry/customer-success-fte-worker:latest .

# Push images
docker push your-registry/customer-success-fte-api:latest
docker push your-registry/customer-success-fte-worker:latest
```

### 2. Update Configuration

```bash
# Edit secrets
kubectl create namespace customer-success-fte --dry-run=client -o yaml | kubectl apply -f -

# Update k8s/deployment.yaml with your image registry
# Update secrets in k8s/deployment.yaml
```

### 3. Deploy

```bash
# Apply all manifests
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/statefulset.yaml
kubectl apply -f k8s/monitoring.yaml

# Or apply in order
kubectl apply -f k8s/deployment.yaml  # Namespace, ConfigMaps, Secrets
kubectl apply -f k8s/statefulset.yaml  # PostgreSQL, Kafka
kubectl apply -f k8s/monitoring.yaml   # Monitoring (optional)

# Wait for StatefulSets to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n customer-success-fte --timeout=300s
kubectl wait --for=condition=ready pod -l app=kafka -n customer-success-fte --timeout=300s

# Deploy application
kubectl apply -f k8s/deployment.yaml
```

### 4. Verify Deployment

```bash
# Check all pods
kubectl get pods -n customer-success-fte

# Check services
kubectl get svc -n customer-success-fte

# Check HPA
kubectl get hpa -n customer-success-fte

# View logs
kubectl logs -f deployment/api-deployment -n customer-success-fte
kubectl logs -f deployment/worker-deployment -n customer-success-fte
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              customer-success-fte Namespace              │   │
│  │                                                          │   │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │   │
│  │  │     API     │    │   Worker    │    │  Scheduler  │  │   │
│  │  │  (x3-20)    │    │   (x2-50)   │    │     (x1)    │  │   │
│  │  │   HPA       │    │    HPA      │    │             │  │   │
│  │  └──────┬──────┘    └──────┬──────┘    └─────────────┘  │   │
│  │         │                  │                             │   │
│  │         └────────┬─────────┘                             │   │
│  │                  │                                       │   │
│  │         ┌────────▼─────────┐    ┌─────────────────────┐  │   │
│  │         │   Kafka          │    │    PostgreSQL       │  │   │
│  │         │   StatefulSet    │    │    StatefulSet      │  │   │
│  │         │   (9092)         │    │    (5432)           │  │   │
│  │         └────────┬─────────┘    └──────────┬──────────┘  │   │
│  │                  │                         │              │   │
│  └──────────────────┼─────────────────────────┼──────────────┘   │
│                     │                         │                  │
│  ┌──────────────────▼─────────────────────────▼──────────────┐   │
│  │                    Ingress (nginx)                         │   │
│  │                    api.your-domain.com                     │   │
│  └────────────────────────────────────────────────────────────┘   │
│                     │                                             │
└─────────────────────┼─────────────────────────────────────────────┘
                      │
                      ▼
                External Traffic
```

## Components

### Deployments

| Deployment | Min | Max | CPU | Memory | Description |
|------------|-----|-----|-----|--------|-------------|
| API | 3 | 20 | 250m-1000m | 512Mi-1Gi | FastAPI application |
| Worker | 2 | 50 | 500m-2000m | 1Gi-2Gi | Kafka message processor |
| Scheduler | 1 | 1 | 100m-500m | 256Mi-512Mi | Lifecycle scheduler |

### StatefulSets

| StatefulSet | Replicas | Storage | Description |
|-------------|----------|---------|-------------|
| PostgreSQL | 1 | 50Gi | CRM database |
| Kafka | 1 | 20Gi | Message broker |
| Zookeeper | 1 | 10Gi | Kafka coordination |

### Services

| Service | Type | Port | Description |
|---------|------|------|-------------|
| api-service | ClusterIP | 80 | Internal API access |
| postgres-service | ClusterIP (headless) | 5432 | Database |
| kafka-service | ClusterIP (headless) | 9092 | Kafka broker |

### HPA Configuration

**API:**
- Min: 3 pods
- Max: 20 pods
- Scale up at: 70% CPU, 80% memory
- Scale down stabilization: 300s

**Worker:**
- Min: 2 pods
- Max: 50 pods
- Scale up at: 70% CPU, 80% memory
- Aggressive scale up for message backlog

## Configuration

### Update Secrets

```bash
# Generate secure secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Update k8s/deployment.yaml secrets
# Or use sealed-secrets / external-secrets
kubectl create secret generic app-secrets \
  --from-literal=APP_DB_PASSWORD='secure-password' \
  --from-literal=APP_SECRET_KEY='secure-random-key' \
  --from-literal=APP_OPENAI_API_KEY='sk-...' \
  -n customer-success-fte \
  --dry-run=client -o yaml | kubectl apply -f -
```

### Update ConfigMap

```bash
kubectl edit configmap app-config -n customer-success-fte

# Rolling restart to apply changes
kubectl rollout restart deployment/api-deployment -n customer-success-fte
kubectl rollout restart deployment/worker-deployment -n customer-success-fte
```

## Scaling

### Manual Scaling

```bash
# Scale API
kubectl scale deployment/api-deployment --replicas=5 -n customer-success-fte

# Scale Worker
kubectl scale deployment/worker-deployment --replicas=10 -n customer-success-fte
```

### Auto-scaling (HPA)

HPA is configured and will automatically scale based on CPU/memory usage.

```bash
# View HPA status
kubectl get hpa -n customer-success-fte

# View HPA metrics
kubectl top pods -n customer-success-fte
```

## Monitoring

### Prometheus Metrics

Access Prometheus (if installed):
```bash
kubectl port-forward svc/prometheus-k8s -n monitoring 9090
```

Key metrics:
- `http_requests_total` - Request count
- `http_request_duration_seconds` - Latency
- `agent_metrics_tickets_created_total` - Tickets created
- `agent_metrics_escalations_total` - Escalations
- `kafka_consumer_group_lag` - Worker backlog

### Grafana Dashboard

Import the provided dashboard ConfigMap to Grafana.

### Logs

```bash
# API logs
kubectl logs -f deployment/api-deployment -n customer-success-fte

# Worker logs
kubectl logs -f deployment/worker-deployment -n customer-success-fte

# Search logs
kubectl logs deployment/api-deployment -n customer-success-fte | grep "error"
```

## Troubleshooting

### Pod Not Starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n customer-success-fte

# Check events
kubectl get events -n customer-success-fte --sort-by='.lastTimestamp'

# Check logs
kubectl logs <pod-name> -n customer-success-fte
```

### Database Connection Issues

```bash
# Test database connectivity
kubectl run test-db --rm -it --image=postgres:16 --restart=Never -n customer-success-fte \
  -- env PGPASSWORD=postgres psql -h postgres-service -U postgres -d customer_success_fte
```

### Kafka Connection Issues

```bash
# List Kafka topics
kubectl run test-kafka --rm -it --image=confluentinc/cp-kafka:7.5.0 --restart=Never -n customer-success-fte \
  -- kafka-topics --bootstrap-server kafka-service:9092 --list
```

### Check Resource Usage

```bash
kubectl top pods -n customer-success-fte
kubectl top nodes
```

## Backup and Restore

### Database Backup

```bash
# Create backup
kubectl run pg-backup --rm -it --image=postgres:16 --restart=Never -n customer-success-fte \
  -- env PGPASSWORD=postgres pg_dump -h postgres-service -U postgres customer_success_fte > backup.sql

# Restore from backup
kubectl run pg-restore --rm -it --image=postgres:16 --restart=Never -n customer-success-fte \
  -- env PGPASSWORD=postgres psql -h postgres-service -U postgres customer_success_fte < backup.sql
```

## Security

### Network Policies

Network policies restrict pod-to-pod communication:
- API can only be accessed from ingress
- Workers can only connect to database and Kafka
- Database and Kafka only accept connections from application pods

### Secrets Management

For production, consider:
- HashiCorp Vault
- AWS Secrets Manager
- Azure Key Vault
- GCP Secret Manager
- Sealed Secrets (Bitnami)

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy to Kubernetes

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build and push API
        run: |
          docker build -t registry/api:${{ github.sha }} .
          docker push registry/api:${{ github.sha }}
      
      - name: Build and push Worker
        run: |
          docker build -f Dockerfile.worker -t registry/worker:${{ github.sha }} .
          docker push registry/worker:${{ github.sha }}
      
      - name: Deploy to Kubernetes
        run: |
          kubectl apply -f k8s/deployment.yaml
          kubectl set image deployment/api-deployment api=registry/api:${{ github.sha }} -n customer-success-fte
          kubectl set image deployment/worker-deployment worker=registry/worker:${{ github.sha }} -n customer-success-fte
          kubectl rollout restart deployment/api-deployment -n customer-success-fte
          kubectl rollout restart deployment/worker-deployment -n customer-success-fte
```

## Cleanup

```bash
# Delete all resources
kubectl delete -f k8s/monitoring.yaml
kubectl delete -f k8s/statefulset.yaml
kubectl delete -f k8s/deployment.yaml

# Delete namespace (removes everything)
kubectl delete namespace customer-success-fte

# Delete PVCs (data will be lost!)
kubectl delete pvc -n customer-success-fte --all
```

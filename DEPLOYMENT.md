# 🚀 CNC Telemetry Box - Deployment Guide

## 📋 OVERVIEW

Guide completo para deploy do CNC Telemetry Box v2.0 em ambiente de produção com arquitetura microservices.

---

## 🏗️ ARQUITETURA DE DEPLOYMENT

### **Serviços**
- **Backend API** (port 8001) - API principal
- **Telemetry Service** (port 8002) - Microservice de telemetria
- **Status Service** (port 8003) - Microservice de status
- **Frontend** (port 80) - React app
- **PostgreSQL** (port 5432) - Database
- **Redis** (port 6379) - Message queue
- **Prometheus** (port 9090) - Monitoring
- **Grafana** (port 3000) - Dashboards

---

## 🐳 DOCKER DEPLOYMENT

### **1. Pré-requisitos**
```bash
# Docker & Docker Compose
docker --version
docker-compose --version

# Espaço em disco
df -h  # Mínimo 10GB disponível

# Memória RAM
free -h  # Mínimo 4GB RAM
```

### **2. Environment Setup**
```bash
# Criar .env
cat > .env << EOF
# Database
POSTGRES_USER=cncbox
POSTGRES_PASSWORD=senha_segura_123
POSTGRES_DB=cnc_telemetry
DATABASE_URL=postgresql://cncbox:senha_segura_123@db:5432/cnc_telemetry

# Redis
REDIS_URL=redis://redis:6379/0

# API
API_HOST=0.0.0.0
API_PORT=8001
LOG_LEVEL=INFO

# Frontend
VITE_API_BASE=http://localhost:8001
VITE_TELEMETRY_SERVICE=http://localhost:8002
VITE_STATUS_SERVICE=http://localhost:8003

# Monitoring
GRAFANA_PASSWORD=admin_seguro_123
EOF
```

### **3. Build & Deploy**
```bash
# Build all services
docker-compose build

# Start production
docker-compose up -d

# Verify deployment
docker-compose ps
```

### **4. Health Checks**
```bash
# Backend API
curl http://localhost:8001/box/healthz

# Telemetry Service
curl http://localhost:8002/health

# Status Service  
curl http://localhost:8003/health

# Frontend
curl http://localhost:80

# Services status
docker-compose exec backend python -c "from backend.app.db import engine; print('DB OK')"
```

---

## 🌐 KUBERNETES DEPLOYMENT

### **1. Namespace & Config**
```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cnc-telemetry
---
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cnc-config
  namespace: cnc-telemetry
data:
  DATABASE_URL: "postgresql://cncbox:senha@postgres:5432/cnc_telemetry"
  REDIS_URL: "redis://redis:6379/0"
  LOG_LEVEL: "INFO"
```

### **2. Database Deployment**
```yaml
# postgres-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: cnc-telemetry
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:16-alpine
        env:
        - name: POSTGRES_USER
          value: "cncbox"
        - name: POSTGRES_PASSWORD
          value: "senha_segura_123"
        - name: POSTGRES_DB
          value: "cnc_telemetry"
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: postgres-pvc
---
# postgres-pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: cnc-telemetry
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 20Gi
```

### **3. Redis Deployment**
```yaml
# redis-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: cnc-telemetry
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        volumeMounts:
        - name: redis-storage
          mountPath: /data
      volumes:
      - name: redis-storage
        persistentVolumeClaim:
          claimName: redis-pvc
---
# redis-pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-pvc
  namespace: cnc-telemetry
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
```

### **4. Backend Services**
```yaml
# backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: cnc-telemetry
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: cnc-telemetry/backend:latest
        envFrom:
        - configMapRef:
            name: cnc-config
        ports:
        - containerPort: 8001
        livenessProbe:
          httpGet:
            path: /box/healthz
            port: 8001
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /box/healthz
            port: 8001
          initialDelaySeconds: 5
          periodSeconds: 5
---
# backend-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: backend-service
  namespace: cnc-telemetry
spec:
  selector:
    app: backend
  ports:
  - port: 8001
    targetPort: 8001
  type: ClusterIP
```

### **5. Microservices**
```yaml
# telemetry-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: telemetry-service
  namespace: cnc-telemetry
spec:
  replicas: 2
  selector:
    matchLabels:
      app: telemetry-service
  template:
    metadata:
      labels:
        app: telemetry-service
    spec:
      containers:
      - name: telemetry
        image: cnc-telemetry/telemetry:latest
        envFrom:
        - configMapRef:
            name: cnc-config
        ports:
        - containerPort: 8002
---
# telemetry-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: telemetry-service
  namespace: cnc-telemetry
spec:
  selector:
    app: telemetry-service
  ports:
  - port: 8002
    targetPort: 8002
  type: ClusterIP
```

### **6. Deploy Commands**
```bash
# Apply all configs
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f postgres-deployment.yaml
kubectl apply -f postgres-pvc.yaml
kubectl apply -f redis-deployment.yaml
kubectl apply -f redis-pvc.yaml
kubectl apply -f backend-deployment.yaml
kubectl apply -f backend-service.yaml
kubectl apply -f telemetry-deployment.yaml
kubectl apply -f telemetry-service.yaml

# Check deployment
kubectl get pods -n cnc-telemetry
kubectl get services -n cnc-telemetry

# Check logs
kubectl logs -f deployment/backend -n cnc-telemetry
```

---

## 🔧 CONFIGURAÇÃO DE PRODUÇÃO

### **1. Security**
```bash
# SSL/TLS
# Usar NGINX Ingress Controller
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: cnc-ingress
  namespace: cnc-telemetry
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - api.cnc-telemetry.com
    secretName: cnc-tls
  rules:
  - host: api.cnc-telemetry.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: backend-service
            port:
              number: 8001
```

### **2. Resource Limits**
```yaml
# resource-limits.yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: cnc-limits
  namespace: cnc-telemetry
spec:
  limits:
  - default:
      cpu: "500m"
      memory: "512Mi"
    defaultRequest:
      cpu: "100m"
      memory: "128Mi"
    type: Container
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: cnc-quota
  namespace: cnc-telemetry
spec:
  hard:
    requests.cpu: "2"
    requests.memory: "4Gi"
    limits.cpu: "4"
    limits.memory: "8Gi"
```

### **3. Autoscaling**
```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: cnc-telemetry
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

## 📊 MONITORAMENTO

### **1. Prometheus Configuration**
```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'cnc-backend'
    static_configs:
      - targets: ['backend:8001']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'cnc-telemetry'
    static_configs:
      - targets: ['telemetry-service:8002']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'cnc-status'
    static_configs:
      - targets: ['status-service:8003']
    metrics_path: '/metrics'
    scrape_interval: 5s
```

### **2. Grafana Dashboards**
```json
{
  "dashboard": {
    "title": "CNC Telemetry Overview",
    "panels": [
      {
        "title": "API Requests",
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
      },
      {
        "title": "Error Rate",
        "type": "singlestat",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m]) / rate(http_requests_total[5m]) * 100",
            "legendFormat": "Error %"
          }
        ]
      }
    ]
  }
}
```

---

## 🔐 SECURITY

### **1. Network Policies**
```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: cnc-network-policy
  namespace: cnc-telemetry
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
  - from:
    - podSelector:
        matchLabels:
          app: backend
    - podSelector:
        matchLabels:
          app: telemetry-service
    - podSelector:
        matchLabels:
          app: status-service
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
```

### **2. Secrets Management**
```bash
# Create secrets
kubectl create secret generic cnc-secrets \
  --from-literal=postgres-password=senha_segura_123 \
  --from-literal=redis-password=redis_seguro_456 \
  --namespace=cnc-telemetry

# Use in deployments
env:
- name: POSTGRES_PASSWORD
  valueFrom:
    secretKeyRef:
      name: cnc-secrets
      key: postgres-password
```

---

## 🔄 CI/CD PIPELINE

### **GitHub Actions**
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: |
        pip install -r backend/requirements.txt
    - name: Run tests
      run: python run_all_tests.py

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Build Docker images
      run: |
        docker-compose build
    - name: Push to registry
      run: |
        docker-compose push

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
    - name: Deploy to Kubernetes
      run: |
        kubectl apply -f k8s/
        kubectl rollout status deployment/backend -n cnc-telemetry
```

---

## 🚨 TROUBLESHOOTING

### **Common Issues**

**Pods not starting**
```bash
# Check events
kubectl get events -n cnc-telemetry --sort-by='.lastTimestamp'

# Check logs
kubectl logs -f deployment/backend -n cnc-telemetry

# Describe pod
kubectl describe pod <pod-name> -n cnc-telemetry
```

**Database connection issues**
```bash
# Test connection
kubectl exec -it deployment/postgres -n cnc-telemetry -- psql -U cncbox -d cnc_telemetry

# Check service
kubectl get svc postgres -n cnc-telemetry
```

**High memory usage**
```bash
# Check resource usage
kubectl top pods -n cnc-telemetry

# Scale up
kubectl scale deployment backend --replicas=5 -n cnc-telemetry
```

**Performance issues**
```bash
# Check metrics
curl http://localhost:9090/api/v1/query?query=rate(http_requests_total[5m])

# Check logs
kubectl logs -f deployment/backend -n cnc-telemetry | grep ERROR
```

---

## 📈 PERFORMANCE TUNING

### **Database Optimization**
```sql
-- PostgreSQL performance settings
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;

-- Create indexes
CREATE INDEX CONCURRENTLY idx_telemetry_machine_timestamp 
ON telemetry(machine_id, timestamp DESC);

CREATE INDEX CONCURRENTLY idx_events_machine_timestamp 
ON events(machine_id, timestamp DESC);
```

### **Application Tuning**
```python
# Connection pool settings
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600
)

# Redis connection
redis_pool = aioredis.ConnectionPool.from_url(
    REDIS_URL,
    max_connections=20,
    retry_on_timeout=True
)
```

---

## 🎯 PRODUCTION CHECKLIST

### **Before Deployment**
- [ ] Environment variables configured
- [ ] Secrets created and secured
- [ ] Database migrations applied
- [ ] SSL certificates installed
- [ ] Monitoring dashboards ready
- [ ] Alert rules configured
- [ ] Backup procedures tested
- [ ] Disaster recovery plan documented

### **After Deployment**
- [ ] Health checks passing
- [ ] Load testing completed
- [ ] Monitoring alerts working
- [ ] Log aggregation configured
- [ ] Security scans passed
- [ ] Performance benchmarks met
- [ ] Documentation updated
- [ ] Team training completed

---

## 📞 SUPPORT

### **Emergency Contacts**
- **DevOps Team**: devops@cnc-telemetry.com
- **Development Team**: dev@cnc-telemetry.com
- **Infrastructure Team**: infra@cnc-telemetry.com

### **Monitoring Dashboards**
- **Grafana**: http://grafana.cnc-telemetry.com
- **Prometheus**: http://prometheus.cnc-telemetry.com
- **Kubernetes**: k8s.cnc-telemetry.com

### **Runbooks**
- **Database Issues**: docs/runbooks/database.md
- **Performance**: docs/runbooks/performance.md
- **Security**: docs/runbooks/security.md
- **Backup/Restore**: docs/runbooks/backup.md

---

**🚀 CNC Telemetry Box - Production Ready!**

*Deploy com confiança, monitore continuamente, itere rapidamente.*

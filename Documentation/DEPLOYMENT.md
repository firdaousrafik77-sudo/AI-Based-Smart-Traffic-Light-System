# Deployment Guide

## Local Development

### Quick Start
```bash
python run.py
```

The server will start on http://localhost:3000

### Manual Setup
```bash
# Install dependencies
pip install -r backend/requirements.txt

# Configure environment (optional)
cp .env.example .env
# Edit .env as needed

# Run the backend
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 3000
```

Access the system:
- Frontend: http://localhost:3000/
- API Docs: http://localhost:3000/docs
- WebSocket: ws://localhost:3000/ws

## Docker Deployment

### Single Container
```bash
docker build -t smart-traffic .
docker run -p 3000:3000 smart-traffic
```

### Docker Compose
```bash
docker-compose up -d
```

To stop:
```bash
docker-compose down
```

View logs:
```bash
docker-compose logs -f traffic-control
```

### Environment Variables
```bash
docker run -p 3000:3000 \
  -e PORT=3000 \
  -e DEBUG=False \
  -e LOG_LEVEL=INFO \
  smart-traffic
```

## Production Deployment

### Using Gunicorn + Nginx

1. **Install dependencies**
```bash
pip install gunicorn gevent gevent-websocket
```

2. **Create gunicorn config** (`gunicorn_config.py`)
```python
bind = "0.0.0.0:3000"
workers = 4
worker_class = "gevent"
timeout = 120
keepalive = 5
```

3. **Start with Gunicorn**
```bash
gunicorn -c gunicorn_config.py backend.main:app
```

4. **Setup Nginx** (optional, for reverse proxy)
```nginx
upstream traffic_app {
    server 127.0.0.1:3000;
}

server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://traffic_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws {
        proxy_pass http://traffic_app/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Systemd Service

Create `/etc/systemd/system/smart-traffic.service`:

```ini
[Unit]
Description=Smart Traffic Control System
After=network.target

[Service]
Type=notify
User=traffic
WorkingDirectory=/opt/smart_traffic_system
Environment="PATH=/opt/smart_traffic_system/venv/bin"
ExecStart=/opt/smart_traffic_system/venv/bin/python /opt/smart_traffic_system/run.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable smart-traffic
sudo systemctl start smart-traffic
sudo systemctl status smart-traffic
```

View logs:
```bash
sudo journalctl -u smart-traffic -f
```

## Cloud Deployment

### AWS Elastic Beanstalk

1. **Create `.ebextensions/traffic.config`**
```yaml
option_settings:
  aws:elasticbeanstalk:application:environment:
    PYTHONPATH: /var/app/current/backend:$PYTHONPATH
  aws:autoscaling:launchconfiguration:
    InstanceType: t3.micro
    RootVolumeSize: 30

commands:
  01_install_deps:
    command: pip install -r backend/requirements.txt
```

2. **Deploy**
```bash
eb init
eb create smart-traffic-env
eb deploy
```

### Azure App Service

```bash
az appservice plan create \
  --name traffic-plan \
  --resource-group mygroup \
  --sku B1 \
  --is-linux

az webapp create \
  --resource-group mygroup \
  --plan traffic-plan \
  --name smart-traffic-app \
  --runtime "PYTHON|3.10"

az webapp deployment source config-zip \
  --resource-group mygroup \
  --name smart-traffic-app \
  --src-path app.zip
```

### Kubernetes (K8s)

Create `k8s-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: smart-traffic
spec:
  replicas: 2
  selector:
    matchLabels:
      app: smart-traffic
  template:
    metadata:
      labels:
        app: smart-traffic
    spec:
      containers:
      - name: traffic-app
        image: smart-traffic:latest
        ports:
        - containerPort: 3000
        env:
        - name: LOG_LEVEL
          value: INFO
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /api/state
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/state
            port: 3000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: smart-traffic-svc
spec:
  selector:
    app: smart-traffic
  ports:
  - protocol: TCP
    port: 80
    targetPort: 3000
  type: LoadBalancer
```

Deploy:
```bash
kubectl apply -f k8s-deployment.yaml
```

## Performance Tuning

### Database Optimization
```python
# Run maintenance periodically
from backend.database import TrafficDatabase
db = TrafficDatabase()
db.cleanup_old_data(days=7)  # Keep 7 days of data
```

### ML Model Optimization
```env
# Reduce training samples for faster startup
ML_TRAINING_SAMPLES=2000

# Adjust history window
ML_HISTORY_WINDOW=5
```

### Traffic Simulation Tuning
```env
# Increase spawn rates for higher traffic
SPAWN_RATE_NORMAL=2

# Longer green lights = faster throughput
MAX_GREEN_DURATION=50
```

## Monitoring and Logging

### Log Levels
```env
LOG_LEVEL=DEBUG    # Verbose
LOG_LEVEL=INFO     # Standard (recommended)
LOG_LEVEL=WARNING  # Only issues
LOG_LEVEL=ERROR    # Only errors
```

### Monitor Metrics Endpoint
```bash
watch -n 1 'curl -s http://localhost:3000/api/metrics | jq'
```

### Database Health
```bash
sqlite3 traffic_system.db ".tables"
sqlite3 traffic_system.db "SELECT COUNT(*) as records FROM traffic_data;"
```

## Backup & Recovery

### Backup Database
```bash
cp traffic_system.db traffic_system.db.backup
# Or with timestamp:
cp traffic_system.db traffic_system.db.$(date +%Y%m%d_%H%M%S).backup
```

### Export Data
```bash
sqlite3 traffic_system.db ".mode csv" ".output traffic_history.csv" "SELECT * FROM traffic_data;"
```

### Automated Backup
```bash
# Create backup script
#!/bin/bash
BACKUP_DIR="/backups/traffic"
mkdir -p $BACKUP_DIR
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
cp /app/traffic_system.db $BACKUP_DIR/traffic_system.db.$TIMESTAMP

# Add to crontab (daily backup)
0 2 * * * /scripts/backup_traffic.sh
```

## Troubleshooting Deployment

### Port Issues
```bash
# Check if port is in use
lsof -i :3000

# Kill process on port
kill -9 $(lsof -t -i :3000)
```

### Database Lock Issues
```bash
# Remove lock file
rm traffic_system.db-shm
rm traffic_system.db-wal
```

### Memory Issues
```bash
# Monitor memory usage
watch -n 1 'free -h'

# Reduce ML training samples
# Edit .env: ML_TRAINING_SAMPLES=1000
```

### WebSocket Connection Issues
```javascript
// Check WebSocket connection
const ws = new WebSocket('wss://your-domain.com/ws');
ws.onerror = () => console.log('Connection failed');
```

## Health Checks

### Manual Health Check
```bash
curl http://localhost:3000/api/state
curl http://localhost:3000/docs
```

### Automated Monitoring
```bash
# Check every 30 seconds
watch -n 30 'curl -s http://localhost:3000/api/state | jq .state'
```

## Scaling Notes

- **Single Server**: Up to ~100 requests/second
- **Multiple Servers**: Use load balancer + shared database
- **Database**: SQLite suitable for single server; use PostgreSQL for multi-server
- **WebSocket**: Sticky sessions required for multi-server setup

---

For more details, see [README.md](README.md)

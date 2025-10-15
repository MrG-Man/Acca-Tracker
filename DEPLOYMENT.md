# 🚀 Football Predictions App - Deployment Guide

## Table of Contents
- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Deployment Methods](#deployment-methods)
- [Configuration](#configuration)
- [Monitoring](#monitoring)
- [Backup & Recovery](#backup--recovery)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Using Docker (Recommended)
```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your settings

# 2. Deploy with Docker Compose
docker-compose up -d

# 3. Check logs
docker-compose logs -f web
```

### Using Shell Script
```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your settings

# 2. Run deployment script
chmod +x deploy.sh
./deploy.sh production
```

## Prerequisites

### System Requirements
- **Python 3.11+**
- **4GB RAM** (minimum)
- **10GB Storage** (minimum)
- **Linux/macOS/Windows** (Docker recommended for Windows)

### Required Services
- **Internet connection** (for API calls and updates)
- **Domain name** (optional, for production)

### API Keys Required
- **Sofascore API Key** (from RapidAPI)

## Environment Setup

### 1. Clone and Setup
```bash
git clone <your-repo-url>
cd football-predictions
```

### 2. Configure Environment
```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
nano .env  # or use your preferred editor
```

### 3. Required Environment Variables

#### Essential Settings
```bash
# Flask Configuration
SECRET_KEY=your-super-secret-key-here
FLASK_ENV=production

# Server Settings
HOST=0.0.0.0
PORT=5000

# API Keys
SOFASCORE_API_KEY=your-rapidapi-key-here
RAPIDAPI_HOST=sofascore.p.rapidapi.com
```

#### Optional Settings
```bash
# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# Security
CORS_ORIGINS=https://yourdomain.com
RATE_LIMIT_PER_MINUTE=60

# Backup
BACKUP_ENABLED=True
BACKUP_RETENTION_DAYS=30
```

## Deployment Methods

### Method 1: Docker Compose (Recommended)

#### Production Deployment
```bash
# Build and start
docker-compose -f docker-compose.yml up -d --build

# Check status
docker-compose ps

# View logs
docker-compose logs -f web

# Scale (if needed)
docker-compose up -d --scale web=3
```

#### Development Deployment
```bash
# For development with live reload
docker-compose -f docker-compose.dev.yml up
```

### Method 2: Manual Deployment

#### Using Deployment Script
```bash
# Make script executable
chmod +x deploy.sh

# Deploy for production
./deploy.sh production

# Deploy for development
./deploy.sh development
```

#### Manual Steps
```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create necessary directories
mkdir -p logs data/backups

# 4. Start application
# Development
python app.py

# Production (with gunicorn)
gunicorn --config gunicorn.conf.py app:app
```

### Method 3: Systemd Service (Linux)

#### Create Service File
```bash
sudo tee /etc/systemd/system/football-predictions.service > /dev/null <<EOF
[Unit]
Description=Football Predictions App
After=network.target

[Service]
Type=simple
User=football
Group=football
WorkingDirectory=/path/to/your/app
EnvironmentFile=/path/to/your/app/.env
ExecStart=/path/to/your/app/venv/bin/gunicorn --config gunicorn.conf.py app:app
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=3

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/path/to/your/app/logs /path/to/your/app/data

[Install]
WantedBy=multi-user.target
EOF
```

#### Manage Service
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable football-predictions
sudo systemctl start football-predictions

# Check status
sudo systemctl status football-predictions

# View logs
sudo journalctl -u football-predictions -f
```

## Configuration

### Production Settings

#### Flask Configuration
```python
# In config.py
class ProductionConfig(Config):
    DEBUG = False
    LOG_LEVEL = 'WARNING'
    SECRET_KEY = os.getenv('SECRET_KEY')  # Must be set
```

#### Gunicorn Settings
```python
# In gunicorn.conf.py
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
timeout = 30
max_requests = 1000
```

### Security Configuration

#### Rate Limiting
- **Default**: 60 requests per minute per IP
- **Configurable** via `RATE_LIMIT_PER_MINUTE` environment variable
- **Endpoints** with different limits can be set in the code

#### CORS Settings
- **Development**: Allows localhost origins
- **Production**: Set `CORS_ORIGINS` to your domain(s)

#### API Security
- API keys loaded from environment variables
- No hard-coded secrets in source code
- Input validation and sanitization

## Monitoring

### Health Checks
```bash
# Health check endpoint
curl http://localhost:5000/health

# Response format
{
    "status": "healthy",
    "timestamp": "2024-01-01T12:00:00",
    "version": "1.0.0",
    "services": {
        "bbc_scraper": true,
        "sofascore_api": true,
        "data_manager": true
    }
}
```

### Application Metrics
```bash
# Metrics endpoint (if enabled)
curl http://localhost:5000/metrics

# Includes API usage, cache statistics, system info
```

### Log Monitoring
```bash
# View application logs
tail -f logs/app.log

# View access logs
tail -f logs/access.log

# Docker logs
docker-compose logs -f web
```

### System Monitoring
```bash
# Check resource usage
docker stats

# Monitor processes
htop

# Check disk usage
df -h
```

## Backup & Recovery

### Automated Backups
```bash
# Run backup script
chmod +x backup.sh
./backup.sh backup

# List available backups
./backup.sh list

# Restore from backup
./backup.sh restore backup_20240101_120000

# Cleanup old backups
./backup.sh cleanup
```

### Manual Backup
```bash
# Create backup directory
BACKUP_DIR="data/backups/backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Copy data
cp -r data/selections "$BACKUP_DIR/"
cp -r data/fixtures "$BACKUP_DIR/"

# Create metadata
cat > "$BACKUP_DIR/backup_metadata.json" << EOF
{
    "backup_date": "$(date -Iseconds)",
    "version": "1.0.0"
}
EOF
```

### Recovery Process
```bash
# 1. Stop application
sudo systemctl stop football-predictions

# 2. Restore data
cp -r backup_directory/data/* data/

# 3. Set proper permissions
sudo chown -R football:football data/

# 4. Start application
sudo systemctl start football-predictions
```

## Troubleshooting

### Common Issues

#### Application Won't Start
```bash
# Check logs
tail -f logs/app.log

# Check environment variables
./deploy.sh development

# Verify dependencies
pip list
```

#### API Connection Issues
```bash
# Test API connectivity
curl -H "X-RapidAPI-Key: $SOFASCORE_API_KEY" \
     "https://sofascore.p.rapidapi.com/categories/list"

# Check API key in .env
grep SOFASCORE_API_KEY .env
```

#### Database Issues (Future)
```bash
# Check database connection
python -c "from app import db; print(db.engine)"

# Run migrations
python manage.py db upgrade
```

#### Performance Issues
```bash
# Check resource usage
docker stats

# Monitor API usage
curl http://localhost:5000/metrics

# Check cache efficiency
python -c "from sofascore_optimized import SofascoreLiveScoresAPI; api = SofascoreLiveScoresAPI(); api.print_stats()"
```

### Debug Mode

#### Enable Debug Logging
```bash
# Set in .env
LOG_LEVEL=DEBUG

# Or run with debug
FLASK_ENV=development python app.py
```

#### Test Endpoints
```bash
# Test health endpoint
curl http://localhost:5000/health

# Test BTTS tracker
curl http://localhost:5000/api/btts-status-test

# Test admin interface
open http://localhost:5000/admin
```

### Emergency Procedures

#### Quick Restart
```bash
# Docker
docker-compose restart web

# Systemd
sudo systemctl restart football-predictions

# Manual
pkill -f gunicorn
gunicorn --config gunicorn.conf.py app:app
```

#### Data Recovery
```bash
# From latest backup
./backup.sh list
./backup.sh restore <latest-backup-name>

# From specific backup
./backup.sh restore backup_20240101_120000
```

## Security Best Practices

### Production Security
1. **Use strong SECRET_KEY**
2. **Set proper file permissions**
3. **Use HTTPS in production**
4. **Keep API keys secure**
5. **Regular security updates**

### File Permissions
```bash
# Set proper permissions
chmod 644 requirements.txt .env.example
chmod 600 .env
chmod 755 deploy.sh backup.sh
chmod -R 755 logs/ data/
```

### Firewall Configuration
```bash
# Allow only necessary ports
sudo ufw allow 5000
sudo ufw allow 80
sudo ufw allow 443

# Enable firewall
sudo ufw enable
```

## Performance Optimization

### Memory Optimization
- **Gunicorn workers**: `CPU cores * 2 + 1`
- **Worker connections**: 1000 (default)
- **Max requests per worker**: 1000

### Cache Optimization
- **BBC scraper cache**: 72 hours
- **Sofascore API cache**: 3 minutes for live data
- **Memory cache**: 5 minutes for frequent data

### Database Optimization (Future)
- **Connection pooling**
- **Query optimization**
- **Regular maintenance**

## Support

### Getting Help
1. Check the logs: `tail -f logs/app.log`
2. Verify configuration: `cat .env | grep -v SECRET_KEY`
3. Test health endpoint: `curl http://localhost:5000/health`
4. Check system resources: `docker stats` or `htop`

### Common Commands Reference
```bash
# Deployment
docker-compose up -d
./deploy.sh production

# Monitoring
docker-compose logs -f
curl http://localhost:5000/health

# Backup
./backup.sh backup
./backup.sh list

# Maintenance
docker-compose restart
sudo systemctl reload football-predictions
```

---

**Last Updated**: January 2024
**Version**: 1.0.0
# Setup Guide

## Environment Setup

### 1. Install Dependencies
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Unix
# or
.\venv\Scripts\activate  # Windows

# Install requirements
pip3 install -r requirements.txt
playwright install chromium
```

### 2. Configure Environment (.env)
```bash
# Create from example
cp .env.example .env

# Edit with your values:
# Database
MONGODB_URL=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/<database>
DATABASE_URL=${MONGODB_URL}

# Notifications  
TELEGRAM_BOT_TOKEN=<your_bot_token>  # From @BotFather
TELEGRAM_CHAT_ID=<your_chat_id>      # From @userinfobot

# Cache
REDIS_URL=redis://<username>:<password>@<host>:<port>
```

### 3. Start Services
```bash
# API Server (Terminal 1)
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Dashboard (Terminal 2)  
streamlit run src/dashboard/main.py --server.port 8501

# Background Workers (Terminal 3)
celery -A src.workers.celery_app worker --loglevel=info
```

### 4. Verify Setup
```bash
# Test database connection
python3 scripts/test_db_connection.py

# Test Telegram notification
python3 scripts/test_telegram.py
```

### 5. Configure Telegram Webhook
See [Webhook Setup](webhook-setup.md) for detailed instructions.

## Production Setup

For production deployment, see [Deployment Guide](deployment-guide.md).

### Additional Configuration

#### MongoDB Collections
Collections are created automatically with proper indexes:
- `products`: Stores product data
  - Indexes: EAN, ASIN, updated_at
- `price_alerts`: User price monitoring
  - Indexes: user_id, product_id, created_at
- `keepa_data`: Historical prices
  - Indexes: asin, timestamp
- `scraping_sessions`: Job tracking
  - Indexes: status, started_at

#### Service Ports
- FastAPI: 8000 (API endpoints)
- Streamlit: 8501 (Dashboard)
- Flower: 5555 (Celery monitoring)
- Prometheus: 9090 (Metrics)
- Grafana: 3000 (Dashboards)

#### Security Notes
- Use strong passwords for all services
- Keep .env file secure and never commit to VCS
- Rotate API keys regularly
- Use separate credentials for development/production
- See [Security Guide](security.md) for best practices

#### Monitoring Setup
- Enable health checks
- Configure logging
- Set up alerts
- Monitor system resources
- See [Monitoring Guide](monitoring.md) for details

## Troubleshooting

See [Troubleshooting Guide](troubleshooting.md) for common issues and solutions.

## Next Steps

1. Review [Security Guide](security.md)
2. Configure monitoring
3. Set up production deployment
4. Enable authentication
5. Configure backup system 
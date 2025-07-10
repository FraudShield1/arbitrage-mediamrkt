# Setup Guide

## Environment Setup

### 1. Install Dependencies
```bash
pip3 install motor pymongo fastapi uvicorn streamlit celery redis asyncpg playwright
playwright install chromium
```

### 2. Configure Environment (.env)
```bash
# Database
MONGODB_URL=mongodb+srv://shemsybot:***@cluster0.7i47zbl.mongodb.net/arbitrage_tool
DATABASE_URL=${MONGODB_URL}

# Notifications  
TELEGRAM_BOT_TOKEN=7777704395:AAG_wk5PEgVPPcCP3KTm_D-2NbwSWwnrHqo
TELEGRAM_CHAT_ID=6008126687

# Cache
REDIS_URL=redis://default:***@redis-15535.c15.us-east-1-2.ec2.redns.redis-cloud.com:15535
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
python3 -c "
import asyncio
from src.config.database import check_database_connection
print('Database OK:', asyncio.run(check_database_connection()))
"

# Test Telegram notification
python3 -c "
import asyncio
from src.services.notifications import send_telegram_notification
print('Telegram OK:', asyncio.run(send_telegram_notification('Test', 'Setup complete')))
"
```

### 5. Configure Telegram Webhook (Optional)
```bash
# Install ngrok for local development
brew install ngrok  # macOS
# or
snap install ngrok  # Ubuntu

# Start ngrok tunnel
ngrok http 8000

# Configure webhook URL
python3 src/utils/setup_telegram_webhook.py

# Verify webhook setup
curl -X GET https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo
```

See [Webhook Setup](webhook-setup.md) for detailed configuration and usage.

## Production Deployment

### Docker (Recommended)
```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Health check
curl http://localhost:8000/health
```

### Manual Deployment
1. Set production environment variables
2. Configure reverse proxy (Nginx)
3. Set up systemd services for auto-restart
4. Configure SSL certificates

## Configuration Details

### MongoDB Collections (Auto-created)
- `products` - Product data with ASIN, EAN, pricing
- `price_alerts` - User-defined price monitoring  
- `keepa_data` - Historical price data
- `scraping_sessions` - Job tracking and results

### Service Ports
- **FastAPI**: 8000 (API endpoints)
- **Streamlit**: 8501 (Dashboard)
- **Flower**: 5555 (Celery monitoring)
- **Prometheus**: 9090 (Metrics)
- **Grafana**: 3000 (Dashboards)

### Key Endpoints
- `http://localhost:8000/health` - API health check
- `http://localhost:8000/docs` - API documentation
- `http://localhost:8501` - Dashboard interface
- `http://localhost:5555` - Task monitoring 
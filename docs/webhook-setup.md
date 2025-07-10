# Telegram Webhook Integration

## Overview
The system supports bi-directional communication with Telegram through webhooks, enabling real-time responses to user commands and interactions.

## Setup Process

### 1. Prerequisites
- Ngrok installed for local development
- Telegram Bot Token configured in environment
- FastAPI backend running on port 8000

### 2. Webhook Configuration
```bash
# Start ngrok tunnel (Terminal 1)
ngrok http 8000

# Configure webhook URL (Terminal 2)
python src/utils/setup_telegram_webhook.py
```

### 3. Environment Variables
```bash
# Existing variables
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# New webhook-specific variables (optional)
WEBHOOK_BASE_URL=https://your-domain.com  # Production only
```

## Webhook Endpoints

### Main Webhook (`/webhooks/telegram`)
- **Method**: POST
- **Purpose**: Receives updates from Telegram
- **Authentication**: Validates Telegram token
- **Response Time**: < 2 seconds (Telegram requirement)

## Supported Commands

| Command | Description | Example |
|---------|-------------|---------|
| /start | Initialize bot interaction | `/start` |
| /help | Display available commands | `/help` |
| /status | Check monitoring status | `/status` |
| /chart | Get price history chart | `/chart [product_id]` |

## Error Handling
- Invalid token validation
- Malformed update objects
- Command processing timeouts
- Rate limiting protection

## Production Deployment
1. Replace ngrok with proper reverse proxy (nginx)
2. Configure SSL certificates
3. Set WEBHOOK_BASE_URL environment variable
4. Update webhook URL using setup script

## Monitoring
- Webhook endpoint health checks
- Command processing metrics
- Error rate tracking
- Response time monitoring

## Security Considerations
- Token validation on all requests
- Rate limiting per chat ID
- IP whitelist for Telegram servers
- SSL/TLS encryption required

## Troubleshooting

### Common Issues
1. Webhook not receiving updates
   - Verify ngrok/domain is accessible
   - Check SSL certificate validity
   - Confirm webhook URL registration

2. Slow response times
   - Monitor command processing duration
   - Check database query performance
   - Verify async handler efficiency

3. Failed message delivery
   - Validate chat ID configuration
   - Check bot permissions
   - Verify network connectivity

### Debug Tools
```bash
# Check webhook status
curl -X GET https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo

# Test webhook endpoint
curl -X POST http://localhost:8000/webhooks/telegram \
  -H "Content-Type: application/json" \
  -d '{"update_id": 1, "message": {"text": "/status"}}'
``` 
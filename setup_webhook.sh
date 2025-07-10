#!/bin/bash

# Telegram Webhook Setup Script
# Run this AFTER your API service is deployed on Render

# Replace these with your actual values
API_URL="https://your-api-service-name.onrender.com"
BOT_TOKEN="your_bot_token_here"
WEBHOOK_SECRET="your_webhook_secret_here"

echo "Setting up Telegram webhook..."
echo "API URL: $API_URL"

# Set the webhook
curl -F "url=$API_URL/webhooks/telegram" \
     -F "secret_token=$WEBHOOK_SECRET" \
     https://api.telegram.org/bot$BOT_TOKEN/setWebhook

echo ""
echo "Webhook setup complete!"
echo "Your bot should now receive updates at: $API_URL/webhooks/telegram" 
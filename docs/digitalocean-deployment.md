# DigitalOcean Deployment Guide

## Prerequisites

1. DigitalOcean account
2. Docker and Docker Compose installed on your local machine
3. MongoDB Atlas account (for database)
4. Redis Cloud account (optional, can use local Redis)
5. Telegram Bot token and chat ID

## Step 1: SSH Key Setup

1. Check for existing SSH keys:
```bash
ls -la ~/.ssh
```

2. If you don't have an SSH key (no files like id_rsa.pub or id_ed25519.pub), create one:
```bash
# Generate new SSH key (Ed25519 - recommended)
ssh-keygen -t ed25519 -C "your_email@example.com"

# Or RSA (legacy but widely supported)
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
```

3. Add SSH key to DigitalOcean:
   - Log into your DigitalOcean account
   - Go to Settings > Security > SSH Keys
   - Click "Add SSH Key"
   - Copy your public key:
     ```bash
     # For Ed25519 key
     cat ~/.ssh/id_ed25519.pub
     # Or for RSA key
     cat ~/.ssh/id_rsa.pub
     ```
   - Paste the key into DigitalOcean and give it a name

4. Test your SSH key (after creating droplet):
```bash
ssh -T root@your_droplet_ip
```

## Step 2: Create Droplet

1. Log in to your DigitalOcean account
2. Click "Create" > "Droplets"
3. Choose the following configuration:
   - **Image**: Ubuntu 22.04 LTS
   - **Plan**: Basic
   - **CPU option**: Regular with SSD
   - **Size**: $24/mo (4GB/2CPUs) - Recommended for production
   - **Region**: Choose closest to target market (Frankfurt for EU)
   - **Authentication**: Select your SSH key (added in Step 1)
   - **Hostname**: arbitrage-mediamrkt

## Step 3: Initial Server Setup

1. SSH into your droplet:
```bash
ssh root@your_droplet_ip
```

2. Update system and install dependencies:
```bash
# Update system
apt update && apt upgrade -y

# Install Docker and Docker Compose
apt install -y docker.io docker-compose

# Start and enable Docker
systemctl start docker
systemctl enable docker

# Install additional dependencies
apt install -y git curl
```

## Step 4: Clone and Configure Repository

1. Clone the repository:
```bash
git clone https://github.com/your-username/arbitrage-mediamrkt.git
cd arbitrage-mediamrkt
```

2. Create environment file:
```bash
cp .env.example .env
```

3. Edit the environment variables:
```bash
nano .env
```

Required variables:
```
MONGODB_URL=your_mongodb_atlas_url
REDIS_URL=your_redis_url
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
KEEPA_API_KEY=your_keepa_api_key
```

## Step 5: Deploy with Docker Compose

1. Build and start services:
```bash
docker-compose up -d --build
```

2. Verify deployment:
```bash
# Check service status
docker-compose ps

# Check logs
docker-compose logs -f

# Test API health
curl http://localhost:8000/health
```

## Step 6: Setup Nginx Reverse Proxy (Optional)

1. Install Nginx:
```bash
apt install -y nginx
```

2. Create Nginx configuration:
```bash
nano /etc/nginx/sites-available/arbitrage
```

Add the following configuration:
```nginx
server {
    listen 80;
    server_name your_domain.com;

    location / {
        proxy_pass http://localhost:8501;  # Streamlit dashboard
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /api {
        proxy_pass http://localhost:8000;  # FastAPI backend
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

3. Enable the site and restart Nginx:
```bash
ln -s /etc/nginx/sites-available/arbitrage /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

## Step 7: Setup SSL with Certbot (Optional)

1. Install Certbot:
```bash
apt install -y certbot python3-certbot-nginx
```

2. Obtain SSL certificate:
```bash
certbot --nginx -d your_domain.com
```

## Monitoring and Maintenance

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f worker
docker-compose logs -f dashboard
```

### Check Service Status
```bash
docker-compose ps
```

### Restart Services
```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart worker
```

### Update Application
```bash
# Pull latest changes
git pull

# Rebuild and restart services
docker-compose up -d --build
```

## Troubleshooting

### Worker Not Processing Tasks
1. Check worker logs:
```bash
docker-compose logs worker
```

2. Verify Redis connection:
```bash
docker-compose exec redis redis-cli ping
```

3. Restart worker:
```bash
docker-compose restart worker
```

### API Health Check Failed
1. Check API logs:
```bash
docker-compose logs api
```

2. Verify MongoDB connection:
```bash
docker-compose exec api curl -f http://localhost:8000/health
```

### Dashboard Not Loading
1. Check dashboard logs:
```bash
docker-compose logs dashboard
```

2. Verify it's accessible:
```bash
curl -f http://localhost:8501/_stcore/health
```

## Backup and Recovery

### Database Backup
MongoDB Atlas provides automated backups. Additionally, you can:
1. Export data periodically
2. Keep backup copies of the `.env` file
3. Document any custom configurations

### Service Recovery
If services fail:
1. Check logs for errors
2. Verify environment variables
3. Restart affected services
4. If needed, rebuild containers:
```bash
docker-compose down
docker-compose up -d --build
``` 
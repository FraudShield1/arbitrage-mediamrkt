#!/bin/bash

# Cross-Market Arbitrage Tool - Development Startup Script

set -e

echo "🚀 Starting Cross-Market Arbitrage Tool (Development Mode)"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env file with your configuration before running again."
    exit 1
fi

# Load environment variables
export $(grep -v '^#' .env | xargs)

echo "📦 Building and starting services with Docker Compose..."
docker-compose up --build -d

echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if services are healthy
echo "🔍 Checking service health..."

# Check PostgreSQL
if docker exec arbitrage_postgres pg_isready -U $POSTGRES_USER -d $POSTGRES_DB; then
    echo "✅ PostgreSQL is ready"
else
    echo "❌ PostgreSQL is not ready"
    exit 1
fi

# Check Redis
if docker exec arbitrage_redis redis-cli ping | grep -q PONG; then
    echo "✅ Redis is ready"
else
    echo "❌ Redis is not ready"
    exit 1
fi

# Check API
if curl -f http://localhost:${API_PORT:-8000}/health > /dev/null 2>&1; then
    echo "✅ API is ready"
else
    echo "❌ API is not ready"
    exit 1
fi

echo ""
echo "🎉 All services are running successfully!"
echo ""
echo "📊 Service URLs:"
echo "   API:       http://localhost:${API_PORT:-8000}"
echo "   API Docs:  http://localhost:${API_PORT:-8000}/docs"
echo "   Dashboard: http://localhost:${DASHBOARD_PORT:-8501}"
echo "   Flower:    http://localhost:${FLOWER_PORT:-5555}"
echo ""
echo "🐳 Docker Commands:"
echo "   View logs:    docker-compose logs -f [service_name]"
echo "   Stop all:     docker-compose down"
echo "   Stop + clean: docker-compose down -v"
echo ""
echo "📝 Log files are available in ./logs/ directory" 
#!/bin/bash

# Native IQ Deployment Script
set -e

echo "🚀 Native IQ Deployment Starting..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Please copy example.env to .env and configure your settings"
    exit 1
fi

# Create data directory
mkdir -p data/chromadb

# Build and start services
echo "🔄 Building Docker containers..."
docker-compose -f deployment/docker-compose.yml build

echo "🔄 Starting services..."
docker-compose -f deployment/docker-compose.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Health check
echo "🏥 Running health checks..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Native IQ API is healthy"
else
    echo "❌ Native IQ API health check failed"
    docker-compose -f deployment/docker-compose.yml logs native-iq
    exit 1
fi

# Test Redis
if docker-compose -f deployment/docker-compose.yml exec -T redis redis-cli ping | grep -q PONG; then
    echo "✅ Redis is healthy"
else
    echo "❌ Redis health check failed"
    exit 1
fi

echo "🎉 Native IQ deployed successfully!"
echo ""
echo "Services running:"
echo "• Native IQ API: http://localhost:8000"
echo "• Redis Cache: localhost:6379"
echo "• Nginx Proxy: http://localhost"
echo ""
echo "To view logs: docker-compose -f deployment/docker-compose.yml logs -f"
echo "To stop: docker-compose -f deployment/docker-compose.yml down"

#!/bin/bash

# Deployment script for Hetzner server
# This script will build and deploy the crypto tracker application

echo "🚀 Starting deployment on Hetzner server..."

# Navigate to project directory
cd /root/crypto-tracker

# Build Docker images
echo "📦 Building Docker images..."
docker-compose build --no-cache

# Start all services
echo "🔧 Starting Docker containers..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Run migrations
echo "🗄️ Running database migrations..."
docker-compose exec -T backend1 python manage.py migrate

# Collect static files
echo "📁 Collecting static files..."
docker-compose exec -T backend1 python manage.py collectstatic --noinput

# Show running containers
echo "✅ Deployment complete! Running containers:"
docker ps

echo "🎉 Deployment finished successfully!"

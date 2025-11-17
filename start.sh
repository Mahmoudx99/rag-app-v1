#!/bin/bash
# Quick start script for RAG Knowledge Base

set -e

echo "=================================================="
echo "🧠 RAG Knowledge Base - Quick Start"
echo "=================================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running"
    echo "Please start Docker and try again"
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: docker-compose is not installed"
    echo "Please install docker-compose and try again"
    exit 1
fi

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created"
fi

# Create data directories
echo "📁 Creating data directories..."
mkdir -p data/uploads data/chromadb data/postgres
echo "✅ Data directories created"

# Build and start services
echo ""
echo "🐳 Building and starting Docker containers..."
echo "This may take a few minutes on first run..."
echo ""

docker-compose up --build -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo ""
    echo "=================================================="
    echo "✅ RAG Knowledge Base is running!"
    echo "=================================================="
    echo ""
    echo "🌐 Access the application:"
    echo "   Frontend:  http://localhost:3000"
    echo "   Backend:   http://localhost:8000"
    echo "   API Docs:  http://localhost:8000/docs"
    echo ""
    echo "📊 View logs:"
    echo "   docker-compose logs -f"
    echo ""
    echo "🛑 Stop services:"
    echo "   docker-compose down"
    echo ""
    echo "=================================================="
else
    echo ""
    echo "❌ Error: Some services failed to start"
    echo "Check logs with: docker-compose logs"
    exit 1
fi

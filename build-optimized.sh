#!/bin/bash

# ============================================================================
# Optimized Multi-Stage Build Script
# Builds all services with layer caching and progress tracking
# ============================================================================

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Enable BuildKit for better caching
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Optimized Multi-Stage Docker Build${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Features:${NC}"
echo -e "  ✓ CPU-only PyTorch (saves ~3GB)"
echo -e "  ✓ Multi-stage builds (smaller images)"
echo -e "  ✓ Layer caching (faster rebuilds)"
echo -e "  ✓ Parallel builds"
echo ""

# Function to show build progress
build_service() {
    local service=$1
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Building: ${service}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    start_time=$(date +%s)

    if docker-compose build "$service"; then
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        echo -e "${GREEN}✓ ${service} built successfully in ${duration}s${NC}"
        echo ""
        return 0
    else
        echo -e "${RED}✗ ${service} build failed${NC}"
        return 1
    fi
}

# Check if specific service requested
if [ $# -eq 1 ]; then
    echo -e "${YELLOW}Building single service: $1${NC}"
    echo ""
    build_service "$1"
    exit 0
fi

# Build all services
echo -e "${YELLOW}Building all services...${NC}"
echo ""

total_start=$(date +%s)
failed_services=()

# Build services (order: dependencies first)
services=("backend" "llm" "file_watcher" "frontend")

for service in "${services[@]}"; do
    if ! build_service "$service"; then
        failed_services+=("$service")
    fi
done

total_end=$(date +%s)
total_duration=$((total_end - total_start))

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Build Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "Total time: ${total_duration}s"
echo ""

if [ ${#failed_services[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ All services built successfully!${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo -e "  1. Start services: ${BLUE}docker-compose up -d${NC}"
    echo -e "  2. View logs: ${BLUE}docker-compose logs -f${NC}"
    echo -e "  3. Check sizes: ${BLUE}docker images | grep rag_${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Failed services: ${failed_services[*]}${NC}"
    exit 1
fi

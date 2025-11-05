#!/bin/bash
#
# GeoNode Quick Deployment Script for s5.dothanhlong.org
#
# This script automates the deployment process for the s5 server
# Run this after checking out the deploy/s5-production branch
#

set -e

echo "=========================================="
echo "GeoNode Deployment for s5.dothanhlong.org"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Error: Do not run this script as root${NC}"
    echo "Run as regular user with docker permissions"
    exit 1
fi

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    echo "Please install Docker first:"
    echo "  sudo apt-get update"
    echo "  sudo apt-get install -y docker.io docker-compose"
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    echo "Please install Docker Compose first:"
    echo "  sudo apt-get install -y docker-compose"
    exit 1
fi

# Check if on correct branch
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null)
if [ "$CURRENT_BRANCH" != "deploy/s5-production" ]; then
    echo -e "${YELLOW}Warning: Not on deploy/s5-production branch${NC}"
    echo "Current branch: $CURRENT_BRANCH"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted. Please checkout deploy/s5-production branch:"
        echo "  git checkout deploy/s5-production"
        exit 1
    fi
fi

# Check DNS resolution
echo "1. Checking DNS resolution..."
if ! dig s5.dothanhlong.org +short &> /dev/null; then
    echo -e "${YELLOW}Warning: dig command not found, skipping DNS check${NC}"
else
    DNS_IP=$(dig s5.dothanhlong.org +short | head -1)
    if [ -z "$DNS_IP" ]; then
        echo -e "${RED}Error: DNS not resolving for s5.dothanhlong.org${NC}"
        echo "Please configure DNS A record before deployment"
        exit 1
    else
        echo -e "${GREEN}✓ DNS resolves to: $DNS_IP${NC}"
    fi
fi

# Check if ports are available
echo ""
echo "2. Checking if required ports are available..."
PORTS_IN_USE=()
for PORT in 8081 8443 8082; do
    if sudo netstat -tuln 2>/dev/null | grep -q ":$PORT "; then
        PORTS_IN_USE+=($PORT)
    elif sudo lsof -i :$PORT &> /dev/null; then
        PORTS_IN_USE+=($PORT)
    fi
done

if [ ${#PORTS_IN_USE[@]} -gt 0 ]; then
    echo -e "${RED}Error: The following ports are already in use: ${PORTS_IN_USE[*]}${NC}"
    echo "Please free these ports or stop conflicting services"
    exit 1
else
    echo -e "${GREEN}✓ Ports 8081, 8443, 8082 are available${NC}"
fi

# Check disk space
echo ""
echo "3. Checking disk space..."
AVAILABLE_GB=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
if [ "$AVAILABLE_GB" -lt 20 ]; then
    echo -e "${YELLOW}Warning: Low disk space (${AVAILABLE_GB}GB available)${NC}"
    echo "Recommended: At least 20GB free"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✓ Sufficient disk space (${AVAILABLE_GB}GB available)${NC}"
fi

# Verify configuration
echo ""
echo "4. Verifying configuration..."
if [ ! -f ".env" ]; then
    if [ -f ".env.s5-production" ]; then
        echo "Copying .env.s5-production to .env..."
        cp .env.s5-production .env
        echo -e "${GREEN}✓ Environment file created${NC}"
    else
        echo -e "${RED}Error: Neither .env nor .env.s5-production file found${NC}"
        exit 1
    fi
fi

SITEURL=$(grep "^SITEURL=" .env | cut -d'=' -f2)
if [ "$SITEURL" != "http://s5.dothanhlong.org:8081/" ]; then
    echo -e "${YELLOW}Warning: SITEURL is not configured for s5.dothanhlong.org${NC}"
    echo "Current SITEURL: $SITEURL"
    echo "Expected: http://s5.dothanhlong.org:8081/"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✓ SITEURL correctly configured${NC}"
fi

# Pull Docker images
echo ""
echo "5. Pulling Docker images..."
docker-compose pull || {
    echo -e "${RED}Error: Failed to pull Docker images${NC}"
    exit 1
}
echo -e "${GREEN}✓ Images pulled successfully${NC}"

# Start services
echo ""
echo "6. Starting services..."
docker-compose up -d || {
    echo -e "${RED}Error: Failed to start services${NC}"
    echo "Check logs with: docker-compose logs"
    exit 1
}
echo -e "${GREEN}✓ Services started${NC}"

# Wait for services to be healthy
echo ""
echo "7. Waiting for services to be healthy (this may take 2-3 minutes)..."
TIMEOUT=180
ELAPSED=0
HEALTHY=false

while [ $ELAPSED -lt $TIMEOUT ]; do
    UNHEALTHY=$(docker-compose ps | grep -c "unhealthy" || true)
    STARTING=$(docker-compose ps | grep -c "starting" || true)

    if [ "$UNHEALTHY" -eq 0 ] && [ "$STARTING" -eq 0 ]; then
        HEALTHY=true
        break
    fi

    echo -n "."
    sleep 5
    ELAPSED=$((ELAPSED + 5))
done

echo ""

if [ "$HEALTHY" = true ]; then
    echo -e "${GREEN}✓ All services are healthy${NC}"
else
    echo -e "${YELLOW}Warning: Some services may not be fully ready yet${NC}"
    echo "Check status with: docker-compose ps"
fi

# Run basic tests
echo ""
echo "8. Running basic connectivity tests..."

# Test HTTP endpoint
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://s5.dothanhlong.org:8081/ 2>/dev/null || echo "000")
if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "302" ]; then
    echo -e "${GREEN}✓ HTTP endpoint responding (HTTP $HTTP_CODE)${NC}"
else
    echo -e "${YELLOW}⚠ HTTP endpoint returned HTTP $HTTP_CODE${NC}"
fi

# Test API endpoint
API_TEST=$(curl -s http://s5.dothanhlong.org:8081/api/v2/ 2>/dev/null | grep -q "datasets" && echo "OK" || echo "FAIL")
if [ "$API_TEST" == "OK" ]; then
    echo -e "${GREEN}✓ API endpoint responding${NC}"
else
    echo -e "${YELLOW}⚠ API endpoint may not be ready${NC}"
fi

# Test GeoServer
GS_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://s5.dothanhlong.org:8081/geoserver/ 2>/dev/null || echo "000")
if [ "$GS_CODE" == "200" ] || [ "$GS_CODE" == "302" ]; then
    echo -e "${GREEN}✓ GeoServer responding (HTTP $GS_CODE)${NC}"
else
    echo -e "${YELLOW}⚠ GeoServer returned HTTP $GS_CODE${NC}"
fi

# Summary
echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Access your GeoNode instance:"
echo "  Homepage:   http://s5.dothanhlong.org:8081/"
echo "  Admin:      http://s5.dothanhlong.org:8081/admin/"
echo "  GeoServer:  http://s5.dothanhlong.org:8081/geoserver/"
echo "  API:        http://s5.dothanhlong.org:8081/api/v2/"
echo ""
echo "Credentials:"
echo "  GeoNode Admin:   admin / zTCBtB1eyCasknK"
echo "  GeoServer Admin: admin / gmdGeNM8Icaj3VZ"
echo ""
echo "Useful commands:"
echo "  View logs:        docker-compose logs -f"
echo "  Container status: docker-compose ps"
echo "  Restart:          docker-compose restart"
echo "  Stop:             docker-compose stop"
echo ""
echo "For detailed documentation, see: DEPLOYMENT_S5.md"
echo ""

# Open in browser (if running locally with display)
if [ -n "$DISPLAY" ]; then
    echo "Opening homepage in browser..."
    xdg-open "http://s5.dothanhlong.org:8081/" 2>/dev/null || \
    open "http://s5.dothanhlong.org:8081/" 2>/dev/null || \
    echo "Please open http://s5.dothanhlong.org:8081/ in your browser"
fi

exit 0

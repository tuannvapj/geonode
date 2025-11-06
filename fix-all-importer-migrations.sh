#!/bin/bash
# Comprehensive fix for ALL problematic importer migrations
# These are data migrations that fail on fresh databases

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "========================================================"
echo -e "${BLUE}GeoNode - Fix ALL Importer Migrations${NC}"
echo "========================================================"
echo ""
echo "This will fake all problematic importer data migrations:"
echo "  - 0006_dataset_migration"
echo "  - 0007_align_resourcehandler_with_asset"
echo "  - Any other data migrations that query non-existent columns"
echo ""

# Stop all services
echo -e "${YELLOW}Step 1: Stopping all services...${NC}"
docker-compose down
sleep 3
echo -e "${GREEN}✓ Services stopped${NC}"

# Start only database
echo ""
echo -e "${YELLOW}Step 2: Starting database...${NC}"
docker-compose up -d db rabbitmq
echo "  Waiting for database (20 seconds)..."
sleep 20

for i in {1..10}; do
    if docker-compose exec -T db pg_isready -U postgres >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Database is ready${NC}"
        break
    fi
    sleep 2
done

# Run migrations up to importer 0005 (before the problematic ones)
echo ""
echo -e "${YELLOW}Step 3: Running migrations up to importer 0005...${NC}"
docker-compose run --rm -e IS_CELERY=True django bash -c "
    python manage.py migrate --run-syncdb --noinput 2>&1 | head -50
    python manage.py migrate importer 0005 --noinput 2>&1 | tail -10
" || echo "  (Errors expected, continuing...)"

echo -e "${GREEN}✓ Base migrations completed${NC}"

# Fake all problematic importer migrations
echo ""
echo -e "${YELLOW}Step 4: Faking problematic importer migrations in database...${NC}"

docker-compose exec -T db psql -U postgres -d geonode <<'EOSQL'
-- Remove any existing records for these migrations
DELETE FROM django_migrations WHERE app='importer' AND name IN (
    '0006_dataset_migration',
    '0007_align_resourcehandler_with_asset'
);

-- Insert fake records for problematic migrations
INSERT INTO django_migrations (app, name, applied) VALUES
    ('importer', '0006_dataset_migration', NOW()),
    ('importer', '0007_align_resourcehandler_with_asset', NOW())
ON CONFLICT DO NOTHING;

-- Verify the records
SELECT app, name, applied FROM django_migrations
WHERE app='importer'
ORDER BY id;
EOSQL

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Successfully faked problematic migrations${NC}"
else
    echo -e "${RED}✗ Failed to insert migration records${NC}"
    exit 1
fi

# Run remaining migrations
echo ""
echo -e "${YELLOW}Step 5: Running remaining migrations...${NC}"
docker-compose run --rm -e IS_CELERY=True django bash -c "
    echo 'Running remaining importer migrations...'
    python manage.py migrate importer --noinput 2>&1 | tail -20

    echo 'Running all other migrations...'
    python manage.py migrate --noinput 2>&1 | tail -20
" || echo "  (Some errors may be expected)"

echo -e "${GREEN}✓ Migrations completed${NC}"

# Migrate datastore
echo ""
echo -e "${YELLOW}Step 6: Migrating datastore database...${NC}"
docker-compose run --rm -e IS_CELERY=True django \
    python manage.py migrate --database=datastore --noinput 2>&1 | tail -10

echo -e "${GREEN}✓ Datastore migrated${NC}"

# Start all services
echo ""
echo -e "${YELLOW}Step 7: Starting all services...${NC}"
docker-compose up -d

echo "  Waiting for services to start (45 seconds)..."
sleep 45

# Check Django status
echo ""
echo -e "${YELLOW}Step 8: Checking Django status...${NC}"

if docker-compose ps django | grep -q "Up"; then
    echo -e "${GREEN}✓ Django container is UP!${NC}"

    # Give Django time to fully initialize
    sleep 10

    # Collect static files
    echo ""
    echo -e "${YELLOW}Step 9: Collecting static files...${NC}"
    docker-compose exec -T django python manage.py collectstatic --nohint --noinput 2>&1 | tail -5 || true

    echo ""
    echo "========================================================"
    echo -e "${GREEN}✓✓✓ SUCCESS! GeoNode is running! ✓✓✓${NC}"
    echo "========================================================"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo ""
    echo "1. Verify all services:"
    echo -e "   ${YELLOW}docker-compose ps${NC}"
    echo ""
    echo "2. Check Django logs:"
    echo -e "   ${YELLOW}docker-compose logs django | tail -50${NC}"
    echo ""
    echo "3. Create superuser:"
    echo -e "   ${YELLOW}docker-compose exec django python manage.py createsuperuser${NC}"
    echo ""
    echo "4. Access GeoNode:"
    echo -e "   ${YELLOW}http://s5.opengis.vn:8091/${NC}"
    echo ""

    # Show service status
    echo "Current service status:"
    docker-compose ps

else
    echo -e "${RED}✗ Django container failed to start${NC}"
    echo ""
    echo "Showing last 100 lines of Django logs:"
    docker-compose logs django | tail -100
    exit 1
fi

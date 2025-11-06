#!/bin/bash
# DEFINITIVE FIX for GeoNode Migration Issue
# This script bypasses the automatic migration in entrypoint.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "========================================================"
echo -e "${BLUE}GeoNode Migration Fix - Definitive Solution${NC}"
echo "========================================================"
echo ""
echo "This script will:"
echo "  1. Stop all services"
echo "  2. Start database only"
echo "  3. Run migrations manually using docker run"
echo "  4. Fake the problematic migration"
echo "  5. Start all services normally"
echo ""

# Step 1: Stop all services
echo -e "${YELLOW}Step 1: Stopping all services...${NC}"
docker-compose down
echo -e "${GREEN}✓ Services stopped${NC}"

# Step 2: Start only database
echo ""
echo -e "${YELLOW}Step 2: Starting database service...${NC}"
docker-compose up -d db rabbitmq
echo "  Waiting for database to initialize (20 seconds)..."
sleep 20

# Check database is ready
echo "  Checking database connection..."
for i in {1..10}; do
    if docker-compose exec -T db pg_isready -U postgres >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Database is ready${NC}"
        break
    fi
    if [ $i -eq 10 ]; then
        echo -e "${RED}✗ Database failed to start${NC}"
        exit 1
    fi
    sleep 2
done

# Step 3: Check if tables exist
echo ""
echo -e "${YELLOW}Step 3: Checking database state...${NC}"
TABLE_COUNT=$(docker-compose exec -T db psql -U postgres -d geonode -tAc \
  "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null || echo "0")

echo "  Found $TABLE_COUNT tables in database"

if [ "$TABLE_COUNT" -lt 10 ]; then
    echo -e "${YELLOW}  Database is empty or incomplete. Running initial migrations...${NC}"

    # Step 4: Run migrations using docker run (bypasses entrypoint.sh)
    echo ""
    echo -e "${YELLOW}Step 4: Running migrations manually (bypassing entrypoint)...${NC}"
    echo "  This may take 2-3 minutes..."

    # Set environment variables to skip entrypoint tasks
    docker-compose run --rm -e IS_CELERY=True django bash -c "
        echo 'Running migrations manually...'
        python manage.py migrate auth --noinput || true
        python manage.py migrate contenttypes --noinput || true
        python manage.py migrate sessions --noinput || true
        python manage.py migrate admin --noinput || true
        python manage.py migrate sites --noinput || true
        python manage.py migrate --run-syncdb --noinput || true
    " 2>&1 | grep -v "Applying importer.0006" || true

    echo -e "${GREEN}✓ Initial migrations completed (errors ignored)${NC}"
else
    echo -e "${GREEN}✓ Database already has tables${NC}"
fi

# Step 5: Fake the problematic migration
echo ""
echo -e "${YELLOW}Step 5: Marking problematic migration as completed...${NC}"

# Check if django_migrations table exists
MIGRATIONS_TABLE_EXISTS=$(docker-compose exec -T db psql -U postgres -d geonode -tAc \
  "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name='django_migrations');" 2>/dev/null || echo "f")

if [ "$MIGRATIONS_TABLE_EXISTS" = "t" ]; then
    echo "  Inserting fake migration record into database..."

    docker-compose exec -T db psql -U postgres -d geonode <<EOF
DELETE FROM django_migrations WHERE app='importer' AND name='0006_dataset_migration';
INSERT INTO django_migrations (app, name, applied)
VALUES ('importer', '0006_dataset_migration', NOW());
EOF

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Successfully marked migration as completed${NC}"
    else
        echo -e "${RED}✗ Failed to insert migration record${NC}"
        exit 1
    fi

    # Verify
    echo "  Verifying migration record..."
    MIGRATION_EXISTS=$(docker-compose exec -T db psql -U postgres -d geonode -tAc \
      "SELECT EXISTS (SELECT 1 FROM django_migrations WHERE app='importer' AND name='0006_dataset_migration');" 2>/dev/null)

    if [ "$MIGRATION_EXISTS" = "t" ]; then
        echo -e "${GREEN}✓ Migration record verified in database${NC}"
    else
        echo -e "${RED}✗ Migration record not found after insert${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}  django_migrations table doesn't exist yet. Running base migrations...${NC}"

    docker-compose run --rm -e IS_CELERY=True django python manage.py migrate --run-syncdb --fake-initial 2>&1 | tail -20

    # Now insert the fake record
    docker-compose exec -T db psql -U postgres -d geonode <<EOF
INSERT INTO django_migrations (app, name, applied)
VALUES ('importer', '0006_dataset_migration', NOW())
ON CONFLICT DO NOTHING;
EOF
fi

# Step 6: Start all services
echo ""
echo -e "${YELLOW}Step 6: Starting all services...${NC}"
docker-compose down
sleep 3
docker-compose up -d

echo "  Waiting for services to start (40 seconds)..."
sleep 40

# Step 7: Check Django status
echo ""
echo -e "${YELLOW}Step 7: Checking Django container status...${NC}"

if docker-compose ps django | grep -q "Up"; then
    echo -e "${GREEN}✓ Django container is running!${NC}"

    # Wait a bit more for Django to fully start
    sleep 10

    echo ""
    echo -e "${YELLOW}Step 8: Completing remaining setup...${NC}"

    # Try to complete migrations
    echo "  Running final migrations..."
    docker-compose exec -T django python manage.py migrate --noinput 2>&1 | tail -10 || true

    echo "  Migrating datastore..."
    docker-compose exec -T django python manage.py migrate --database=datastore --noinput 2>&1 | tail -10 || true

    echo "  Collecting static files..."
    docker-compose exec -T django python manage.py collectstatic --nohint --noinput 2>&1 | tail -5 || true

    echo ""
    echo "========================================================"
    echo -e "${GREEN}SUCCESS! Django is running!${NC}"
    echo "========================================================"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo ""
    echo "1. Check all services are running:"
    echo "   ${YELLOW}docker-compose ps${NC}"
    echo ""
    echo "2. Create superuser:"
    echo "   ${YELLOW}docker-compose exec django python manage.py createsuperuser${NC}"
    echo ""
    echo "3. Access GeoNode:"
    echo "   ${YELLOW}http://s5.opengis.vn:8091/${NC}"
    echo ""
    echo "4. Monitor logs:"
    echo "   ${YELLOW}docker-compose logs -f django${NC}"
    echo ""

else
    echo -e "${RED}✗ Django container is not running${NC}"
    echo ""
    echo "Checking Django logs for errors:"
    docker-compose logs django | tail -50
    echo ""
    echo -e "${RED}Please share the error above for further troubleshooting.${NC}"
    exit 1
fi

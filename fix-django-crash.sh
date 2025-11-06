#!/bin/bash
# Fix Django crash loop by manually faking the problematic migration
# This script accesses the database directly when Django container is crashing

set -e

echo "================================================"
echo "Fix Django Crash Loop - Database Direct Access"
echo "================================================"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo -e "${YELLOW}Step 1: Checking if database container is running...${NC}"
if ! docker-compose ps db | grep -q "Up"; then
    echo -e "${RED}✗ Database container is not running. Starting it...${NC}"
    docker-compose up -d db
    sleep 10
fi
echo -e "${GREEN}✓ Database container is running${NC}"

echo ""
echo -e "${YELLOW}Step 2: Waiting for database to be ready...${NC}"
for i in {1..15}; do
    if docker-compose exec -T db pg_isready -U postgres >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Database is ready${NC}"
        break
    fi
    echo "  Waiting for database... attempt $i/15"
    sleep 2
done

echo ""
echo -e "${YELLOW}Step 3: Checking if django_migrations table exists...${NC}"
TABLE_EXISTS=$(docker-compose exec -T db psql -U postgres -d geonode -tAc \
  "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name='django_migrations');" 2>/dev/null || echo "f")

if [ "$TABLE_EXISTS" = "f" ]; then
    echo -e "${RED}✗ django_migrations table doesn't exist. This is a completely fresh database.${NC}"
    echo -e "${YELLOW}  We need to let Django create the initial tables first.${NC}"
    echo ""
    echo -e "${YELLOW}Step 3a: Stopping Django to prevent crash loop...${NC}"
    docker-compose stop django celery

    echo ""
    echo -e "${YELLOW}Step 3b: Creating initial database tables...${NC}"
    echo "  This will run Django migrate command once to create base tables..."

    # Run migrate command directly without starting the full service
    docker-compose run --rm --no-deps django python manage.py migrate --run-syncdb --fake-initial 2>&1 | tail -20

    if [ $? -ne 0 ]; then
        echo -e "${RED}✗ Initial migration failed. Trying alternative approach...${NC}"

        # Try migrating everything except the problematic app first
        echo "  Migrating all apps except importer..."
        docker-compose run --rm --no-deps django python manage.py migrate --run-syncdb auth contenttypes sessions admin 2>&1 | tail -10
    fi

    # Update TABLE_EXISTS flag
    TABLE_EXISTS="t"
fi

if [ "$TABLE_EXISTS" = "t" ]; then
    echo -e "${GREEN}✓ django_migrations table exists${NC}"

    echo ""
    echo -e "${YELLOW}Step 4: Checking if problematic migration is already recorded...${NC}"

    MIGRATION_EXISTS=$(docker-compose exec -T db psql -U postgres -d geonode -tAc \
      "SELECT EXISTS (SELECT 1 FROM django_migrations WHERE app='importer' AND name='0006_dataset_migration');" 2>/dev/null || echo "f")

    if [ "$MIGRATION_EXISTS" = "t" ]; then
        echo -e "${GREEN}✓ Migration already recorded as applied${NC}"
    else
        echo -e "${YELLOW}⚠ Migration not found. Inserting fake migration record...${NC}"

        docker-compose exec -T db psql -U postgres -d geonode <<-EOSQL
            INSERT INTO django_migrations (app, name, applied)
            VALUES ('importer', '0006_dataset_migration', NOW())
            ON CONFLICT DO NOTHING;
EOSQL

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Successfully inserted fake migration record${NC}"
        else
            echo -e "${RED}✗ Failed to insert migration record${NC}"
            exit 1
        fi
    fi
fi

echo ""
echo -e "${YELLOW}Step 5: Verifying migration record...${NC}"
docker-compose exec -T db psql -U postgres -d geonode -c \
  "SELECT app, name, applied FROM django_migrations WHERE app='importer' ORDER BY applied DESC LIMIT 5;"

echo ""
echo -e "${YELLOW}Step 6: Restarting all services...${NC}"
docker-compose down
sleep 3
docker-compose up -d

echo ""
echo -e "${YELLOW}Step 7: Waiting for services to start (45 seconds)...${NC}"
sleep 45

echo ""
echo -e "${YELLOW}Step 8: Checking Django container status...${NC}"
DJANGO_STATUS=$(docker-compose ps django | grep django | awk '{print $4}')
echo "  Django status: $DJANGO_STATUS"

if docker-compose ps django | grep -q "Up"; then
    echo -e "${GREEN}✓ Django container is running!${NC}"

    echo ""
    echo -e "${YELLOW}Step 9: Checking Django logs for errors...${NC}"
    docker-compose logs django | tail -30

    echo ""
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}Fix completed! Django should be starting now.${NC}"
    echo -e "${GREEN}================================================${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Monitor Django startup:"
    echo "   docker-compose logs -f django"
    echo ""
    echo "2. Once Django is fully up, complete setup:"
    echo "   docker-compose exec django python manage.py migrate"
    echo "   docker-compose exec django python manage.py migrate --database=datastore"
    echo "   docker-compose exec django python manage.py collectstatic --nohint --noinput"
    echo ""
    echo "3. Create superuser:"
    echo "   docker-compose exec django python manage.py createsuperuser"
    echo ""
    echo "4. Access GeoNode:"
    echo "   http://s5.opengis.vn:8091/"
else
    echo -e "${RED}✗ Django container is still not running properly${NC}"
    echo ""
    echo "Check the logs:"
    echo "  docker-compose logs django"
fi

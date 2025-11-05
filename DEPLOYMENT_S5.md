# GeoNode Deployment for s5.dothanhlong.org

**Branch**: `deploy/s5-production`
**Domain**: s5.dothanhlong.org
**Date**: November 5, 2025

---

## Quick Start (For s5.dothanhlong.org Server)

This branch is pre-configured for deployment on **s5.dothanhlong.org** with ports **8081/8443/8082**.
Simply checkout this branch and run docker-compose!

### Prerequisites

1. **DNS configured**: `s5.dothanhlong.org` → Your server IP
2. **Ports available**: 8081, 8082, 8443
3. **Docker & Docker Compose installed**
4. **Firewall configured** (see below)

### One-Command Deployment

```bash
# Clone repository
git clone https://github.com/your-org/geonode.git /opt/geonode
cd /opt/geonode

# Checkout deployment branch
git checkout deploy/s5-production

# Copy pre-configured environment file
cp .env.s5-production .env

# Start services
docker-compose up -d

# Monitor startup (wait for healthy status)
docker-compose logs -f
```

That's it! GeoNode will be available at:
- **Homepage**: http://s5.dothanhlong.org:8081/
- **Admin**: http://s5.dothanhlong.org:8081/admin/
- **GeoServer**: http://s5.dothanhlong.org:8081/geoserver/

---

## Pre-Configured Settings

This branch includes the following production-ready configuration:

### Ports
- **HTTP**: 8081 (instead of 80)
- **HTTPS**: 8443 (instead of 443)
- **GeoServer**: 8082 (instead of 8080)
- **PostgreSQL**: Internal only (5432 inside containers)
- **RabbitMQ**: Internal only (5672 inside containers)

### Domain & URLs
- **SITEURL**: http://s5.dothanhlong.org:8081/
- **HTTP_HOST**: s5.dothanhlong.org
- **ALLOWED_HOSTS**: django, localhost, s5.dothanhlong.org
- **GEOSERVER_WEB_UI_LOCATION**: http://s5.dothanhlong.org:8081/geoserver/
- **CORS_ALLOWED_ORIGINS**: Configured for domain and localhost

### Production Settings
- **DEBUG**: False (production mode)
- **ADMIN_EMAIL**: admin@dothanhlong.org
- **DEFAULT_FROM_EMAIL**: GeoNode <no-reply@dothanhlong.org>
- **MONITORING_HOST_NAME**: s5.dothanhlong.org

### Security
- SSL/TLS: Disabled by default (use LETSENCRYPT_MODE=disabled)
- Session cookies: Configured for .dothanhlong.org domain
- CORS: Enabled for domain and subdomains

---

## Detailed Deployment Steps

### Step 1: Verify DNS Resolution

```bash
# Check DNS is working
dig s5.dothanhlong.org +short
# Should return your server IP

# Test from different DNS servers
dig @8.8.8.8 s5.dothanhlong.org +short  # Google DNS
dig @1.1.1.1 s5.dothanhlong.org +short  # Cloudflare DNS

# Verify connectivity
ping -c 4 s5.dothanhlong.org
```

### Step 2: Configure Firewall

```bash
# UFW (Ubuntu/Debian)
sudo ufw allow 8081/tcp comment 'GeoNode HTTP'
sudo ufw allow 8443/tcp comment 'GeoNode HTTPS'
sudo ufw allow 8082/tcp comment 'GeoServer Direct'
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw enable
sudo ufw status

# firewalld (CentOS/RHEL)
sudo firewall-cmd --permanent --add-port=8081/tcp
sudo firewall-cmd --permanent --add-port=8443/tcp
sudo firewall-cmd --permanent --add-port=8082/tcp
sudo firewall-cmd --reload

# iptables
sudo iptables -A INPUT -p tcp --dport 8081 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8443 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8082 -j ACCEPT
sudo iptables-save > /etc/iptables/rules.v4
```

### Step 3: Install Docker & Docker Compose

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y docker.io docker-compose

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Verify installation
docker --version
docker-compose --version

# Add your user to docker group (optional)
sudo usermod -aG docker $USER
newgrp docker
```

### Step 4: Clone Repository

```bash
# Clone to /opt/geonode
sudo mkdir -p /opt
cd /opt
sudo git clone https://github.com/your-org/geonode.git geonode
sudo chown -R $USER:$USER /opt/geonode
cd /opt/geonode

# Checkout deployment branch
git checkout deploy/s5-production

# Verify you're on the right branch
git branch --show-current
# Should show: deploy/s5-production

# Copy pre-configured environment file
cp .env.s5-production .env

# Verify configuration
grep SITEURL .env
# Should show: SITEURL=http://s5.dothanhlong.org:8081/
```

### Step 5: Pull Docker Images

```bash
cd /opt/geonode

# Pull all required images
docker-compose pull

# This will download:
# - geonode/geonode:4.4.3
# - geonode/nginx:1.25.3-latest
# - geonode/geoserver:2.24.4-latest
# - geonode/postgis:15.3-latest
# - rabbitmq:3-alpine
# - memcached:alpine
```

### Step 6: Start Services

```bash
# Start all services in detached mode
docker-compose up -d

# Monitor logs
docker-compose logs -f

# Watch for these messages:
# - "django4geonode" - "Booting worker with pid"
# - "geoserver4geonode" - "INFO: Server startup"
# - "db4geonode" - "database system is ready to accept connections"

# Press Ctrl+C to exit log view (containers keep running)
```

### Step 7: Wait for Healthy Status

```bash
# Check container status
docker-compose ps

# All services should show "Up" and "healthy"
# This may take 2-3 minutes after initial startup

# Watch health status in real-time
watch -n 5 'docker-compose ps'

# Once all healthy, press Ctrl+C
```

### Step 8: Verify Deployment

```bash
# Test HTTP endpoint
curl -I http://s5.dothanhlong.org:8081/
# Expected: HTTP/1.1 200 OK or 302

# Test API
curl -s http://s5.dothanhlong.org:8081/api/v2/ | grep datasets
# Expected: JSON with "datasets" key

# Test GeoServer
curl -I http://s5.dothanhlong.org:8081/geoserver/
# Expected: HTTP/1.1 200 OK or 302

# Test GeoServer direct
curl -I http://s5.dothanhlong.org:8082/geoserver/
# Expected: HTTP/1.1 200 OK or 302

# Test database connectivity
docker exec django4geonode python manage.py dbshell -c "SELECT version();"
# Expected: PostgreSQL version info
```

---

## Access Information

### Web Interfaces

| Service | URL | Credentials |
|---------|-----|-------------|
| **GeoNode Homepage** | http://s5.dothanhlong.org:8081/ | N/A (public) |
| **GeoNode Admin** | http://s5.dothanhlong.org:8081/admin/ | admin / zTCBtB1eyCasknK |
| **GeoServer Web UI** | http://s5.dothanhlong.org:8081/geoserver/ | admin / gmdGeNM8Icaj3VZ |
| **GeoServer Direct** | http://s5.dothanhlong.org:8082/geoserver/ | admin / gmdGeNM8Icaj3VZ |
| **API Root** | http://s5.dothanhlong.org:8081/api/v2/ | N/A (token auth) |

### OGC Services

| Service | Endpoint URL |
|---------|--------------|
| **WMS** | http://s5.dothanhlong.org:8081/geoserver/wms |
| **WFS** | http://s5.dothanhlong.org:8081/geoserver/wfs |
| **WCS** | http://s5.dothanhlong.org:8081/geoserver/wcs |
| **WMS-C** | http://s5.dothanhlong.org:8081/geoserver/gwc/service/wms |

### API Endpoints

| Endpoint | URL |
|----------|-----|
| **Datasets API** | http://s5.dothanhlong.org:8081/api/v2/datasets/ |
| **Maps API** | http://s5.dothanhlong.org:8081/api/v2/maps/ |
| **Users API** | http://s5.dothanhlong.org:8081/api/v2/users/ |
| **Metadata API** | http://s5.dothanhlong.org:8081/api/v2/datasets/{id}/metadata_fields/ |
| **OAuth2 Token** | http://s5.dothanhlong.org:8081/o/token/ |

### OAuth2 Configuration

**For QGIS Plugin**:
```
Server URL: http://s5.dothanhlong.org:8081/
Client ID: Iyin6MNBz4K58z0
Client Secret: d1Nbpf3gcFlV3xc
Token URL: http://s5.dothanhlong.org:8081/o/token/
```

**Get Access Token**:
```bash
curl -X POST http://s5.dothanhlong.org:8081/o/token/ \
  -d "grant_type=password" \
  -d "username=admin" \
  -d "password=zTCBtB1eyCasknK" \
  -d "client_id=Iyin6MNBz4K58z0" \
  -d "client_secret=d1Nbpf3gcFlV3xc"
```

---

## Container Management

### Common Commands

```bash
# View logs
docker-compose logs -f [service_name]
docker-compose logs -f django
docker-compose logs -f geoserver

# Restart specific service
docker-compose restart django
docker-compose restart geoserver
docker-compose restart nginx

# Restart all services
docker-compose restart

# Stop all services
docker-compose stop

# Start all services
docker-compose start

# Stop and remove containers (keeps data)
docker-compose down

# Stop and remove containers + volumes (DELETES DATA!)
docker-compose down -v  # ⚠️ Use with caution!

# View container status
docker-compose ps

# View resource usage
docker stats --no-stream

# Execute command in container
docker exec -it django4geonode bash
docker exec -it geoserver4geonode bash

# View container logs from beginning
docker logs django4geonode

# Follow container logs
docker logs -f django4geonode
```

### Database Management

```bash
# Access PostgreSQL shell
docker exec -it db4geonode psql -U postgres

# In psql:
\l                    # List databases
\c geonode            # Connect to geonode database
\dt                   # List tables
\q                    # Quit

# Backup database
docker exec db4geonode pg_dumpall -U postgres | gzip > /backup/geonode_$(date +%Y%m%d).sql.gz

# Restore database
gunzip -c /backup/geonode_20251105.sql.gz | docker exec -i db4geonode psql -U postgres

# Run Django migrations
docker exec django4geonode python manage.py migrate

# Create Django superuser
docker exec -it django4geonode python manage.py createsuperuser

# Collect static files
docker exec django4geonode python manage.py collectstatic --noinput

# Update GeoServer layers
docker exec django4geonode python manage.py updatelayers
```

---

## Troubleshooting

### Issue: Containers won't start

```bash
# Check logs for errors
docker-compose logs django
docker-compose logs geoserver
docker-compose logs db

# Check port conflicts
sudo netstat -tuln | grep -E ":(8081|8082|8443)"
sudo lsof -i :8081

# Restart Docker daemon
sudo systemctl restart docker
docker-compose up -d
```

### Issue: 502 Bad Gateway

```bash
# Check django is healthy
docker exec django4geonode curl -f http://localhost:8000/

# Check nginx upstream config
docker exec nginx4geonode cat /etc/nginx/nginx.conf | grep upstream

# Restart services
docker-compose restart django nginx
```

### Issue: Database connection errors

```bash
# Check database is running
docker exec db4geonode pg_isready -U postgres

# Check connection string
docker exec django4geonode python manage.py dbshell

# View database logs
docker logs db4geonode | tail -50

# Restart database
docker-compose restart db
```

### Issue: Static files not loading (404)

```bash
# Collect static files
docker exec django4geonode python manage.py collectstatic --noinput

# Check volume
docker exec nginx4geonode ls -la /mnt/volumes/statics/static/

# Restart nginx
docker-compose restart nginx
```

### Issue: GeoServer layers not loading

```bash
# Check GeoServer is accessible
curl -u admin:gmdGeNM8Icaj3VZ http://s5.dothanhlong.org:8082/geoserver/rest/workspaces.json

# Re-register layers
docker exec django4geonode python manage.py updatelayers

# Check GeoServer logs
docker logs geoserver4geonode | tail -100
```

### Issue: Cannot login to admin

```bash
# Reset admin password
docker exec -it django4geonode python manage.py changepassword admin

# Create new superuser
docker exec -it django4geonode python manage.py createsuperuser

# Check ALLOWED_HOSTS
grep ALLOWED_HOSTS .env
# Should include: s5.dothanhlong.org
```

---

## Performance Tuning

### Increase GeoServer Memory

Edit `.env`:
```bash
# Change from default 4GB to 8GB
GEOSERVER_JAVA_OPTS=-Djava.awt.headless=true -Xms8G -Xmx8G ...
```

Restart GeoServer:
```bash
docker-compose restart geoserver
```

### Increase PostgreSQL Connections

Edit `.env`:
```bash
POSTGRESQL_MAX_CONNECTIONS=300  # Default is 200
```

Restart database:
```bash
docker-compose restart db
```

### Enable Memcached

Edit `.env`:
```bash
MEMCACHED_ENABLED=True
```

Restart Django:
```bash
docker-compose restart django
```

---

## SSL/TLS Configuration (Optional)

### Option 1: Let's Encrypt (Recommended)

For non-standard ports (8081/8443), use DNS-01 challenge:

```bash
# Install certbot with DNS plugin
sudo apt-get install certbot python3-certbot-dns-cloudflare

# Configure DNS credentials (example for Cloudflare)
cat > ~/.secrets/cloudflare.ini <<EOF
dns_cloudflare_api_token = YOUR_API_TOKEN
EOF
chmod 600 ~/.secrets/cloudflare.ini

# Obtain certificate
sudo certbot certonly \
  --dns-cloudflare \
  --dns-cloudflare-credentials ~/.secrets/cloudflare.ini \
  -d s5.dothanhlong.org

# Copy to nginx volume
docker run --rm \
  -v geonode-nginxcerts:/certs \
  -v /etc/letsencrypt:/letsencrypt \
  alpine sh -c "
    cp /letsencrypt/live/s5.dothanhlong.org/fullchain.pem /certs/ && \
    cp /letsencrypt/live/s5.dothanhlong.org/privkey.pem /certs/
  "

# Update .env
# LETSENCRYPT_MODE=production

# Restart nginx
docker-compose restart geonode
```

### Option 2: Reverse Proxy on Standard Ports

Set up external Nginx on 80/443 forwarding to 8081/8443:

```nginx
# /etc/nginx/sites-available/geonode
server {
    listen 80;
    server_name s5.dothanhlong.org;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name s5.dothanhlong.org;

    ssl_certificate /etc/letsencrypt/live/s5.dothanhlong.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/s5.dothanhlong.org/privkey.pem;

    location / {
        proxy_pass http://localhost:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    client_max_body_size 5G;
}
```

Enable and restart:
```bash
sudo ln -s /etc/nginx/sites-available/geonode /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

Then update `.env`:
```bash
SITEURL=https://s5.dothanhlong.org/
```

---

## Backup & Restore

### Create Backup

```bash
# Create backup directory
mkdir -p /backup

# Backup database
docker exec db4geonode pg_dumpall -U postgres | gzip > /backup/geonode_db_$(date +%Y%m%d).sql.gz

# Backup GeoServer data directory
docker run --rm \
  -v geonode-gsdatadir:/data \
  -v /backup:/backup \
  alpine tar czf /backup/geoserver_data_$(date +%Y%m%d).tar.gz -C /data .

# Backup uploaded files
docker run --rm \
  -v geonode-statics:/data \
  -v /backup:/backup \
  alpine tar czf /backup/geonode_statics_$(date +%Y%m%d).tar.gz -C /data .

# Backup configuration
tar czf /backup/geonode_config_$(date +%Y%m%d).tar.gz \
  .env docker-compose.yml docker-compose-dev.yml
```

### Restore from Backup

```bash
# Stop services
docker-compose down

# Restore database
gunzip -c /backup/geonode_db_20251105.sql.gz | \
  docker exec -i db4geonode psql -U postgres

# Restore GeoServer data
docker run --rm \
  -v geonode-gsdatadir:/data \
  -v /backup:/backup \
  alpine tar xzf /backup/geoserver_data_20251105.tar.gz -C /data

# Restore uploaded files
docker run --rm \
  -v geonode-statics:/data \
  -v /backup:/backup \
  alpine tar xzf /backup/geonode_statics_20251105.tar.gz -C /data

# Restore configuration
tar xzf /backup/geonode_config_20251105.tar.gz

# Start services
docker-compose up -d
```

### Automated Backup Script

Create `/opt/scripts/backup-geonode.sh`:

```bash
#!/bin/bash
set -e

BACKUP_DIR="/backup"
DATE=$(date +%Y%m%d_%H%M%S)

echo "Starting GeoNode backup - $DATE"

# Database
docker exec db4geonode pg_dumpall -U postgres | \
  gzip > ${BACKUP_DIR}/geonode_db_${DATE}.sql.gz

# GeoServer data
docker run --rm \
  -v geonode-gsdatadir:/data \
  -v ${BACKUP_DIR}:/backup \
  alpine tar czf /backup/geoserver_data_${DATE}.tar.gz -C /data .

# Uploaded files
docker run --rm \
  -v geonode-statics:/data \
  -v ${BACKUP_DIR}:/backup \
  alpine tar czf /backup/geonode_statics_${DATE}.tar.gz -C /data .

# Delete backups older than 30 days
find ${BACKUP_DIR} -name "geonode_*" -mtime +30 -delete

echo "Backup complete: $DATE"
```

Schedule with cron:
```bash
# Run daily at 2 AM
0 2 * * * /opt/scripts/backup-geonode.sh >> /var/log/geonode-backup.log 2>&1
```

---

## Monitoring & Maintenance

### Health Checks

```bash
# Check all services
docker-compose ps

# Check disk space
df -h

# Check volume sizes
docker system df -v

# Check container resource usage
docker stats --no-stream

# Check database size
docker exec db4geonode psql -U postgres -c "
SELECT pg_database.datname,
       pg_size_pretty(pg_database_size(pg_database.datname)) AS size
FROM pg_stat_database;
"
```

### Log Rotation

Docker logs can grow large. Configure log rotation in `/etc/docker/daemon.json`:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

Restart Docker:
```bash
sudo systemctl restart docker
docker-compose up -d
```

### Update GeoNode

```bash
# Pull latest changes
cd /opt/geonode
git pull origin deploy/s5-production

# Pull updated images
docker-compose pull

# Restart services
docker-compose up -d

# Run migrations if needed
docker exec django4geonode python manage.py migrate

# Collect static files
docker exec django4geonode python manage.py collectstatic --noinput
```

---

## Security Recommendations

### Change Default Passwords

```bash
# Change admin password in .env BEFORE first deployment
# Edit .env:
ADMIN_PASSWORD=YOUR_SECURE_PASSWORD

# Change GeoServer admin password in .env
GEOSERVER_ADMIN_PASSWORD=YOUR_SECURE_PASSWORD

# Change database passwords
POSTGRES_PASSWORD=YOUR_SECURE_PASSWORD
GEONODE_DATABASE_PASSWORD=YOUR_SECURE_PASSWORD
GEONODE_GEODATABASE_PASSWORD=YOUR_SECURE_PASSWORD

# After changing, recreate containers
docker-compose down
docker-compose up -d
```

### Enable HTTPS

See "SSL/TLS Configuration" section above.

### Restrict Database Access

By default, PostgreSQL is not exposed externally. Keep it that way unless absolutely necessary.

### Regular Updates

```bash
# Update system packages
sudo apt-get update && sudo apt-get upgrade -y

# Update Docker images monthly
docker-compose pull
docker-compose up -d
```

### Firewall Configuration

Only expose necessary ports:
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 8081/tcp
sudo ufw allow 8443/tcp
# Don't expose 8082 if not needed externally
sudo ufw enable
```

---

## Support & Documentation

### Official Documentation
- GeoNode: https://docs.geonode.org/
- GeoServer: https://docs.geoserver.org/
- Docker Compose: https://docs.docker.com/compose/

### Additional Documentation (in this repository)
- `PORT_MIGRATION_PLAN.md` - Detailed port migration guide
- `DOMAIN_CONFIGURATION.md` - Domain-specific configuration
- `IMPLEMENTATION_SUMMARY.md` - Metadata API implementation
- `METADATA_API_DOCUMENTATION.md` - API reference

### Get Help

```bash
# Check Django system
docker exec django4geonode python manage.py check

# View Django settings
docker exec django4geonode python manage.py diffsettings

# Django shell
docker exec -it django4geonode python manage.py shell

# GeoServer REST API
curl -u admin:PASSWORD http://s5.dothanhlong.org:8082/geoserver/rest/about/version.json
```

---

## Quick Reference

### Important Paths (in containers)

| Path | Location | Purpose |
|------|----------|---------|
| `/mnt/volumes/statics/static/` | nginx, django | Static files (CSS, JS) |
| `/mnt/volumes/statics/uploaded/` | nginx, django | User uploads |
| `/geoserver_data/data/` | geoserver | GeoServer data directory |
| `/var/lib/postgresql/data/` | db | PostgreSQL data |
| `/var/lib/rabbitmq/` | rabbitmq | RabbitMQ data |

### Key Configuration Files

| File | Purpose |
|------|---------|
| `.env` | Environment variables (ports, domain, passwords) |
| `docker-compose.yml` | Production service definitions |
| `docker-compose-dev.yml` | Development service definitions |
| `geonode/settings.py` | Django settings |
| `uwsgi.ini` | uWSGI configuration |

### Environment Variables Reference

See `.env` file for all configurable variables. Key variables:

```bash
# Domain & URLs
SITEURL=http://s5.dothanhlong.org:8081/
HTTP_HOST=s5.dothanhlong.org
ALLOWED_HOSTS="['django', 'localhost', 's5.dothanhlong.org']"

# Ports
HTTP_PORT=8081
HTTPS_PORT=8443

# Database
DATABASE_URL=postgis://geonode:PASSWORD@db:5432/geonode

# GeoServer
GEOSERVER_LOCATION=http://geoserver:8080/geoserver/
GEOSERVER_PUBLIC_LOCATION=http://s5.dothanhlong.org:8081/geoserver/

# Security
DEBUG=False
SECRET_KEY=YOUR_SECRET_KEY
ADMIN_PASSWORD=YOUR_PASSWORD

# Email
ADMIN_EMAIL=admin@dothanhlong.org
DEFAULT_FROM_EMAIL='GeoNode <no-reply@dothanhlong.org>'
```

---

## Deployment Checklist

### Pre-Deployment
- [ ] DNS configured: `dig s5.dothanhlong.org +short`
- [ ] Firewall configured: ports 8081, 8443, 8082 open
- [ ] Docker installed: `docker --version`
- [ ] Docker Compose installed: `docker-compose --version`
- [ ] Sufficient disk space: `df -h` (minimum 20GB recommended)
- [ ] Changed default passwords in `.env`

### Deployment
- [ ] Cloned repository to `/opt/geonode`
- [ ] Checked out `deploy/s5-production` branch
- [ ] Verified `.env` configuration
- [ ] Pulled Docker images: `docker-compose pull`
- [ ] Started services: `docker-compose up -d`
- [ ] All containers healthy: `docker-compose ps`

### Post-Deployment
- [ ] Homepage accessible: http://s5.dothanhlong.org:8081/
- [ ] Admin login works: http://s5.dothanhlong.org:8081/admin/
- [ ] GeoServer accessible: http://s5.dothanhlong.org:8081/geoserver/
- [ ] API responding: http://s5.dothanhlong.org:8081/api/v2/
- [ ] Can upload layer
- [ ] Can create map
- [ ] OAuth2 token generation works
- [ ] Backups configured (cron job)
- [ ] Monitoring set up (optional)

---

## Success! 🎉

Your GeoNode instance is now running on **s5.dothanhlong.org**!

**Access URLs**:
- Homepage: http://s5.dothanhlong.org:8081/
- Admin: http://s5.dothanhlong.org:8081/admin/ (admin / zTCBtB1eyCasknK)
- GeoServer: http://s5.dothanhlong.org:8081/geoserver/ (admin / gmdGeNM8Icaj3VZ)

For issues or questions, refer to the troubleshooting section or check the logs:
```bash
docker-compose logs -f
```

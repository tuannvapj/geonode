# Claude Context for GeoNode QGIS Plugin API Backend

## Project Overview
This is a customized GeoNode 4.4.3 installation that serves as an API backend for QGIS plugins, specifically developed for the "CSDL ĐBS HCM" (Vietnamese geospatial database system). The project extends GeoNode's capabilities with custom APIs and Vietnamese localization.

## Technology Stack
- **Framework**: Django 4.2.17 with GeoNode 4.4.3
- **Database**: PostgreSQL with PostGIS extensions
- **API**: Django REST Framework 3.14.0 + Tastypie hybrid
- **Authentication**: OAuth2 with Bearer token support
- **Spatial Backend**: GeoServer for spatial data services
- **Task Queue**: Celery with Redis/RabbitMQ
- **Frontend**: MapStore client integration
- **Testing**: pytest, pytest-django, selenium

## Project Structure
```
geonode/                    # Main Django project directory
├── api/                    # Core API endpoints and views
├── people/                 # User management and profiles
├── layers/                 # Geospatial dataset management
├── maps/                   # Web map composition
├── documents/              # Document/metadata management
├── groups/                 # Organization/group access control
├── security/               # Permission system
├── base/                   # Core models and utilities
├── geoserver/              # GeoServer integration
├── harvesting/             # Metadata harvesting
├── settings.py             # Main Django settings
└── urls.py                 # URL routing

csdl_api/                   # Custom Vietnamese transport API
├── views.py                # Custom ViewSets
├── urls.py                 # API routing
├── permissions.py          # Custom permissions
└── models.py               # Custom data models
```

## Key Development Areas

### API Development
- **Main API Router**: Uses dynamic-rest for advanced querying
- **Authentication**: Multi-method auth (session, OAuth2, Bearer tokens)
- **QGIS Integration**: Special endpoints for QGIS plugin authentication
- **Swagger Docs**: Available at `/api/schema/swagger-ui/`

### Database Models
- **ResourceBase**: Core model for all geospatial resources
- **Profile**: Extended user model with custom fields
- **Layer**: Geospatial dataset model with permissions
- **Map**: Web map composition model
- **GroupProfile**: Organization/group management

### Custom Extensions
- **CSDL API**: Located in `/csdl_api/` directory
- **Vietnamese Localization**: Full translation support
- **Custom User Fields**: Extended profile information
- **Transport Data**: Specialized endpoints for infrastructure data

## Development Commands

### Running the Application
```bash
# Development server
python manage.py runserver

# With Docker
docker-compose -f docker-compose-dev.yml up

# Run tests
python manage.py test
pytest

# Database migrations
python manage.py makemigrations
python manage.py migrate
```

### Code Quality
```bash
# Linting
flake8
black .

# Type checking (if configured)
mypy geonode/
```

## API Endpoints

### Core GeoNode APIs
- `GET /api/v2/` - Main API root
- `GET /api/o/userinfo/` - User information (QGIS plugin auth)
- `GET /api/v2/layers/` - Layer management
- `GET /api/v2/maps/` - Map management
- `GET /api/v2/documents/` - Document management
- `GET /api/v2/users/` - User management

### Custom CSDL API
- `GET /api/csdl/duong-bo/` - Transport/road data endpoint

### Authentication
- OAuth2 Bearer token: `Authorization: Bearer <token>`
- Session authentication for web interface
- Query parameter: `?access_token=<token>`

## Configuration Files
- **Settings**: `geonode/settings.py` (main configuration)
- **Environment**: `.env` file for environment variables
- **Docker**: `docker-compose-dev.yml` for development
- **Requirements**: `requirements.txt` for Python dependencies

## Vietnamese Localization
- Translation files in `geonode/locale/vi/LC_MESSAGES/`
- Custom Vietnamese language support
- Localized user interface and API responses

## Security Considerations
- Permission-based access control system
- OAuth2 token validation
- CSRF protection for web interface
- Group-based resource access
- Granular permissions (read, write, download, admin)

## QGIS Plugin Integration Points
1. **Authentication**: Bearer token support in `/api/o/userinfo/`
2. **Resource Access**: RESTful endpoints for spatial data
3. **User Profile**: Extended user information for plugin use
4. **Permissions**: Group-based access control
5. **Data Formats**: Support for SHP, KML, CSV, and OGC services

## Development Workflow
1. **Models**: Define in appropriate app's `models.py`
2. **APIs**: Create ViewSets in `api/views.py` or app-specific API modules
3. **Permissions**: Use custom permission classes in `permissions.py`
4. **URLs**: Register in `urls.py` files
5. **Tests**: Write tests in `tests.py` or dedicated test modules
6. **Migrations**: Run after model changes

## Monitoring and Logging
- Django logging configured in settings
- Monitoring app available for system metrics
- Celery task monitoring
- GeoServer integration monitoring

## Common Issues and Solutions
- **QGIS Plugin Auth**: Ensure Bearer token is properly formatted
- **Permissions**: Check user groups and resource permissions
- **GeoServer**: Verify GeoServer connection and layer publishing
- **Database**: Ensure PostGIS extensions are properly installed
- **Static Files**: Run `collectstatic` for production deployments

## Branch Information
- **Current Branch**: geonode-4.4.3
- **Main Branch**: master
- **Recent Changes**: Custom user fields, API enhancements, CSDL app integration
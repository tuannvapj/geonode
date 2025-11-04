# Dataset Upload API Documentation

## Overview

The `/api/v2/uploads/upload/` endpoint allows you to upload geospatial datasets with rich metadata including keywords, descriptions, and category labels.

## Endpoint

```
POST /api/v2/uploads/upload/
```

## Authentication

Required. Use one of the following methods:
- Session authentication (browser)
- Basic authentication (username:password)
- OAuth2 Bearer token

## Content Type

```
multipart/form-data
```

## Request Parameters

### Required Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `base_file` | File | The main geospatial file (e.g., .shp, .tif, .zip) |

### Optional Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `dataset_title` | String | Display title for the dataset | "Vietnam Administrative Boundaries" |
| `description` | String | Detailed description/abstract of the dataset | "Official administrative boundaries for Vietnam updated 2024" |
| `keywords` | String | Comma-separated keywords for search and categorization | "vietnam, boundaries, administrative, gis" |
| `labels` | String | Comma-separated category labels | "Irrigation, Basemap, Remote Sensing" |
| `charset` | String | Character encoding (default: UTF-8) | "UTF-8" |
| `permissions` | String | JSON permissions object | `{"users": {"AnonymousUser": ["view_resourcebase"]}}` |
| `time` | String | Enable time dimension | "true" or "false" |

### Shapefile Additional Files

For shapefiles, you should also upload the following components:

| Parameter | Type | Description |
|-----------|------|-------------|
| `dbf_file` | File | DBF attribute file (.dbf) |
| `shx_file` | File | Shape index file (.shx) |
| `prj_file` | File | Projection file (.prj) |
| `xml_file` | File | Optional metadata file (.xml) |
| `sld_file` | File | Optional style file (.sld) |

## Supported File Formats

- **Shapefiles**: .shp (requires .dbf and .shx)
- **GeoTIFF**: .tif, .tiff, .geotiff, .geotif
- **Zipped files**: .zip
- **CSV**: .csv
- **KML**: .kml

## Response Format

### Success Response (201 Created)

```json
{
  "success": true,
  "execution_id": "550e8400-e29b-41d4-a716-446655440000",
  "upload_id": 123,
  "message": "Upload initiated successfully. Use the execution_id to track progress.",
  "metadata": {
    "title": "Vietnam Administrative Boundaries",
    "description": "Official administrative boundaries for Vietnam",
    "keywords": ["vietnam", "boundaries", "administrative", "gis"],
    "labels": ["Basemap", "Administrative"]
  }
}
```

### Error Responses

#### 400 Bad Request
```json
{
  "success": false,
  "errors": ["base_file is required"],
  "code": "missing_file"
}
```

#### 403 Forbidden
```json
{
  "success": false,
  "errors": ["Authentication required"],
  "code": "authentication_required"
}
```

#### 500 Internal Server Error
```json
{
  "success": false,
  "errors": ["Upload failed: <error details>"],
  "code": "upload_error"
}
```

## Usage Examples

### Example 1: Upload a Shapefile with Metadata (Python)

```python
import requests

url = "http://localhost:8000/api/v2/uploads/upload/"

# Prepare files
files = {
    'base_file': open('/Users/tuannguyen/Desktop/plugin-csdl-db-hcm/data/HanhChinh_GiaoThong_ThuyHe/ThuyHe_line_fields_remove.shp', 'rb'),
    'dbf_file': open('/Users/tuannguyen/Desktop/plugin-csdl-db-hcm/data/HanhChinh_GiaoThong_ThuyHe/ThuyHe_line_fields_remove.dbf', 'rb'),
    'shx_file': open('/Users/tuannguyen/Desktop/plugin-csdl-db-hcm/data/HanhChinh_GiaoThong_ThuyHe/ThuyHe_line_fields_remove.shx', 'rb'),
    'prj_file': open('/Users/tuannguyen/Desktop/plugin-csdl-db-hcm/data/HanhChinh_GiaoThong_ThuyHe/ThuyHe_line_fields_remove.prj', 'rb'),
}

# Prepare metadata
data = {
    'dataset_title': 'Vietnam Administrative Boundaries',
    'description': 'Official administrative boundaries for Vietnam updated 2024',
    'keywords': 'vietnam, boundaries, administrative, gis',
    'labels': 'Basemap, Administrative',
    'charset': 'UTF-8',
}

# Make request with authentication
response = requests.post(
    url,
    files=files,
    data=data,
    auth=('username', 'password')
)

print(response.json())
```

### Example 2: Upload a GeoTIFF (Python)

```python
import requests

url = "http://localhost:8000/api/v2/uploads/upload/"

files = {
    'base_file': open('satellite_image.tif', 'rb'),
}

data = {
    'dataset_title': 'Sentinel-2 Satellite Image - Hanoi',
    'description': 'Sentinel-2 multispectral image of Hanoi captured on 2024-01-15',
    'keywords': 'satellite, sentinel, hanoi, remote sensing',
    'labels': 'Remote Sensing, Imagery',
}

response = requests.post(url, files=files, data=data, auth=('username', 'password'))
print(response.json())
```

### Example 3: Upload with OAuth2 Bearer Token (cURL)

```bash
curl -X POST http://localhost:8000/api/v2/uploads/upload/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "base_file=@/path/to/data.shp" \
  -F "dbf_file=@/path/to/data.dbf" \
  -F "shx_file=@/path/to/data.shx" \
  -F "prj_file=@/path/to/data.prj" \
  -F "dataset_title=My Dataset" \
  -F "description=This is my dataset description" \
  -F "keywords=keyword1, keyword2, keyword3" \
  -F "labels=Irrigation, Basemap"
```

### Example 4: QGIS Plugin Integration (Python)

```python
from qgis.core import QgsNetworkAccessManager
from PyQt5.QtNetwork import QNetworkRequest, QNetworkReply
from PyQt5.QtCore import QUrl, QFile, QIODevice

def upload_layer_to_geonode(layer_path, token, metadata):
    """Upload a QGIS layer to GeoNode with metadata."""

    url = QUrl("http://localhost:8000/api/v2/uploads/upload/")
    request = QNetworkRequest(url)
    request.setRawHeader(b"Authorization", f"Bearer {token}".encode())

    # Create multipart form data
    from PyQt5.QtNetwork import QHttpMultiPart, QHttpPart
    multipart = QHttpMultiPart(QHttpMultiPart.FormDataType)

    # Add file
    file_part = QHttpPart()
    file_part.setHeader(QNetworkRequest.ContentDispositionHeader,
                       f'form-data; name="base_file"; filename="{os.path.basename(layer_path)}"')
    file = QFile(layer_path)
    file.open(QIODevice.ReadOnly)
    file_part.setBodyDevice(file)
    multipart.append(file_part)

    # Add metadata
    for key, value in metadata.items():
        part = QHttpPart()
        part.setHeader(QNetworkRequest.ContentDispositionHeader, f'form-data; name="{key}"')
        part.setBody(str(value).encode())
        multipart.append(part)

    # Send request
    manager = QgsNetworkAccessManager.instance()
    reply = manager.post(request, multipart)

    # Handle response
    reply.finished.connect(lambda: handle_upload_response(reply))

def handle_upload_response(reply):
    """Handle the upload response."""
    if reply.error() == QNetworkReply.NoError:
        response = reply.readAll().data().decode('utf-8')
        print(f"Upload successful: {response}")
    else:
        print(f"Upload failed: {reply.errorString()}")
```

## Tracking Upload Progress

Use the returned `execution_id` to track the upload progress:

```python
import requests

execution_id = "550e8400-e29b-41d4-a716-446655440000"
url = f"http://localhost:8000/api/v2/executionrequest/{execution_id}/"

response = requests.get(url, auth=('username', 'password'))
status = response.json()

print(f"Status: {status['status']}")
print(f"Progress: {status.get('step', 'N/A')}")
```

## Common Label Categories

Here are some common label categories you can use:

- **Irrigation**: Water management and irrigation systems
- **Basemap**: Base cartographic layers (boundaries, roads, etc.)
- **Meteorology & Hydrology**: Weather and water data
- **Remote Sensing**: Satellite and aerial imagery
- **Transportation**: Roads, railways, airports
- **Land Use**: Land cover and land use classification
- **Environmental**: Environmental monitoring data
- **Infrastructure**: Buildings, utilities, facilities
- **Agriculture**: Agricultural data and analysis
- **Demographics**: Population and census data

## Best Practices

1. **File Size**: Keep files under 500MB for optimal performance
2. **Keywords**: Use 3-10 relevant keywords per dataset
3. **Labels**: Select 1-3 category labels that best describe your data
4. **Description**: Provide a clear, concise description (100-500 characters)
5. **Shapefiles**: Always upload all required components (.shp, .dbf, .shx, .prj)
6. **Permissions**: Set appropriate permissions based on data sensitivity
7. **Charset**: Specify correct charset for non-UTF8 data to prevent encoding issues

## Troubleshooting

### Issue: "base_file is required"
**Solution**: Ensure you're sending the file with the parameter name `base_file`.

### Issue: "File type .xyz not supported"
**Solution**: Check that your file extension is in the supported formats list.

### Issue: "Missing required shapefile components"
**Solution**: For shapefiles, upload all required files (.shp, .dbf, .shx, .prj).

### Issue: Authentication errors
**Solution**: Verify your credentials or token is valid and has upload permissions.

## API Specification

The endpoint is documented in the OpenAPI/Swagger specification available at:

```
/api/schema/swagger-ui/
```

## Support

For issues or questions, please consult:
- GeoNode Documentation: https://docs.geonode.org/
- Project Repository: https://github.com/GeoNode/geonode
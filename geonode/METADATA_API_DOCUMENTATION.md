# Dataset Metadata Edit API Documentation

## Overview

The Metadata Edit API allows authenticated users to view and update metadata for existing datasets. This API is designed specifically for QGIS plugin integration, enabling users to edit metadata **after** successful upload.

## Base URL

```
http://localhost:8000/api/v2/datasets/{dataset_id}/metadata_fields/
```

## Authentication

All endpoints require authentication using one of the following methods:

- **Bearer Token**: `Authorization: Bearer YOUR_TOKEN`
- **Session Authentication**: Cookie-based (for web interface)
- **Basic Authentication**: `Authorization: Basic BASE64_ENCODED_CREDENTIALS`

## Endpoints

### GET /api/v2/datasets/{dataset_id}/metadata_fields/

Retrieve current metadata for a dataset. Use this to pre-fill edit dialogs.

#### Permissions Required
- `base.view_resourcebase` - User must have view permission for the dataset

#### Request Example

```bash
curl --location 'http://localhost:8000/api/v2/datasets/28/metadata_fields/' \
--header 'Authorization: Bearer YOUR_TOKEN'
```

#### Response Example (200 OK)

```json
{
  "id": 28,
  "uuid": "123e4567-e89b-12d3-a456-426614174000",
  "title": "HienTrangSDD_2020",
  "description": "Hiện trạng sử dụng đất 2020",
  "abstract": "Hiện trạng sử dụng đất 2020",
  "keywords": ["hiện trạng", "sử dụng đất", "2020"],
  "labels": ["Bản đồ nền"],
  "regions": ["HCMC"],
  "category": "farming"
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Dataset ID |
| `uuid` | string | Dataset UUID |
| `title` | string | Dataset title |
| `description` | string | Dataset description (alias for abstract) |
| `abstract` | string | Dataset abstract (same as description) |
| `keywords` | array | List of keyword strings |
| `labels` | array | Vietnamese category labels |
| `regions` | array | Geographic regions |
| `category` | string | ISO topic category identifier |

---

### PATCH /api/v2/datasets/{dataset_id}/metadata_fields/

Update metadata fields for an existing dataset.

#### Permissions Required
- `base.change_resourcebase_metadata` - User must have edit permission for the dataset

#### Request Example

```bash
curl --location --request PATCH 'http://localhost:8000/api/v2/datasets/28/metadata_fields/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer YOUR_TOKEN' \
--data '{
  "title": "HienTrangSDD_2020",
  "description": "Hiện trạng sử dụng đất năm 2020",
  "keywords": ["hiện trạng", "sử dụng đất", "2020"],
  "labels": ["Bản đồ nền"],
  "regions": ["HCMC"]
}'
```

#### Request Body Fields

All fields are **optional**. Only include fields you want to update.

| Field | Type | Format | Description |
|-------|------|--------|-------------|
| `title` | string | Plain text | Dataset title |
| `description` | string | Plain text | Dataset description |
| `abstract` | string | Plain text | Dataset abstract (alias for description) |
| `keywords` | array or string | `["kw1", "kw2"]` or `"kw1,kw2"` | Keywords |
| `labels` | array or string | `["label1"]` or `"label1,label2"` | Vietnamese labels |
| `regions` | array or string | `["region1"]` or `"region1,region2"` | Geographic regions |

#### Supported Vietnamese Labels

- `Thuỷ lợi` - Irrigation/water resources
- `Bản đồ nền` - Base maps
- `Khí tượng thuỷ văn` - Meteorology/hydrology
- `Viễn thám` - Remote sensing

Labels are stored as keywords and automatically appear in the `labels` field in GET responses.

#### Response Example (200 OK)

```json
{
  "success": true,
  "message": "Metadata successfully updated",
  "dataset": {
    "id": 28,
    "uuid": "123e4567-e89b-12d3-a456-426614174000",
    "title": "HienTrangSDD_2020",
    "description": "Hiện trạng sử dụng đất năm 2020",
    "keywords": ["hiện trạng", "sử dụng đất", "2020", "Bản đồ nền"],
    "regions": ["HCMC"]
  }
}
```

#### Error Responses

**400 Bad Request** - Invalid payload

```json
{
  "error": "title must be a string"
}
```

**403 Forbidden** - Permission denied

```json
{
  "detail": "You do not have permission to perform this action."
}
```

**404 Not Found** - Dataset not found

```json
{
  "detail": "Not found."
}
```

**500 Internal Server Error** - Server error

```json
{
  "error": "Failed to update metadata: ..."
}
```

---

## Python Usage Examples

### Example 1: Get Metadata for Pre-filling Edit Dialog

```python
import requests

# Configuration
base_url = "http://localhost:8000"
dataset_id = 28
token = "YOUR_BEARER_TOKEN"

# GET request
url = f"{base_url}/api/v2/datasets/{dataset_id}/metadata_fields/"
headers = {"Authorization": f"Bearer {token}"}

response = requests.get(url, headers=headers)

if response.status_code == 200:
    metadata = response.json()
    print(f"Title: {metadata['title']}")
    print(f"Description: {metadata['description']}")
    print(f"Keywords: {metadata['keywords']}")
    print(f"Labels: {metadata['labels']}")
else:
    print(f"Error: {response.status_code} - {response.text}")
```

### Example 2: Update Metadata After Upload

```python
import requests

# Configuration
base_url = "http://localhost:8000"
dataset_id = 28
token = "YOUR_BEARER_TOKEN"

# Prepare metadata
metadata = {
    "title": "HienTrangSDD_2020",
    "description": "Hiện trạng sử dụng đất năm 2020",
    "keywords": ["hiện trạng", "sử dụng đất", "2020"],
    "labels": ["Bản đồ nền"],
    "regions": ["HCMC"]
}

# PATCH request
url = f"{base_url}/api/v2/datasets/{dataset_id}/metadata_fields/"
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

response = requests.patch(url, json=metadata, headers=headers)

if response.status_code == 200:
    result = response.json()
    print(f"✓ {result['message']}")
    print(f"Updated dataset: {result['dataset']}")
else:
    print(f"✗ Error: {response.status_code} - {response.text}")
```

### Example 3: Partial Update (Only Some Fields)

```python
import requests

# Configuration
base_url = "http://localhost:8000"
dataset_id = 28
token = "YOUR_BEARER_TOKEN"

# Update only title and keywords
partial_update = {
    "title": "New Title",
    "keywords": ["new", "keywords"]
}

url = f"{base_url}/api/v2/datasets/{dataset_id}/metadata_fields/"
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

response = requests.patch(url, json=partial_update, headers=headers)

if response.status_code == 200:
    print("✓ Metadata updated successfully")
else:
    print(f"✗ Error: {response.text}")
```

---

## QGIS Plugin Integration Workflow

### Step 1: Upload Dataset

User uploads a dataset through QGIS plugin using existing upload mechanism.

```python
# Upload dataset (existing code)
upload_response = upload_dataset(file_path)
dataset_id = upload_response['dataset_id']
```

### Step 2: Show "Edit Metadata" Button

After successful upload, show a button/dialog to edit metadata.

```python
if upload_response['success']:
    show_edit_metadata_button(dataset_id)
```

### Step 3: Pre-fill Edit Dialog

When user clicks "Edit Metadata", fetch current metadata to pre-fill the form.

```python
def prefill_metadata_dialog(dataset_id, token):
    url = f"{base_url}/api/v2/datasets/{dataset_id}/metadata_fields/"
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        metadata = response.json()

        # Pre-fill form fields
        dialog.title_field.setText(metadata['title'])
        dialog.description_field.setPlainText(metadata['description'])
        dialog.keywords_field.setText(', '.join(metadata['keywords']))
        dialog.labels_combo.setCurrentText(metadata['labels'][0] if metadata['labels'] else '')

        return True
    else:
        show_error("Failed to load metadata")
        return False
```

### Step 4: Submit Metadata Update

When user clicks "Save" in the edit dialog, send PATCH request.

```python
def save_metadata(dataset_id, token, title, description, keywords, labels):
    url = f"{base_url}/api/v2/datasets/{dataset_id}/metadata_fields/"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "title": title,
        "description": description,
        "keywords": keywords.split(','),
        "labels": [labels]
    }

    response = requests.patch(url, json=payload, headers=headers)

    if response.status_code == 200:
        show_success("Metadata updated successfully!")
        refresh_dataset_list()  # Refresh Data Source table
        return True
    else:
        show_error(f"Failed to update metadata: {response.text}")
        return False
```

### Step 5: Refresh Data Source Table

After successful update, refresh the dataset list to show updated metadata.

```python
def refresh_dataset_list():
    # Call GET /api/v2/datasets/ to refresh the table
    # Updated metadata will now appear in description, keyword_list, labels columns
    load_datasets()
```

---

## Verification

After updating metadata via PATCH, you can verify the changes by:

1. **GET the same dataset**:
   ```bash
   curl http://localhost:8000/api/v2/datasets/28/metadata_fields/ \
   -H "Authorization: Bearer TOKEN"
   ```

2. **Check dataset list** (QGIS plugin Data Source table):
   ```bash
   curl http://localhost:8000/api/v2/datasets/ \
   -H "Authorization: Bearer TOKEN"
   ```

   The response will include updated `description`, `keyword_list`, and `labels` fields.

3. **Check dataset detail page**:
   Visit `http://localhost:8000/datasets/28/` in web browser to see updated metadata.

---

## Testing

### Manual Testing with cURL

**Test GET:**
```bash
curl -X GET http://localhost:8000/api/v2/datasets/28/metadata_fields/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Test PATCH:**
```bash
curl -X PATCH http://localhost:8000/api/v2/datasets/28/metadata_fields/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Title",
    "description": "Test Description",
    "keywords": ["test", "metadata"],
    "labels": ["Bản đồ nền"]
  }'
```

### Python Testing Script

```python
#!/usr/bin/env python3
"""Test metadata edit API"""

import requests
import json

BASE_URL = "http://localhost:8000"
TOKEN = "YOUR_TOKEN_HERE"
DATASET_ID = 28

def test_get_metadata():
    """Test GET /api/v2/datasets/{id}/metadata_fields/"""
    print("Testing GET metadata...")

    url = f"{BASE_URL}/api/v2/datasets/{DATASET_ID}/metadata_fields/"
    headers = {"Authorization": f"Bearer {TOKEN}"}

    response = requests.get(url, headers=headers)

    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

    return response.status_code == 200

def test_patch_metadata():
    """Test PATCH /api/v2/datasets/{id}/metadata_fields/"""
    print("\nTesting PATCH metadata...")

    url = f"{BASE_URL}/api/v2/datasets/{DATASET_ID}/metadata_fields/"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "title": "Test Dataset Updated",
        "description": "This is a test description",
        "keywords": ["test", "metadata", "api"],
        "labels": ["Bản đồ nền"]
    }

    response = requests.patch(url, headers=headers, json=payload)

    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

    return response.status_code == 200

if __name__ == "__main__":
    print("=== Metadata Edit API Tests ===\n")

    get_success = test_get_metadata()
    patch_success = test_patch_metadata()

    print("\n=== Results ===")
    print(f"GET:   {'✓ PASS' if get_success else '✗ FAIL'}")
    print(f"PATCH: {'✓ PASS' if patch_success else '✗ FAIL'}")
```

---

## Troubleshooting

### Issue: 403 Forbidden

**Cause**: User doesn't have permission to edit the dataset.

**Solution**: Ensure the authenticated user is the owner or has edit permissions for the dataset.

### Issue: 404 Not Found

**Cause**: Dataset ID doesn't exist.

**Solution**: Verify the dataset ID is correct by checking `/api/v2/datasets/`.

### Issue: 400 Bad Request

**Cause**: Invalid payload format (e.g., keywords is a number instead of list/string).

**Solution**: Check the error message in response and fix the payload format.

### Issue: Metadata Not Appearing in Dataset List

**Cause**: Dataset list wasn't refreshed after update.

**Solution**: Call `GET /api/v2/datasets/` again to fetch the updated list.

---

## Migration from Old Approach

If you were using the previous upload-time metadata approach, here's how to migrate:

### Before (Old Approach)
```python
# Send metadata during upload (UNRELIABLE)
upload_data = {
    'base_file': file,
    'dataset_title': 'Title',
    'description': 'Description',
    # ... metadata sent with upload
}
# Hope signal handler applies it (often failed)
```

### After (New Approach)
```python
# Step 1: Upload file (no metadata)
upload_response = upload_dataset(file)
dataset_id = upload_response['dataset_id']

# Step 2: Edit metadata after upload (RELIABLE)
metadata = {
    'title': 'Title',
    'description': 'Description',
    'keywords': ['keyword1', 'keyword2']
}
update_metadata(dataset_id, metadata)
```

### Benefits of New Approach

1. **Reliability**: Direct database update, no caching or signal handlers
2. **User Control**: Explicit metadata editing, not automatic
3. **Testability**: Simple API endpoints, easy to test
4. **Debuggability**: Clear success/error responses
5. **Flexibility**: Update metadata anytime, not just during upload

---

## Related Endpoints

- `GET /api/v2/datasets/` - List all datasets (includes `description`, `keyword_list`, `labels` fields)
- `GET /api/v2/datasets/{id}/` - Get dataset detail
- `GET /api/o/userinfo/` - Get current user info (for authentication)

---

## Support

For issues or questions:
- Check logs: `docker-compose logs -f django`
- Report issues: https://github.com/anthropics/geonode/issues
- API docs: http://localhost:8000/api/schema/swagger-ui/

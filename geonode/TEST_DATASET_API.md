# Testing Dataset API New Fields

## Changes Made

Added three new fields to the `/api/v2/datasets/` endpoint:

1. **description** - Alias for the `abstract` field (already exists as `abstract`)
2. **keyword_list** - Array of keyword strings (simplified from the complex `keywords` object)
3. **labels** - Array of Vietnamese category labels

## Required: Restart Django Server

After modifying the serializers, you **MUST restart** the Django/GeoNode server for changes to take effect:

### If running with Docker:

```bash
# Restart the Django container
docker-compose restart django

# Or restart all services
docker-compose restart

# Check logs
docker-compose logs -f django
```

### If running directly:

```bash
# Stop the server (Ctrl+C)
# Then restart
python manage.py runserver

# Or with gunicorn
gunicorn geonode.wsgi:application --reload
```

## Test the API

### 1. Basic Test - Check if fields are present

```bash
curl -H "Authorization: Bearer M5C0X0zpjc4ZOv3gr8qMmWVVVQZzle" \
  "http://localhost/api/v2/datasets/" | jq '.datasets[0] | keys'
```

This should show all available fields including `description`, `keyword_list`, and `labels`.

### 2. View Specific Fields

```bash
# View just the new fields
curl -H "Authorization: Bearer M5C0X0zpjc4ZOv3gr8qMmWVVVQZzle" \
  "http://localhost/api/v2/datasets/" | \
  jq '.datasets[] | {title, description, keyword_list, labels}'
```

### 3. Get Single Dataset

```bash
# Replace {id} with actual dataset ID
curl -H "Authorization: Bearer M5C0X0zpjc4ZOv3gr8qMmWVVVQZzle" \
  "http://localhost/api/v2/datasets/{id}/" | \
  jq '{title, description, keyword_list, labels, abstract, keywords}'
```

### 4. Python Test Script

Create a file `test_api.py`:

```python
import requests
import json

url = "http://localhost/api/v2/datasets/"
headers = {"Authorization": "Bearer M5C0X0zpjc4ZOv3gr8qMmWVVVQZzle"}

response = requests.get(url, headers=headers)

if response.status_code == 200:
    data = response.json()
    datasets = data.get('datasets', [])

    print(f"Found {len(datasets)} datasets\n")

    for dataset in datasets[:3]:  # Show first 3
        print(f"=" * 60)
        print(f"Title: {dataset.get('title')}")
        print(f"Description: {dataset.get('description', 'N/A')[:100]}...")
        print(f"Abstract: {dataset.get('abstract', 'N/A')[:100]}...")
        print(f"Keyword List: {dataset.get('keyword_list', [])}")
        print(f"Labels: {dataset.get('labels', [])}")
        print(f"Keywords (full): {[k.get('name') for k in dataset.get('keywords', [])]}")
        print()

        # Verify new fields exist
        has_description = 'description' in dataset
        has_keyword_list = 'keyword_list' in dataset
        has_labels = 'labels' in dataset

        print(f"✓ Has 'description': {has_description}")
        print(f"✓ Has 'keyword_list': {has_keyword_list}")
        print(f"✓ Has 'labels': {has_labels}")
        print()
else:
    print(f"Error: {response.status_code}")
    print(response.text)
```

Run it:

```bash
python test_api.py
```

## Expected Response Format

```json
{
  "datasets": [
    {
      "pk": 123,
      "title": "Dataset Title",
      "abstract": "Full abstract text here...",
      "description": "Full abstract text here...",
      "keywords": [
        {
          "name": "keyword1",
          "slug": "keyword1"
        }
      ],
      "keyword_list": ["keyword1", "keyword2", "keyword3"],
      "labels": ["Thuỷ lợi", "Bản đồ nền"],
      "category": {
        "identifier": "inlandWaters",
        "gn_description": "Inland Waters"
      },
      ...
    }
  ]
}
```

## Troubleshooting

### Issue 1: Fields not showing up after restart

**Problem**: New fields `description`, `keyword_list`, `labels` are not in the response.

**Solutions**:

1. **Clear Python bytecode cache**:
```bash
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -delete
```

2. **Verify serializer is loaded**:
```bash
# In Django shell
python manage.py shell

from geonode.layers.api.serializers import DatasetListSerializer
serializer = DatasetListSerializer()
print(serializer.get_fields().keys())
# Should see 'description', 'keyword_list', 'labels'
```

3. **Check for syntax errors**:
```bash
python manage.py check
```

4. **Full restart with cache clear**:
```bash
# Docker
docker-compose down
docker-compose up -d

# Direct
rm -rf **/__pycache__
python manage.py runserver
```

### Issue 2: Empty values

**Problem**: Fields exist but return empty values `[]` or `""`.

**Solutions**:

1. **Check if dataset has keywords**:
```bash
curl -H "Authorization: Bearer M5C0X0zpjc4ZOv3gr8qMmWVVVQZzle" \
  "http://localhost/api/v2/datasets/{id}/" | jq '.keywords'
```

2. **Check if dataset has category**:
```bash
curl -H "Authorization: Bearer M5C0X0zpjc4ZOv3gr8qMmWVVVQZzle" \
  "http://localhost/api/v2/datasets/{id}/" | jq '.category'
```

3. **Add test data via Django admin**:
   - Go to `/admin/layers/dataset/{id}/change/`
   - Add keywords and select a category
   - Save and test API again

### Issue 3: Server errors

**Problem**: Getting 500 errors after changes.

**Solutions**:

1. **Check Django logs**:
```bash
# Docker
docker-compose logs django

# Direct
# Check console output
```

2. **Verify imports**:
```python
# In Django shell
python manage.py shell

try:
    from geonode.layers.api.serializers import DatasetSerializer, DatasetListSerializer
    print("✓ Imports successful")
except Exception as e:
    print(f"✗ Import error: {e}")
```

3. **Check for circular imports**:
```bash
python -c "from geonode.layers.api.serializers import DatasetSerializer"
```

## Verify Changes in Code

To verify the code changes were applied:

```bash
# Check if new fields are in serializer
grep -A 5 "keyword_list\|labels\|description" geonode/layers/api/serializers.py

# Should see:
# description = serializers.CharField(source='abstract', read_only=True)
# keyword_list = serializers.SerializerMethodField()
# labels = serializers.SerializerMethodField()
```

## Integration with Plugin

Once confirmed working, update your plugin to use these fields:

```python
# In your QGIS plugin
response = requests.get(
    "http://localhost/api/v2/datasets/",
    headers={"Authorization": f"Bearer {token}"}
)

for dataset in response.json()['datasets']:
    # Use simplified fields
    title = dataset['title']
    description = dataset.get('description', '')  # or use 'abstract'
    keywords = dataset.get('keyword_list', [])     # Simple list
    labels = dataset.get('labels', [])             # Vietnamese labels

    # Display in UI
    print(f"{title}: {', '.join(labels)}")
```

## Notes

1. The `description` field is an **alias** for `abstract` - both will have the same value
2. The `keyword_list` field is a **simplified version** of `keywords` - just an array of strings
3. The `labels` field is **computed on-the-fly** from:
   - ISO topic category (mapped to Vietnamese)
   - Keywords matching Vietnamese label names
4. All three fields are **read-only**

## Support

If issues persist after restart:
1. Check Django version compatibility
2. Verify DRF (Django Rest Framework) version
3. Check for any middleware that might filter response fields
4. Enable Django debug mode and check detailed error messages
# Upload Metadata Implementation

## Overview

This document describes the implementation of metadata support for dataset uploads in GeoNode, specifically designed to work with the QGIS plugin.

## Problem Statement

The QGIS plugin was sending metadata fields (`dataset_title`, `description`, `keywords`, `labels`) during upload, but the GeoNode server was not persisting this metadata to the created datasets. The metadata was stored in `ExecutionRequest.input_params` but never applied to the actual Dataset objects.

## Solution

We've implemented a complete workflow that:

1. **Accepts metadata** during upload via the REST API
2. **Stores metadata** in ExecutionRequest.input_params for async processing
3. **Processes uploads asynchronously** using Celery workers
4. **Applies metadata** to datasets after they are created

## Implementation Details

### 1. New Upload Endpoint

**File**: `geonode/upload/api/views.py`

Added a new endpoint `upload_with_metadata()` that:
- Accepts file uploads with metadata fields
- Creates an ExecutionRequest to track the upload
- Saves files to temporary directory
- Queues a Celery task for async processing
- Returns execution_id for status tracking

**Endpoint**: `POST /api/v2/uploads/upload_with_metadata/`

**Parameters**:
- `base_file`: Main file (shapefile, GeoTIFF, etc.)
- `dataset_title`: Title for the dataset
- `description`: Description/abstract text
- `keywords`: Comma-separated keywords
- `labels`: Comma-separated labels/categories
- `charset`: Character encoding (default: UTF-8)
- `permissions`: JSON permissions object

**Response**:
```json
{
  "success": true,
  "execution_id": "uuid-here",
  "upload_id": 123,
  "message": "Upload queued successfully. Metadata will be applied after import.",
  "metadata": {
    "title": "Dataset Title",
    "description": "Description text",
    "keywords": ["keyword1", "keyword2"],
    "labels": ["Label1", "Label2"]
  }
}
```

### 2. Celery Task for Processing

**File**: `geonode/upload/tasks.py`

Added `process_upload_with_metadata()` task that:
- Retrieves the ExecutionRequest and metadata from input_params
- Finds the created Dataset (after GeoNode's importer creates it)
- Applies metadata using the helper function
- Updates ExecutionRequest status
- Links the Upload to the Dataset

**Usage**:
```python
from geonode.upload.tasks import process_upload_with_metadata
process_upload_with_metadata.delay(execution_id)
```

### 3. Metadata Helper Functions

**File**: `geonode/upload/upload_helpers.py`

Contains helper functions:

#### `apply_metadata_to_dataset(dataset, keywords, labels, description)`

Applies metadata to a Dataset instance:
- Sets `dataset.abstract` from description
- Adds keywords using django-taggit
- Adds hierarchical keywords for labels
- Saves the dataset

**Example**:
```python
from geonode.upload.upload_helpers import apply_metadata_to_dataset

dataset = Dataset.objects.get(name='my_dataset')
keywords = ['urban', 'planning', '2030']
labels = ['Sử dụng đất', 'Quy hoạch']
description = 'Urban planning dataset for 2030'

apply_metadata_to_dataset(dataset, keywords, labels, description)
```

### 4. Management Command

**File**: `geonode/upload/management/commands/apply_metadata_to_dataset.py`

A Django management command for testing and manual metadata application:

```bash
python manage.py apply_metadata_to_dataset <dataset_name_or_id> \
    --title "New Title" \
    --description "Description text" \
    --keywords "keyword1,keyword2,keyword3" \
    --labels "Label1,Label2"
```

**Example**:
```bash
python manage.py apply_metadata_to_dataset quyhoachsdd_2030 \
    --title "QuyHoachSDD_2030" \
    --description "Quy hoạch sử dụng đất năm 2030" \
    --keywords "quy hoạch,sử dụng đất,2030" \
    --labels "Sử dụng đất"
```

## Workflow

```
┌─────────────┐
│ QGIS Plugin │
└──────┬──────┘
       │ POST /api/v2/uploads/upload_with_metadata/
       │ (files + metadata)
       ↓
┌────────────────────┐
│ Upload API Endpoint│
└─────────┬──────────┘
          │ 1. Save files to temp directory
          │ 2. Create ExecutionRequest with metadata in input_params
          │ 3. Create Upload session
          │ 4. Queue Celery task
          ↓
┌──────────────────────────┐
│ Celery Task (async)      │
│ process_upload_with_     │
│ metadata()               │
└────────┬─────────────────┘
         │ 1. Get ExecutionRequest
         │ 2. Import dataset (via GeoNode importer)
         │ 3. Find created Dataset
         │ 4. Apply metadata
         │ 5. Update ExecutionRequest status
         ↓
┌──────────────────┐
│ Dataset Created  │
│ with Metadata    │
└──────────────────┘
```

## Testing

### 1. Using the Management Command

Test metadata application on an existing dataset:

```bash
python manage.py apply_metadata_to_dataset <dataset_name> \
    --title "Test Title" \
    --description "Test description" \
    --keywords "test,keywords" \
    --labels "Test Label"
```

### 2. Using Django Shell

```python
from geonode.layers.models import Dataset
from geonode.upload.upload_helpers import apply_metadata_to_dataset

# Get a dataset
ds = Dataset.objects.get(name='test_dataset')

# Apply metadata
keywords = ['keyword1', 'keyword2']
labels = ['Label1', 'Label2']
description = 'Test description'

apply_metadata_to_dataset(ds, keywords, labels, description)

# Verify
ds.refresh_from_db()
print(f'Title: {ds.title}')
print(f'Abstract: {ds.abstract}')
print(f'Keywords: {list(ds.keywords.values_list("name", flat=True))}')
```

### 3. Using the API Endpoint

Use curl or the QGIS plugin to test the upload endpoint:

```bash
curl -X POST http://localhost:8000/api/v2/uploads/upload_with_metadata/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "base_file=@test.shp" \
  -F "dbf_file=@test.dbf" \
  -F "shx_file=@test.shx" \
  -F "prj_file=@test.prj" \
  -F "dataset_title=Test Dataset" \
  -F "description=Test description" \
  -F "keywords=test,upload,metadata" \
  -F "labels=Test Category"
```

## Configuration

### Celery Settings

Ensure Celery is configured in `geonode/settings.py`:

```python
# Celery broker
CELERY_BROKER_URL = 'redis://localhost:6379/0'

# Or RabbitMQ
# CELERY_BROKER_URL = 'amqp://guest:guest@localhost:5672//'

# Task queues
CELERY_TASK_QUEUES = {
    'geonode': {
        'exchange': 'geonode',
        'routing_key': 'geonode',
    },
}
```

### Running Celery Workers

Start Celery workers to process upload tasks:

```bash
# Development
celery -A geonode.celery_app worker -l info -Q geonode

# Production
celery -A geonode.celery_app worker -l info -Q geonode -D
```

## Troubleshooting

### Issue: Metadata not applied

**Check:**
1. Is Celery worker running?
   ```bash
   ps aux | grep celery
   ```

2. Check ExecutionRequest status:
   ```python
   from geonode.resource.models import ExecutionRequest
   er = ExecutionRequest.objects.get(exec_id='your-execution-id')
   print(er.status)
   print(er.log)
   ```

3. Check Celery logs:
   ```bash
   tail -f /var/log/celery/*.log
   ```

### Issue: Dataset not found after import

**Solution:** The Celery task searches for datasets by name. If the dataset name doesn't match the filename, the task may not find it. Check the logs:

```python
import logging
logger = logging.getLogger('geonode.upload.tasks')
# Check logs for "[UPLOAD-TASK]" messages
```

### Issue: Keywords not appearing

**Check:**
- Keywords are managed by django-taggit
- Verify keywords are actually saved:
  ```python
  dataset.keywords.all()
  ```
- Check if HierarchicalKeyword was created:
  ```python
  from geonode.base.models import HierarchicalKeyword
  HierarchicalKeyword.objects.filter(name='your_keyword')
  ```

## Future Improvements

1. **Direct Import Integration**: Integrate with GeoNode's importer directly instead of waiting for datasets to be created

2. **Retry Logic**: Add retry logic if dataset is not found immediately after import

3. **Webhook Notifications**: Notify the QGIS plugin when metadata application is complete

4. **Batch Operations**: Support applying metadata to multiple datasets at once

5. **Metadata Templates**: Allow users to save metadata templates for reuse

## Related Files

- `geonode/upload/api/views.py` - Upload API endpoints
- `geonode/upload/tasks.py` - Celery tasks
- `geonode/upload/upload_helpers.py` - Helper functions
- `geonode/upload/management/commands/apply_metadata_to_dataset.py` - Management command
- `geonode/resource/models.py` - ExecutionRequest model
- `geonode/layers/models.py` - Dataset model
- `geonode/base/models.py` - HierarchicalKeyword, ResourceBase models

## References

- GeoNode Documentation: https://docs.geonode.org/
- Django REST Framework: https://www.django-rest-framework.org/
- Celery Documentation: https://docs.celeryproject.org/
- QGIS Plugin Development: https://docs.qgis.org/

---

**Created**: 2024-11-03
**Author**: Claude Code
**Version**: 1.0
**Status**: Implemented

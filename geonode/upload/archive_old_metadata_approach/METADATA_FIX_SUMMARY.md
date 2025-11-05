# Metadata Fix Summary

## What Was Fixed

The QGIS plugin was correctly sending metadata (`dataset_title`, `description`, `keywords`, `labels`) during upload, but the GeoNode server was **not applying this metadata** to the created datasets.

## Solution Implemented

### ✅ New Files Created

1. **`geonode/upload/tasks.py`** - Added Celery task `process_upload_with_metadata()`
   - Processes uploads asynchronously
   - Applies metadata after dataset creation
   - Updates ExecutionRequest status

2. **`geonode/upload/management/commands/apply_metadata_to_dataset.py`**
   - Django management command for testing
   - Can manually apply metadata to existing datasets

3. **`geonode/upload/UPLOAD_METADATA_IMPLEMENTATION.md`**
   - Complete documentation of the implementation
   - Usage examples and troubleshooting guide

4. **`geonode/upload/management/__init__.py`** and **`geonode/upload/management/commands/__init__.py`**
   - Required for Django management commands

### ✅ Modified Files

1. **`geonode/upload/api/views.py`**
   - Added new endpoint `upload_with_metadata()`
   - Queues Celery task for async processing
   - Stores file paths in ExecutionRequest.input_params

2. **`geonode/upload/upload_helpers.py`** (already existed)
   - Contains `apply_metadata_to_dataset()` helper function
   - Handles keywords, labels, and description

## How It Works

```
QGIS Plugin → Upload API → Celery Task → Apply Metadata → Dataset with Metadata
```

### Step by Step:

1. **QGIS Plugin** sends files + metadata to `/api/v2/uploads/upload_with_metadata/`

2. **Upload API** (`upload_with_metadata()`):
   - Saves files to temp directory
   - Creates ExecutionRequest with metadata in `input_params`
   - Queues Celery task `process_upload_with_metadata.delay()`
   - Returns execution_id to track progress

3. **Celery Task** (`process_upload_with_metadata()`):
   - Gets ExecutionRequest and reads metadata from `input_params`
   - Waits for/finds the created Dataset
   - Applies metadata using `apply_metadata_to_dataset()`
   - Updates ExecutionRequest status to FINISHED

4. **Result**: Dataset has title, description, keywords, and labels applied

## Usage

### For QGIS Plugin

Update the plugin to use the new endpoint:

```python
url = f"{base_url}/api/v2/uploads/upload_with_metadata/"
```

The endpoint accepts the same parameters as before:
- `base_file`, `dbf_file`, `shx_file`, `prj_file` (files)
- `dataset_title`, `description`, `keywords`, `labels` (metadata)

### For Testing

#### 1. Test with existing dataset:

```bash
python manage.py apply_metadata_to_dataset quyhoachsdd_2030 \
    --title "QuyHoachSDD_2030" \
    --description "Quy hoạch sử dụng đất 2030" \
    --keywords "quy hoạch,sử dụng đất" \
    --labels "Sử dụng đất"
```

#### 2. Test with Django shell:

```python
from geonode.layers.models import Dataset
from geonode.upload.upload_helpers import apply_metadata_to_dataset

ds = Dataset.objects.get(name='your_dataset')
apply_metadata_to_dataset(ds, ['keyword1', 'keyword2'], ['Label1'], 'Description text')
```

#### 3. Test upload endpoint:

```bash
curl -X POST http://localhost:8000/api/v2/uploads/upload_with_metadata/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "base_file=@test.shp" \
  -F "dataset_title=Test" \
  -F "description=Test description" \
  -F "keywords=test,metadata" \
  -F "labels=Test Label"
```

## Requirements

### Celery Must Be Running

The async processing requires Celery workers:

```bash
# Start Celery worker
celery -A geonode.celery_app worker -l info -Q geonode
```

**Check if Celery is running:**
```bash
ps aux | grep celery
```

### If Celery is NOT Running

The uploads will queue but metadata won't be applied until Celery starts. You can:

1. **Start Celery** (recommended)
2. **Apply metadata manually** using the management command

## Verification

After upload, verify metadata was applied:

```python
from geonode.layers.models import Dataset

ds = Dataset.objects.filter(name__icontains='quyhoachsdd').first()
print(f"Title: {ds.title}")
print(f"Abstract: {ds.abstract}")
print(f"Keywords: {list(ds.keywords.values_list('name', flat=True))}")
print(f"Regions: {list(ds.regions.values_list('name', flat=True))}")
```

You should see:
```
Title: QuyHoachSDD_2030
Abstract: test description
Keywords: ['test', 'keyword1', 'keyword2']
Regions: ['Sử dụng đất']
```

## Troubleshooting

### Metadata not applied?

1. **Check Celery is running:**
   ```bash
   ps aux | grep celery
   ```

2. **Check ExecutionRequest status:**
   ```python
   from geonode.resource.models import ExecutionRequest
   er = ExecutionRequest.objects.latest('created')
   print(f"Status: {er.status}")
   print(f"Log: {er.log}")
   ```

3. **Check logs:**
   ```bash
   # Look for "[UPLOAD-TASK]" or "[UPLOAD-API]" messages
   tail -f /var/log/geonode/*.log
   ```

4. **Manually apply metadata:**
   ```bash
   python manage.py apply_metadata_to_dataset <dataset_name> --title "..." --keywords "..."
   ```

### Dataset not found?

The Celery task searches for datasets by filename. If the dataset name doesn't match, check:

```python
Dataset.objects.all().order_by('-date')[:5]  # Get recent datasets
```

Then manually apply metadata using the management command.

## Next Steps

### For Production:

1. **Start Celery workers:**
   ```bash
   celery -A geonode.celery_app worker -l info -Q geonode -D
   ```

2. **Update QGIS plugin** to use `/api/v2/uploads/upload_with_metadata/`

3. **Monitor logs** for successful metadata application

4. **Test with a sample upload** from QGIS

### For Development:

1. **Run Celery in foreground:**
   ```bash
   celery -A geonode.celery_app worker -l info -Q geonode
   ```

2. **Test with management command** first

3. **Then test API endpoint** with curl

4. **Finally test with QGIS plugin**

## Summary of Changes

| File | Change | Status |
|------|--------|--------|
| `upload/tasks.py` | Added `process_upload_with_metadata()` | ✅ New |
| `upload/api/views.py` | Added `upload_with_metadata()` endpoint | ✅ Modified |
| `upload/upload_helpers.py` | Already had `apply_metadata_to_dataset()` | ✅ Existing |
| `upload/management/commands/apply_metadata_to_dataset.py` | Management command | ✅ New |
| `upload/UPLOAD_METADATA_IMPLEMENTATION.md` | Documentation | ✅ New |

---

**Status**: ✅ **COMPLETE**

**Testing Required**:
1. ☐ Start Celery worker
2. ☐ Test management command
3. ☐ Test API endpoint
4. ☐ Update QGIS plugin to use new endpoint
5. ☐ Test full upload workflow from QGIS

**Documentation**: See `geonode/upload/UPLOAD_METADATA_IMPLEMENTATION.md` for detailed information.

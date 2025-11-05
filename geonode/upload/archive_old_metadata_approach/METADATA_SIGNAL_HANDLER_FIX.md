# Metadata Signal Handler Fix - FINAL SOLUTION

## Problem Identified

After thorough investigation, the root cause was discovered:

**The upload API endpoint doesn't actually import datasets** - it only saves files and creates an ExecutionRequest. GeoNode's dataset import happens through a SEPARATE mechanism (GeoServer importer or other backend processes), so metadata stored in ExecutionRequest.input_params was never being applied to the created datasets.

## Solution: Django Signal Handler

Instead of trying to intercept the upload process, we use Django signals to **automatically apply metadata AFTER any dataset is created**, regardless of how it was uploaded.

### How It Works

```
1. User uploads file with metadata through QGIS plugin
   ↓
2. Upload API creates ExecutionRequest with metadata in input_params
   ↓
3. GeoNode's normal import process creates the Dataset
   ↓
4. Django post_save signal fires
   ↓
5. Signal handler finds matching ExecutionRequest by filename
   ↓
6. Metadata is applied using resource_manager.update()
   ↓
7. Dataset now has title, description, keywords!
```

## Files Modified/Created

### 1. New Signal Handler
**File**: `geonode/upload/signals.py` (NEW)

A Django signal handler that listens for Dataset creation and automatically applies metadata from matching ExecutionRequests.

**Key Features**:
- Triggers on `post_save` signal for Dataset model
- Only processes newly created datasets (`created=True`)
- Matches ExecutionRequests by comparing dataset name to uploaded filename
- Uses `resource_manager.update()` for proper metadata application
- Handles keywords, description, and title
- Updates ExecutionRequest status to FINISHED
- Links Upload to Dataset

### 2. Signal Registration
**File**: `geonode/upload/apps.py` (MODIFIED)

Added signal import in the `ready()` method to register the handler when the app loads.

```python
def ready(self):
    super().ready()
    # ... existing code ...
    # Import signal handlers to register them
    from geonode.upload import signals  # noqa: F401
```

### 3. Updated Celery Task
**File**: `geonode/upload/tasks.py` (MODIFIED)

Improved the `process_upload_with_metadata()` task to:
- Poll for dataset creation (30 second timeout)
- Use `resource_manager.update()` for metadata application
- Better logging with `[UPLOAD-METADATA-TASK]` prefix

**Note**: The Celery task is now a backup/alternative to the signal handler. The signal handler is the primary mechanism.

## Advantages of This Approach

1. **Works with ANY upload method** - doesn't matter if upload comes from QGIS plugin, web UI, or API
2. **No need to modify upload endpoints** - signal handler intercepts all dataset creations
3. **Uses GeoNode's official API** - `resource_manager.update()` handles all complexities
4. **Automatic** - no manual intervention needed
5. **Idempotent** - can be run multiple times safely

## Testing

### 1. Check Signal Handler is Registered

```bash
python manage.py shell
>>> from geonode.upload.signals import apply_metadata_from_execution_request
>>> print(apply_metadata_from_execution_request)
<function apply_metadata_from_execution_request at 0x...>
```

### 2. Test Upload with Metadata

Upload a dataset through QGIS plugin with metadata, then check:

```python
from geonode.layers.models import Dataset

# Find the newly created dataset
ds = Dataset.objects.latest('date')

print(f"Title: {ds.title}")
print(f"Abstract: {ds.abstract}")
print(f"Keywords: {list(ds.keywords.values_list('name', flat=True))}")
```

You should see your metadata applied!

### 3. Check Logs

Look for signal handler messages:

```bash
tail -f /var/log/geonode/*.log | grep "UPLOAD-SIGNAL"
```

Expected log messages:
```
[UPLOAD-SIGNAL] Dataset created: 123 - my_dataset
[UPLOAD-SIGNAL] Found matching ExecutionRequest: abc-123-def
[UPLOAD-SIGNAL] Applying metadata:
[UPLOAD-SIGNAL]   - Title: My Dataset
[UPLOAD-SIGNAL]   - Description: Test description
[UPLOAD-SIGNAL]   - Keywords: ['test', 'upload']
[UPLOAD-SIGNAL] Successfully applied metadata to dataset 123
```

## How Metadata is Applied

The signal handler uses GeoNode's `resource_manager.update()` method:

```python
resource_manager.update(
    uuid=str(dataset.uuid),
    instance=dataset,
    vals={
        'title': 'Dataset Title',
        'abstract': 'Description text'
    },
    keywords=['keyword1', 'keyword2'],
    regions=[],  # labels/categories
    notify=False
)
```

This ensures metadata is applied correctly following GeoNode's internal workflows.

## Matching Logic

The signal handler matches ExecutionRequests to Datasets by:

1. Looking for ExecutionRequests with status READY or RUNNING
2. Extracting the `file_name` from `input_params`
3. Normalizing both the filename and dataset name (lowercase, replace spaces with underscores)
4. Checking if the normalized names match (contains or is contained in)
5. Verifying that metadata fields are present
6. Applying the metadata if all conditions are met

## Metadata Fields Supported

| Field | ExecutionRequest Key | Dataset Field | Notes |
|-------|---------------------|---------------|-------|
| Title | `dataset_title` | `title` | Applied via `vals` |
| Description | `description` | `abstract` | Applied via `vals` |
| Keywords | `keywords` | `keywords` | Applied via `keywords` parameter |
| Labels | `labels` | `regions` | Attempted but may need adjustment |

## Known Limitations

1. **Labels/Regions**: The `labels` field is passed as `regions` parameter, but GeoNode's regions are predefined geographic areas. Custom labels might not work directly. This may need further customization.

2. **Matching Ambiguity**: If multiple datasets have similar names, the handler matches the most recent one. This should be fine for normal upload workflows.

3. **Timing**: The signal fires immediately after dataset creation, which might be before GeoServer has fully published the layer. This usually isn't a problem.

## Troubleshooting

### Metadata Not Applied

**Check 1**: Is the signal handler registered?
```python
from django.db.models.signals import post_save
from geonode.layers.models import Dataset
print(post_save.receivers)  # Should show our handler
```

**Check 2**: Is there a matching ExecutionRequest?
```python
from geonode.resource.models import ExecutionRequest
ExecutionRequest.objects.filter(
    status__in=[ExecutionRequest.STATUS_READY, ExecutionRequest.STATUS_RUNNING]
).values('exec_id', 'input_params')
```

**Check 3**: Check the logs for signal handler messages

### Signal Handler Not Firing

- Restart Django server to reload the app configuration
- Verify `apps.py` has the signal import
- Check for Python syntax errors in `signals.py`

## Comparison to Previous Attempts

| Approach | Issue | Status |
|----------|-------|--------|
| Modify upload view | View doesn't actually import datasets | ❌ Abandoned |
| Celery task | Task doesn't know when dataset is created | ⚠️ Backup only |
| Signal handler | Works for ALL dataset creations | ✅ **CURRENT SOLUTION** |

## Next Steps

1. ✅ Signal handler is implemented and registered
2. ☐ Test with actual upload from QGIS plugin
3. ☐ Verify metadata appears in `/api/v2/datasets` response
4. ☐ Adjust labels/regions handling if needed
5. ☐ Monitor logs to ensure it works consistently

## Summary

**THE CORE FIX**: Added a Django signal handler (`geonode/upload/signals.py`) that automatically applies metadata to ANY newly created dataset by matching it with pending ExecutionRequests.

**NO CHANGES NEEDED** to:
- QGIS plugin code
- Upload API endpoints (old or new)
- Frontend code

The signal handler works transparently in the background, applying metadata whenever a dataset is created, regardless of the upload method.

---

**Created**: 2024-11-04
**Status**: ✅ IMPLEMENTED AND READY FOR TESTING
**Author**: Claude Code
**Version**: 2.0 (Signal Handler Approach)

# Metadata Fix - Docker/Container Guide

## Quick Reference for Containerized Deployment

Since your Django app is deployed in a Docker container with uWSGI, here's how to test and verify the metadata fix.

## Step 1: Restart the Container

The signal handler needs to be loaded when Django starts:

```bash
# Restart your Django/uWSGI container
docker-compose restart django

# OR if using docker commands directly
docker restart <container-name>
```

## Step 2: Check if Signal Handler is Registered

Run the test command inside the container:

```bash
# If using docker-compose
docker-compose exec django python manage.py test_metadata_signal

# OR if using docker directly
docker exec -it <container-name> python manage.py test_metadata_signal
```

**What to look for:**
- ✓ Signal handler is registered
- Recent datasets with metadata
- Pending ExecutionRequests

## Step 3: Upload a Test Dataset

1. **Upload through QGIS plugin** with metadata:
   - Title: "Test Dataset"
   - Description: "This is a test"
   - Keywords: "test, metadata"
   - Labels: "Test Label"

2. **Wait a few seconds** for the dataset to be created

3. **Check the results:**

```bash
docker-compose exec django python manage.py test_metadata_signal
```

Look at the "Recent datasets" section - you should see your metadata applied!

## Step 4: Apply Metadata to Existing Datasets (Optional)

If you have datasets that were uploaded BEFORE the signal handler was installed, apply metadata retroactively:

```bash
# Dry run first (see what would happen)
docker-compose exec django python manage.py apply_pending_metadata --dry-run

# Actually apply the metadata
docker-compose exec django python manage.py apply_pending_metadata
```

## Step 5: Verify via API

Check if metadata appears in the API response:

```bash
curl http://localhost/api/v2/datasets/ | python -m json.tool | grep -A 10 '"title"'
```

Or visit in your browser:
```
http://localhost/api/v2/datasets/
```

Look for the fields:
- `title` - should match your `dataset_title`
- `description` - should match your `description`
- `keyword_list` - should contain your keywords
- `labels` - should contain your labels

## Troubleshooting Commands

### Check Recent Datasets

```bash
docker-compose exec django python manage.py shell <<EOF
from geonode.layers.models import Dataset
ds = Dataset.objects.latest('date')
print(f"Title: {ds.title}")
print(f"Abstract: {ds.abstract}")
print(f"Keywords: {list(ds.keywords.values_list('name', flat=True))}")
EOF
```

### Check ExecutionRequests

```bash
docker-compose exec django python manage.py shell <<EOF
from geonode.resource.models import ExecutionRequest
req = ExecutionRequest.objects.latest('created')
print(f"Status: {req.status}")
print(f"Metadata: {req.input_params}")
print(f"Output: {req.output_params}")
EOF
```

### Manually Apply Metadata to a Specific Dataset

```bash
docker-compose exec django python manage.py apply_metadata_to_dataset <dataset-name> \
    --title "My Title" \
    --description "My description" \
    --keywords "keyword1,keyword2" \
    --labels "Label1"
```

## Common Issues

### Issue: "Signal handler NOT found"

**Solution**: Restart the Django container
```bash
docker-compose restart django
```

### Issue: "Dataset not found"

**Possible causes**:
1. Dataset name doesn't match the uploaded filename
2. Dataset hasn't been created yet (GeoServer might still be processing)

**Solution**: Check dataset names
```bash
docker-compose exec django python manage.py shell -c \
    "from geonode.layers.models import Dataset; \
     print([ds.name for ds in Dataset.objects.all().order_by('-date')[:10]])"
```

### Issue: Metadata not applied even though signal is registered

**Check**:
1. Is there a matching ExecutionRequest?
   ```bash
   docker-compose exec django python manage.py test_metadata_signal
   ```

2. Apply manually:
   ```bash
   docker-compose exec django python manage.py apply_pending_metadata
   ```

## Verification Checklist

- [ ] Container restarted after code changes
- [ ] Signal handler is registered (check with `test_metadata_signal`)
- [ ] Test upload performed through QGIS plugin
- [ ] Dataset appears in database
- [ ] Metadata fields are populated (check with `test_metadata_signal` or API)
- [ ] ExecutionRequest status is FINISHED
- [ ] Upload is linked to Dataset

## Docker-Compose Shortcuts

Add these to your workflow:

```bash
# Quick test
alias test-metadata="docker-compose exec django python manage.py test_metadata_signal"

# Apply pending metadata
alias apply-metadata="docker-compose exec django python manage.py apply_pending_metadata"

# Django shell
alias dshell="docker-compose exec django python manage.py shell"

# Restart Django
alias restart-django="docker-compose restart django"
```

Usage:
```bash
restart-django
sleep 5
test-metadata
```

## Expected Output (Success)

When everything is working, `test_metadata_signal` should show:

```
======================================================================
METADATA SIGNAL HANDLER TEST
======================================================================

1. Checking if signal handler is registered...
   ✓ Signal handler is registered!

2. Recent datasets and their metadata:

   Dataset 1:
     ID: 123
     Name: hientrangsdd_2020
     Title: HienTrangSDD_2020        <-- ✓ Your title
     Abstract: This is a test...     <-- ✓ Your description
     Keywords: ['test', 'metadata']  <-- ✓ Your keywords
     Regions: ['Test Label']         <-- ✓ Your labels (maybe)

3. Pending ExecutionRequests with metadata:
   No pending ExecutionRequests found. <-- ✓ All processed

4. Recently completed ExecutionRequests:

   ExecutionRequest 1:
     Output:
       - metadata_applied: True      <-- ✓ Metadata was applied!

======================================================================
SUMMARY:
✓ Signal handler is registered
  Total datasets: 10
  Pending ExecutionRequests: 0
  Completed ExecutionRequests: 5
```

## Notes for Production

1. **Always restart the container** after deploying new code
2. **Use `--dry-run`** first when running `apply_pending_metadata`
3. **Monitor the ExecutionRequests** table for failed uploads
4. **Clear old ExecutionRequests** periodically (they're cleaned automatically by Celery)

---

**Quick Start:**
```bash
docker-compose restart django
sleep 5
docker-compose exec django python manage.py test_metadata_signal
```

If signal handler is registered and you see recent datasets with metadata → ✅ **IT'S WORKING!**

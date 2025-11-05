# Middleware Setup Instructions

## Add Upload Metadata Middleware to Django Settings

To enable metadata capture from QGIS plugin uploads, add the middleware to your Django settings.

### Step 1: Edit settings.py

Find the `MIDDLEWARE` list in `geonode/settings.py` and add this line:

```python
MIDDLEWARE = [
    ...other middleware...
    'geonode.upload.middleware.UploadMetadataMiddleware',  # ADD THIS LINE
]
```

**Important**: Add it near the END of the MIDDLEWARE list, after authentication middleware.

### Step 2: Restart Django

```bash
docker-compose restart django
```

### Step 3: Test

Upload a dataset through QGIS plugin with metadata, then run:

```bash
docker-compose exec django python manage.py test_metadata_signal
```

You should see metadata applied!

## Alternative: Add to settings programmatically

If you can't edit `settings.py` directly, add this to your `local_settings.py`:

```python
# Enable upload metadata capture
MIDDLEWARE = MIDDLEWARE + ['geonode.upload.middleware.UploadMetadataMiddleware']
```

## Verification

After adding the middleware and restarting:

1. The middleware will log: `[UPLOAD-MIDDLEWARE] Captured metadata for upload: <filename>`
2. The signal handler will log: `[UPLOAD-SIGNAL] Found metadata in cache`
3. Metadata will be applied to the dataset

## Without Middleware

If you can't add middleware, you can still apply metadata manually after upload:

```bash
docker-compose exec django python manage.py apply_metadata_to_dataset <dataset_name> \
    --title "Title" \
    --description "Description" \
    --keywords "keyword1,keyword2"
```

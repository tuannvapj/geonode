# OBSOLETE: Upload-time Metadata Persistence Approach

**Status**: ARCHIVED - This approach has been replaced

## Why This Was Archived

This directory contains code and documentation from our previous attempt to automatically persist metadata during the upload process. This approach proved unreliable due to:

1. **Cache Backend Issues**: The server used DummyCache which doesn't persist data
2. **Timing Issues**: Signal handlers had difficulty matching uploaded files to created datasets
3. **Complexity**: Required middleware, signals, cache management, and complex filename normalization
4. **Docker Constraints**: Difficult to debug in containerized uWSGI environment without log access

## New Approach

We've replaced this with a **simpler, more reliable approach**:

- **After-upload metadata editing** via dedicated API endpoints
- `PATCH /api/v2/datasets/{id}/metadata/` - Update metadata for existing dataset
- `GET /api/v2/datasets/{id}/metadata/` - Get metadata for pre-filling edit dialog
- Plugin shows "Edit Metadata" button after successful upload
- Direct database writes using resource_manager.update() - no caching involved

## Files Archived

### Code Files
- `middleware.py` - Intercepted upload requests to capture metadata
- `signals.py` - Django signal handler to apply metadata after dataset creation
- `metadata_cache.py` - Cache-based metadata storage utilities
- `models_metadata.py` - Database model for metadata storage (alternative to cache)
- `upload_helpers.py` - Helper functions for applying metadata

### Documentation
- `FINAL_METADATA_SOLUTION.md` - Complete guide to the old middleware/signal approach
- `METADATA_FIX_DOCKER_GUIDE.md` - Docker-specific troubleshooting
- `METADATA_FIX_SUMMARY.md` - Summary of the old approach
- `MIDDLEWARE_SETUP.md` - Setup instructions for middleware
- `METADATA_SIGNAL_HANDLER_FIX.md` - Signal handler documentation
- `UPLOAD_METADATA_IMPLEMENTATION.md` - Implementation details

### Management Commands (Removed)
- `test_metadata_signal.py` - Testing command for signal handler
- `apply_pending_metadata.py` - Manually apply pending metadata
- `apply_metadata_to_dataset.py` - Apply metadata to specific dataset

## Lessons Learned

1. **Simple is better**: Direct API calls are more reliable than automatic interception
2. **User control**: Let users explicitly edit metadata rather than automatic application
3. **Testability**: Direct API endpoints are easier to test than middleware + signals
4. **Debugging**: Avoid solutions that require complex log analysis in production

## Date Archived

November 4, 2025

## See Instead

- `/geonode/layers/api/views.py` - New DatasetMetadataView API
- `/METADATA_API_DOCUMENTATION.md` - New API documentation
- `/PLUGIN_METADATA_INTEGRATION.md` - Plugin integration guide

#########################################################################
#
# Copyright (C) 2024 OSGeo
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#########################################################################
"""
Temporary metadata cache for upload metadata.

This module provides a simple cache to store upload metadata temporarily
until the dataset is created and the signal handler can apply it.
"""
from django.core.cache import cache
from django.conf import settings
import hashlib
import logging

logger = logging.getLogger(__name__)

# Cache timeout in seconds (5 minutes)
METADATA_CACHE_TIMEOUT = getattr(settings, 'UPLOAD_METADATA_CACHE_TIMEOUT', 300)


def normalize_filename(filename):
    """Normalize a filename for cache key generation."""
    # Remove extension and normalize
    name = filename.rsplit('.', 1)[0] if '.' in filename else filename
    return name.lower().replace(' ', '_').replace('-', '_')


def get_cache_key(filename_or_datasetname):
    """Generate a cache key for metadata."""
    normalized = normalize_filename(filename_or_datasetname)
    # Use hash to keep key length reasonable
    key_hash = hashlib.md5(normalized.encode()).hexdigest()[:12]
    return f"upload_metadata_{key_hash}_{normalized[:30]}"


def store_metadata(filename, metadata):
    """
    Store metadata for an upload.

    Args:
        filename: The uploaded filename
        metadata: Dict with keys: dataset_title, description, keywords, labels
    """
    cache_key = get_cache_key(filename)
    cache.set(cache_key, metadata, METADATA_CACHE_TIMEOUT)
    logger.info(f"[METADATA-CACHE] Stored metadata for {filename} (key: {cache_key})")
    logger.info(f"[METADATA-CACHE] Metadata: {metadata}")
    return cache_key


def get_metadata(dataset_name):
    """
    Retrieve metadata for a dataset by name.

    Args:
        dataset_name: The dataset name (usually derived from filename)

    Returns:
        Dict with metadata or None
    """
    cache_key = get_cache_key(dataset_name)
    metadata = cache.get(cache_key)

    if metadata:
        logger.info(f"[METADATA-CACHE] Found metadata for {dataset_name} (key: {cache_key})")
        logger.info(f"[METADATA-CACHE] Metadata: {metadata}")
    else:
        logger.debug(f"[METADATA-CACHE] No metadata found for {dataset_name} (key: {cache_key})")

    return metadata


def clear_metadata(dataset_name):
    """Clear metadata from cache after it's been applied."""
    cache_key = get_cache_key(dataset_name)
    cache.delete(cache_key)
    logger.info(f"[METADATA-CACHE] Cleared metadata for {dataset_name}")


def list_cached_metadata():
    """
    List all cached metadata (for debugging).

    Note: This requires redis/memcached backend with key pattern support.
    """
    try:
        from django.core.cache import caches
        cache_backend = caches['default']

        # This works with Redis
        if hasattr(cache_backend.client, 'keys'):
            keys = cache_backend.client.keys('upload_metadata_*')
            result = {}
            for key in keys:
                if isinstance(key, bytes):
                    key = key.decode('utf-8')
                value = cache.get(key)
                if value:
                    result[key] = value
            return result
        else:
            return {"error": "Cache backend doesn't support key listing"}
    except Exception as e:
        logger.exception(f"Error listing cached metadata: {e}")
        return {"error": str(e)}

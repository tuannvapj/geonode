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
Middleware to intercept upload requests and store metadata.

This middleware captures upload metadata from QGIS plugin requests
and stores it in cache so the signal handler can apply it after
the dataset is created.
"""
import logging
import json

logger = logging.getLogger(__name__)


class UploadMetadataMiddleware:
    """
    Middleware that intercepts upload requests and stores metadata in cache.

    This works with GeoNode's importer API and any other upload mechanism.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Intercept upload requests BEFORE they're processed
        if request.method in ['POST', 'PUT'] and self.is_upload_request(request):
            self.capture_metadata(request)

        response = self.get_response(request)
        return response

    def is_upload_request(self, request):
        """Check if this is an upload request."""
        # Check for various upload endpoints
        upload_patterns = [
            '/api/v2/uploads',
            '/api/v2/resource-service/execution-request',
            '/importer/upload',
        ]

        return any(pattern in request.path for pattern in upload_patterns)

    def capture_metadata(self, request):
        """Capture and store upload metadata from the request."""
        try:
            # Get metadata from various possible sources
            metadata = {}

            # 1. Check POST data
            if hasattr(request, 'POST'):
                metadata['dataset_title'] = request.POST.get('dataset_title', '')
                metadata['description'] = request.POST.get('description', '')
                metadata['keywords'] = request.POST.get('keywords', '')
                metadata['labels'] = request.POST.get('labels', '')

            # 2. Check JSON body (for API requests)
            if request.content_type == 'application/json' and hasattr(request, 'body'):
                try:
                    body = json.loads(request.body)
                    if isinstance(body, dict):
                        metadata['dataset_title'] = body.get('dataset_title', metadata.get('dataset_title', ''))
                        metadata['description'] = body.get('description', metadata.get('description', ''))
                        metadata['keywords'] = body.get('keywords', metadata.get('keywords', ''))
                        metadata['labels'] = body.get('labels', metadata.get('labels', ''))
                except (json.JSONDecodeError, ValueError):
                    pass

            # 3. Check multipart form data
            if hasattr(request, 'FILES') and request.FILES:
                base_file = request.FILES.get('base_file') or request.FILES.get('file')
                if base_file:
                    filename = base_file.name

                    # Check if there's any metadata to store
                    has_metadata = any([
                        metadata.get('dataset_title'),
                        metadata.get('description'),
                        metadata.get('keywords'),
                        metadata.get('labels')
                    ])

                    if has_metadata:
                        logger.info(f"[UPLOAD-MIDDLEWARE] Captured metadata for upload: {filename}")
                        logger.info(f"[UPLOAD-MIDDLEWARE]   - dataset_title: {metadata.get('dataset_title')}")
                        logger.info(f"[UPLOAD-MIDDLEWARE]   - description: {metadata.get('description')}")
                        logger.info(f"[UPLOAD-MIDDLEWARE]   - keywords: {metadata.get('keywords')}")
                        logger.info(f"[UPLOAD-MIDDLEWARE]   - labels: {metadata.get('labels')}")

                        # Store in database
                        from geonode.upload.models import UploadMetadata
                        UploadMetadata.store(filename, metadata)
                    else:
                        logger.debug(f"[UPLOAD-MIDDLEWARE] No metadata found in request for {filename}")

        except Exception as e:
            logger.exception(f"[UPLOAD-MIDDLEWARE] Error capturing metadata: {e}")

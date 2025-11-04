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
Signal handlers for upload-related events.

This module contains signal handlers that automatically apply metadata
to datasets after they are created via upload.
"""
import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from geonode.layers.models import Dataset
from geonode.resource.models import ExecutionRequest
from geonode.resource.manager import resource_manager
from geonode.upload.models import UploadMetadata

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Dataset)
def apply_metadata_from_execution_request(sender, instance, created, **kwargs):
    """
    Automatically apply metadata to newly created datasets.

    This signal handler checks if there's a pending ExecutionRequest with metadata
    for this dataset and applies it using resource_manager.update().

    The handler matches ExecutionRequests by:
    1. Looking for READY or RUNNING status
    2. Matching the dataset name to the file_name in input_params
    3. Checking if metadata fields (dataset_title, description, keywords, labels) are present
    """
    if not created:
        # Only process newly created datasets
        return

    try:
        # Look for metadata in TWO places:
        # 1. Database (UploadMetadata model - for direct uploads from QGIS plugin)
        # 2. ExecutionRequest (for API uploads)

        dataset_name = instance.name.lower()
        logger.info(f"[UPLOAD-SIGNAL] Dataset created: {instance.id} - {instance.name}")

        # FIRST: Check UploadMetadata database table
        pending_metadata = UploadMetadata.get_pending(instance.name)

        if pending_metadata:
            logger.info(f"[UPLOAD-SIGNAL] Found metadata in database for {instance.name}")

            # Extract metadata
            metadata_dict = pending_metadata.get_metadata_dict()
            dataset_title = metadata_dict.get('dataset_title', '')
            description = metadata_dict.get('description', '')
            keywords_list = metadata_dict.get('keywords', [])
            labels_list = metadata_dict.get('labels', [])

            # Ensure keywords and labels are lists
            if isinstance(keywords_list, str):
                keywords_list = [k.strip() for k in keywords_list.split(',') if k.strip()]
            if isinstance(labels_list, str):
                labels_list = [l.strip() for l in labels_list.split(',') if l.strip()]

            # Check if there's actually metadata to apply
            has_metadata = any([dataset_title, description, keywords_list, labels_list])

            if has_metadata:
                logger.info(f"[UPLOAD-SIGNAL] Applying metadata from database:")
                logger.info(f"[UPLOAD-SIGNAL]   - Title: {dataset_title}")
                logger.info(f"[UPLOAD-SIGNAL]   - Description: {description}")
                logger.info(f"[UPLOAD-SIGNAL]   - Keywords: {keywords_list}")
                logger.info(f"[UPLOAD-SIGNAL]   - Labels: {labels_list}")

                # Prepare metadata for resource_manager.update()
                vals = {}
                if dataset_title:
                    vals['title'] = dataset_title
                if description:
                    vals['abstract'] = description

                # Use resource_manager.update() to apply metadata
                resource_manager.update(
                    uuid=str(instance.uuid),
                    instance=instance.get_real_instance(),
                    vals=vals,
                    keywords=keywords_list,
                    regions=[],
                    notify=False
                )

                logger.info(f"[UPLOAD-SIGNAL] Successfully applied metadata from database to dataset {instance.id}")

                # Mark as applied
                pending_metadata.mark_applied(instance.id)

                # Done - metadata applied
                return

        # SECOND: Check ExecutionRequests (fallback for API uploads)
        logger.info(f"[UPLOAD-SIGNAL] No database metadata, checking ExecutionRequests...")

        pending_requests = ExecutionRequest.objects.filter(
            status__in=[ExecutionRequest.STATUS_READY, ExecutionRequest.STATUS_RUNNING, ExecutionRequest.STATUS_FINISHED]
        ).order_by('-created')

        for exec_request in pending_requests[:10]:  # Check the 10 most recent
            input_params = exec_request.input_params or {}
            file_name = input_params.get('file_name', '')

            if not file_name:
                continue

            # Normalize file name for comparison
            file_basename = file_name.rsplit('.', 1)[0].lower().replace(' ', '_')

            # Check if this ExecutionRequest is for this dataset
            if file_basename in dataset_name or dataset_name in file_basename:
                logger.info(f"[UPLOAD-SIGNAL] Found matching ExecutionRequest: {exec_request.exec_id}")

                # Extract metadata
                dataset_title = input_params.get('dataset_title', '')
                description = input_params.get('description', '')
                keywords_list = input_params.get('keywords', [])
                labels_list = input_params.get('labels', [])

                # Ensure keywords and labels are lists
                if isinstance(keywords_list, str):
                    keywords_list = [k.strip() for k in keywords_list.split(',') if k.strip()]
                if isinstance(labels_list, str):
                    labels_list = [l.strip() for l in labels_list.split(',') if l.strip()]

                # Check if there's actually metadata to apply
                has_metadata = any([dataset_title, description, keywords_list, labels_list])

                if has_metadata:
                    logger.info(f"[UPLOAD-SIGNAL] Applying metadata:")
                    logger.info(f"[UPLOAD-SIGNAL]   - Title: {dataset_title}")
                    logger.info(f"[UPLOAD-SIGNAL]   - Description: {description}")
                    logger.info(f"[UPLOAD-SIGNAL]   - Keywords: {keywords_list}")
                    logger.info(f"[UPLOAD-SIGNAL]   - Labels: {labels_list}")

                    # Prepare metadata for resource_manager.update()
                    vals = {}
                    if dataset_title:
                        vals['title'] = dataset_title
                    if description:
                        vals['abstract'] = description  # GeoNode uses 'abstract' field

                    try:
                        # Use resource_manager.update() to apply metadata
                        resource_manager.update(
                            uuid=str(instance.uuid),
                            instance=instance.get_real_instance(),
                            vals=vals,
                            keywords=keywords_list,
                            regions=[],  # labels_list might not work directly as regions
                            notify=False
                        )

                        logger.info(f"[UPLOAD-SIGNAL] Successfully applied metadata to dataset {instance.id}")

                        # Update ExecutionRequest status
                        exec_request.status = ExecutionRequest.STATUS_FINISHED
                        exec_request.output_params = {
                            'dataset_id': instance.id,
                            'dataset_uuid': str(instance.uuid),
                            'dataset_name': instance.name,
                            'metadata_applied': True
                        }
                        exec_request.save()

                        # Link Upload to Dataset if it exists
                        from geonode.upload.models import Upload
                        upload = Upload.objects.filter(import_id=str(exec_request.exec_id)).first()
                        if upload and not upload.resource:
                            upload.resource = instance.get_real_instance()
                            upload.state = Upload.STATE_PROCESSED
                            upload.save()
                            logger.info(f"[UPLOAD-SIGNAL] Linked Upload {upload.id} to Dataset {instance.id}")

                        # Stop after finding and applying metadata
                        break

                    except Exception as e:
                        logger.exception(f"[UPLOAD-SIGNAL] Error applying metadata: {e}")
                        exec_request.status = ExecutionRequest.STATUS_FAILED
                        exec_request.log = f"Signal handler error: {str(e)}"
                        exec_request.save()
                else:
                    logger.debug(f"[UPLOAD-SIGNAL] ExecutionRequest {exec_request.exec_id} has no metadata to apply")

    except Exception as e:
        logger.exception(f"[UPLOAD-SIGNAL] Error in signal handler: {e}")

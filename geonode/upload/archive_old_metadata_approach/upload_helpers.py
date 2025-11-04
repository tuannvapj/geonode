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
Helper functions for processing dataset uploads with metadata.
"""
import os
import logging
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)


def apply_metadata_to_dataset(dataset, keywords: List[str], labels: List[str], description: str = ''):
    """
    Apply metadata (keywords, labels, description) to a dataset.

    Args:
        dataset: The Dataset instance
        keywords: List of keyword strings
        labels: List of label/category strings
        description: Description/abstract text
    """
    from geonode.base.models import HierarchicalKeyword, TopicCategory

    try:
        # Set description/abstract if provided
        if description:
            dataset.abstract = description

        # Add keywords
        if keywords:
            # Keywords are managed by django-taggit TaggableManager
            # We can add them directly
            dataset.keywords.add(*keywords)
            logger.info(f"Added {len(keywords)} keywords to dataset {dataset.id}")

        # Add labels as additional keywords or categories
        # Labels can be treated as hierarchical keywords or topic categories
        if labels:
            for label in labels:
                # Try to create or get hierarchical keyword
                try:
                    keyword, created = HierarchicalKeyword.objects.get_or_create(
                        name=label,
                        defaults={'slug': label.lower().replace(' ', '-')}
                    )
                    # Add to keywords as well
                    dataset.keywords.add(label)
                    logger.info(f"Added label '{label}' to dataset {dataset.id}")
                except Exception as e:
                    logger.warning(f"Could not add label '{label}': {e}")

        # Save the dataset
        dataset.save()
        logger.info(f"Successfully applied metadata to dataset {dataset.id}")
        return True

    except Exception as e:
        logger.exception(f"Error applying metadata to dataset: {e}")
        return False


def validate_upload_files(base_file_path: str) -> Dict[str, any]:
    """
    Validate uploaded geospatial files.

    Args:
        base_file_path: Path to the main uploaded file

    Returns:
        Dict with 'valid' (bool) and 'errors' (list) keys
    """
    result = {'valid': True, 'errors': []}

    if not os.path.exists(base_file_path):
        result['valid'] = False
        result['errors'].append(f"File not found: {base_file_path}")
        return result

    file_ext = os.path.splitext(base_file_path)[1].lower()

    # For shapefiles, check for required components
    if file_ext == '.shp':
        base_name = os.path.splitext(base_file_path)[0]
        required_files = ['.shp', '.dbf', '.shx']
        missing_files = []

        for ext in required_files:
            if not os.path.exists(base_name + ext):
                missing_files.append(ext)

        if missing_files:
            result['valid'] = False
            result['errors'].append(f"Missing required shapefile components: {', '.join(missing_files)}")

    # Check file size (max 500MB)
    file_size = os.path.getsize(base_file_path)
    max_size = 500 * 1024 * 1024  # 500MB

    if file_size > max_size:
        result['valid'] = False
        result['errors'].append(f"File too large: {file_size / (1024*1024):.2f}MB (max: 500MB)")

    return result


def get_dataset_from_upload(upload_id: int):
    """
    Get the Dataset instance associated with an Upload.

    Args:
        upload_id: Upload instance ID

    Returns:
        Dataset instance or None
    """
    from geonode.upload.models import Upload
    from geonode.layers.models import Dataset

    try:
        upload = Upload.objects.get(id=upload_id)
        if upload.resource:
            # The resource field links to ResourceBase
            # We need to get the actual Dataset instance
            dataset = Dataset.objects.filter(resourcebase_ptr_id=upload.resource.id).first()
            return dataset
    except Upload.DoesNotExist:
        logger.error(f"Upload {upload_id} not found")
    except Exception as e:
        logger.exception(f"Error getting dataset from upload: {e}")

    return None
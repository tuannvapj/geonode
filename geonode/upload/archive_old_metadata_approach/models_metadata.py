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
Database model for temporary upload metadata storage.

This replaces the cache-based approach to avoid cache backend issues.
"""
from django.db import models
from django.utils import timezone
from datetime import timedelta


class UploadMetadata(models.Model):
    """
    Temporary storage for upload metadata.

    This model stores metadata sent with file uploads until the dataset
    is created and the signal handler can apply it.

    Records are automatically cleaned up after 1 hour.
    """

    # Normalized filename (used for matching with datasets)
    filename_normalized = models.CharField(max_length=255, db_index=True)

    # Original filename
    filename_original = models.CharField(max_length=255)

    # Metadata fields
    dataset_title = models.CharField(max_length=500, blank=True, default='')
    description = models.TextField(blank=True, default='')
    keywords = models.TextField(blank=True, default='', help_text='Comma-separated keywords')
    labels = models.TextField(blank=True, default='', help_text='Comma-separated labels')

    # Status tracking
    applied = models.BooleanField(default=False, help_text='Whether metadata has been applied')
    applied_to_dataset_id = models.IntegerField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'upload'
        verbose_name = 'Upload Metadata'
        verbose_name_plural = 'Upload Metadata'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['filename_normalized', 'applied']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        status = "✓ Applied" if self.applied else "⏳ Pending"
        return f"{self.filename_original} - {status}"

    @classmethod
    def store(cls, filename, metadata):
        """
        Store metadata for a file upload.

        Args:
            filename: Original filename
            metadata: Dict with dataset_title, description, keywords, labels

        Returns:
            UploadMetadata instance
        """
        normalized = cls.normalize_filename(filename)

        # Delete any existing pending metadata for this file
        cls.objects.filter(filename_normalized=normalized, applied=False).delete()

        # Create new record
        return cls.objects.create(
            filename_normalized=normalized,
            filename_original=filename,
            dataset_title=metadata.get('dataset_title', ''),
            description=metadata.get('description', ''),
            keywords=metadata.get('keywords', ''),
            labels=metadata.get('labels', ''),
        )

    @classmethod
    def get_pending(cls, dataset_name):
        """
        Get pending metadata for a dataset name.

        Args:
            dataset_name: Dataset name to match

        Returns:
            UploadMetadata instance or None
        """
        normalized = cls.normalize_filename(dataset_name)

        # Try exact match first
        metadata = cls.objects.filter(
            filename_normalized=normalized,
            applied=False
        ).first()

        if metadata:
            return metadata

        # Try fuzzy match
        metadata = cls.objects.filter(
            filename_normalized__contains=normalized[:20],  # Match first 20 chars
            applied=False
        ).first()

        return metadata

    @classmethod
    def normalize_filename(cls, filename):
        """Normalize filename for consistent matching."""
        # Remove extension
        name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        # Lowercase and replace special chars
        return name.lower().replace(' ', '_').replace('-', '_')

    def mark_applied(self, dataset_id):
        """Mark this metadata as applied to a dataset."""
        self.applied = True
        self.applied_to_dataset_id = dataset_id
        self.applied_at = timezone.now()
        self.save()

    def get_metadata_dict(self):
        """Get metadata as a dictionary."""
        return {
            'dataset_title': self.dataset_title,
            'description': self.description,
            'keywords': self.keywords,
            'labels': self.labels,
        }

    @classmethod
    def cleanup_old(cls, hours=1):
        """Delete metadata older than specified hours."""
        cutoff = timezone.now() - timedelta(hours=hours)
        deleted = cls.objects.filter(created_at__lt=cutoff).delete()
        return deleted[0] if deleted else 0

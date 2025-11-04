#!/usr/bin/env python3
"""
Test script for metadata application to datasets.

This script tests the apply_metadata_to_dataset() function.

Usage:
    python scripts/test_metadata_application.py
"""
import os
import sys
import django

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geonode.settings')
django.setup()

from geonode.layers.models import Dataset
from geonode.upload.upload_helpers import apply_metadata_to_dataset


def test_metadata_application():
    """Test applying metadata to a dataset."""
    print("=" * 70)
    print("Testing Metadata Application")
    print("=" * 70)
    print()

    # Get the most recent dataset
    dataset = Dataset.objects.all().order_by('-date').first()

    if not dataset:
        print("❌ No datasets found in the database.")
        print("   Please create a dataset first or import one.")
        return False

    print(f"✓ Found dataset: {dataset.id} - {dataset.name}")
    print()

    # Store original values
    original_title = dataset.title
    original_abstract = dataset.abstract
    original_keywords = list(dataset.keywords.values_list('name', flat=True))

    print("Original values:")
    print(f"  Title: {original_title}")
    print(f"  Abstract: {original_abstract}")
    print(f"  Keywords: {original_keywords}")
    print()

    # Test metadata
    test_title = "Test Title - " + dataset.name
    test_keywords = ['test', 'metadata', 'application']
    test_labels = ['Test Label']
    test_description = 'This is a test description for metadata application.'

    print("Applying test metadata:")
    print(f"  Title: {test_title}")
    print(f"  Keywords: {test_keywords}")
    print(f"  Labels: {test_labels}")
    print(f"  Description: {test_description}")
    print()

    # Apply metadata
    dataset.title = test_title
    success = apply_metadata_to_dataset(dataset, test_keywords, test_labels, test_description)

    if not success:
        print("❌ Failed to apply metadata")
        return False

    # Refresh and verify
    dataset.refresh_from_db()

    print("✓ Metadata applied successfully!")
    print()
    print("New values:")
    print(f"  Title: {dataset.title}")
    print(f"  Abstract: {dataset.abstract}")
    print(f"  Keywords: {list(dataset.keywords.values_list('name', flat=True))}")
    print()

    # Verify
    if dataset.title != test_title:
        print(f"❌ Title not updated. Expected '{test_title}', got '{dataset.title}'")
        return False

    if dataset.abstract != test_description:
        print(f"❌ Abstract not updated. Expected '{test_description}', got '{dataset.abstract}'")
        return False

    current_keywords = list(dataset.keywords.values_list('name', flat=True))
    for keyword in test_keywords:
        if keyword not in current_keywords:
            print(f"❌ Keyword '{keyword}' not found in dataset keywords: {current_keywords}")
            return False

    print("=" * 70)
    print("✅ ALL TESTS PASSED")
    print("=" * 70)
    print()
    print("Summary:")
    print(f"  Dataset ID: {dataset.id}")
    print(f"  Dataset Name: {dataset.name}")
    print(f"  Title: {dataset.title}")
    print(f"  Abstract: {dataset.abstract}")
    print(f"  Keywords: {list(dataset.keywords.values_list('name', flat=True))}")
    print()

    return True


if __name__ == '__main__':
    try:
        result = test_metadata_application()
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

#!/usr/bin/env python
"""
Test script for category field in metadata_fields API
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, '/usr/src/geonode')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geonode.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from geonode.layers.models import Dataset
import json

User = get_user_model()

def test_metadata_api():
    """Test GET and PATCH metadata_fields endpoints"""

    # Get admin user and first dataset
    user = User.objects.get(username='admin')
    dataset = Dataset.objects.first()

    if not dataset:
        print("❌ No datasets found")
        return

    print(f"Testing with dataset ID: {dataset.id}")
    print(f"Title: {dataset.title}")
    print(f"Current category_custom: {dataset.category_custom}")
    print()

    # Create authenticated client
    client = Client()
    client.force_login(user)

    # Test 1: GET metadata_fields
    print("=" * 60)
    print("TEST 1: GET /api/v2/datasets/{}/metadata_fields/".format(dataset.id))
    print("=" * 60)

    get_url = f'/api/v2/datasets/{dataset.id}/metadata_fields/'
    response = client.get(get_url)

    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("Response Data:")
        print(json.dumps(data, indent=2, ensure_ascii=False))

        # Check if category field exists
        if 'category' in data:
            print(f"\n✅ 'category' field present: '{data['category']}'")
        else:
            print("\n❌ 'category' field missing")

        # Check if labels field exists (should NOT exist)
        if 'labels' in data:
            print(f"❌ 'labels' field still present (should be removed): {data['labels']}")
        else:
            print("✅ 'labels' field correctly removed")
    else:
        print(f"❌ GET request failed: {response.content}")

    print()

    # Test 2: PATCH metadata_fields with category
    print("=" * 60)
    print("TEST 2: PATCH /api/v2/datasets/{}/metadata_fields/".format(dataset.id))
    print("=" * 60)

    patch_data = {
        "title": "Test Category Update",
        "description": "Testing category field",
        "keywords": ["test", "category"],
        "category": "Sử dụng đất",
        "regions": []
    }

    print("PATCH Payload:")
    print(json.dumps(patch_data, indent=2, ensure_ascii=False))
    print()

    patch_url = f'/api/v2/datasets/{dataset.id}/metadata_fields/'
    response = client.patch(
        patch_url,
        data=json.dumps(patch_data),
        content_type='application/json'
    )

    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("Response Data:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print("\n✅ PATCH request successful")

        # Verify in database
        dataset.refresh_from_db()
        print(f"\nDatabase verification:")
        print(f"  - category_custom: '{dataset.category_custom}'")

        if dataset.category_custom == "Sử dụng đất":
            print("✅ Category successfully saved to database")
        else:
            print(f"❌ Category not saved correctly. Expected 'Sử dụng đất', got '{dataset.category_custom}'")
    else:
        print(f"❌ PATCH request failed")
        try:
            error_data = response.json()
            print(json.dumps(error_data, indent=2, ensure_ascii=False))
        except:
            print(response.content)

    print()

    # Test 3: GET again to verify category is returned
    print("=" * 60)
    print("TEST 3: GET again to verify category persisted")
    print("=" * 60)

    response = client.get(get_url)

    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"category: '{data.get('category', 'NOT FOUND')}'")

        if data.get('category') == "Sử dụng đất":
            print("✅ Category correctly returned from API")
        else:
            print(f"❌ Category mismatch. Expected 'Sử dụng đất', got '{data.get('category')}'")

    print()
    print("=" * 60)
    print("TESTS COMPLETE")
    print("=" * 60)

if __name__ == '__main__':
    test_metadata_api()

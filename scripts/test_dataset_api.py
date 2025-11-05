#!/usr/bin/env python3
"""
Test script to verify Dataset API new fields.

Usage:
    python scripts/test_dataset_api.py
"""

import requests
import json
import sys

# Configuration
BASE_URL = "http://localhost"
TOKEN = "M5C0X0zpjc4ZOv3gr8qMmWVVVQZzle"

def test_api():
    """Test the datasets API endpoint."""

    url = f"{BASE_URL}/api/v2/datasets/"
    headers = {"Authorization": f"Bearer {TOKEN}"}

    print("=" * 70)
    print("Testing Dataset API - New Fields")
    print("=" * 70)
    print(f"URL: {url}")
    print(f"Token: {TOKEN[:20]}...")
    print()

    try:
        response = requests.get(url, headers=headers, timeout=10)

        print(f"Status Code: {response.status_code}")

        if response.status_code != 200:
            print(f"Error Response: {response.text[:500]}")
            return False

        data = response.json()
        datasets = data.get('datasets', [])

        print(f"Total Datasets: {len(datasets)}")
        print()

        if not datasets:
            print("⚠ No datasets found. Please create some test data first.")
            return False

        # Check first dataset
        dataset = datasets[0]

        print("=" * 70)
        print("First Dataset Analysis")
        print("=" * 70)

        # Basic info
        print(f"ID: {dataset.get('pk')}")
        print(f"Title: {dataset.get('title', 'N/A')}")
        print()

        # Check for new fields
        has_description = 'description' in dataset
        has_keyword_list = 'keyword_list' in dataset
        has_labels = 'labels' in dataset

        print("Field Availability Check:")
        print(f"  {'✓' if has_description else '✗'} description: {has_description}")
        print(f"  {'✓' if has_keyword_list else '✗'} keyword_list: {has_keyword_list}")
        print(f"  {'✓' if has_labels else '✗'} labels: {has_labels}")
        print()

        if not (has_description and has_keyword_list and has_labels):
            print("❌ ISSUE: Some required fields are missing!")
            print("\nAvailable fields:")
            print(json.dumps(list(dataset.keys()), indent=2))
            print("\n⚠ Please restart the Django server and try again.")
            return False

        # Show field values
        print("Field Values:")
        print(f"  abstract: {dataset.get('abstract', 'N/A')[:80]}...")
        print(f"  description: {dataset.get('description', 'N/A')[:80]}...")
        print(f"  keyword_list: {dataset.get('keyword_list', [])}")
        print(f"  labels: {dataset.get('labels', [])}")
        print()

        # Show original keywords field for comparison
        keywords_full = dataset.get('keywords', [])
        print(f"  keywords (full): {[k.get('name') for k in keywords_full]}")
        print()

        # Verify description matches abstract
        abstract = dataset.get('abstract', '')
        description = dataset.get('description', '')

        if abstract == description:
            print("✓ description field correctly mirrors abstract")
        else:
            print("⚠ description and abstract don't match")
            print(f"  abstract: {abstract[:50]}...")
            print(f"  description: {description[:50]}...")
        print()

        # Check multiple datasets
        if len(datasets) > 1:
            print("=" * 70)
            print(f"Checking all {len(datasets)} datasets...")
            print("=" * 70)

            all_good = True
            for idx, ds in enumerate(datasets):
                has_all = all([
                    'description' in ds,
                    'keyword_list' in ds,
                    'labels' in ds
                ])

                status = "✓" if has_all else "✗"
                print(f"{status} Dataset {idx+1} ({ds.get('pk')}): {ds.get('title', 'N/A')[:40]}")

                if not has_all:
                    all_good = False
                    print(f"    Missing: {[f for f in ['description', 'keyword_list', 'labels'] if f not in ds]}")

            print()
            if all_good:
                print("✓ All datasets have the new fields!")
            else:
                print("❌ Some datasets are missing fields. Server restart may be needed.")

        print()
        print("=" * 70)
        print("Summary")
        print("=" * 70)

        if has_description and has_keyword_list and has_labels:
            print("✓ SUCCESS: All new fields are present and working!")
            print()
            print("Next steps:")
            print("1. Use these fields in your QGIS plugin")
            print("2. description = dataset['description']")
            print("3. keywords = dataset['keyword_list']")
            print("4. labels = dataset['labels']")
            return True
        else:
            print("❌ FAILED: Fields are missing")
            print()
            print("Troubleshooting steps:")
            print("1. Restart Django server: docker-compose restart django")
            print("2. Clear Python cache: find . -name '*.pyc' -delete")
            print("3. Check server logs: docker-compose logs django")
            print("4. Run: python manage.py check")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Request Error: {e}")
        print()
        print("Please check:")
        print("1. Is the server running? (docker-compose ps)")
        print("2. Is the URL correct? (http://localhost)")
        print("3. Is the token valid?")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_single_dataset(dataset_id):
    """Test a single dataset by ID."""

    url = f"{BASE_URL}/api/v2/datasets/{dataset_id}/"
    headers = {"Authorization": f"Bearer {TOKEN}"}

    print(f"\nTesting single dataset: {dataset_id}")
    print(f"URL: {url}")

    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            dataset = response.json().get('dataset', response.json())
            print(f"\nDataset: {dataset.get('id')}")
            print(f"\nDataset: {dataset.get('title')}")
            print(f"Description: {dataset.get('description', 'N/A')[:100]}")
            print(f"Keywords: {dataset.get('keyword_list', [])}")
            print(f"Labels: {dataset.get('labels', [])}")
        else:
            print(f"Error: {response.status_code}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    # Test list endpoint
    success = test_api()

    # If specific dataset ID provided, test that too
    if len(sys.argv) > 1:
        dataset_id = sys.argv[1]
        test_single_dataset(dataset_id)

    sys.exit(0 if success else 1)
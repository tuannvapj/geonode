#!/usr/bin/env python3
"""
Django management script to check if serializer fields are properly configured.

Run inside Django environment:
    python manage.py shell < scripts/check_serializer.py

Or:
    docker-compose exec django python manage.py shell < scripts/check_serializer.py
"""

print("=" * 70)
print("Checking Dataset Serializers")
print("=" * 70)
print()

# Import serializers
try:
    from geonode.layers.api.serializers import DatasetSerializer, DatasetListSerializer
    print("✓ Successfully imported serializers")
except Exception as e:
    print(f"✗ Failed to import serializers: {e}")
    exit(1)

print()

# Check DatasetSerializer
print("DatasetSerializer Fields:")
print("-" * 70)
serializer = DatasetSerializer()
fields = serializer.get_fields()

# Check for our new fields
new_fields = ['description', 'keyword_list', 'labels']
for field_name in new_fields:
    if field_name in fields:
        print(f"  ✓ {field_name}: {type(fields[field_name]).__name__}")
    else:
        print(f"  ✗ {field_name}: MISSING")

print()

# Check DatasetListSerializer
print("DatasetListSerializer Fields:")
print("-" * 70)
list_serializer = DatasetListSerializer()
list_fields = list_serializer.get_fields()

for field_name in new_fields:
    if field_name in list_fields:
        print(f"  ✓ {field_name}: {type(list_fields[field_name]).__name__}")
    else:
        print(f"  ✗ {field_name}: MISSING")

print()

# Test with actual data if available
try:
    from geonode.layers.models import Dataset

    dataset_count = Dataset.objects.count()
    print(f"Found {dataset_count} datasets in database")

    if dataset_count > 0:
        print()
        print("Testing serialization with real data:")
        print("-" * 70)

        dataset = Dataset.objects.first()
        print(f"Using dataset: {dataset.title} (ID: {dataset.pk})")

        # Serialize with DatasetListSerializer
        serialized = DatasetListSerializer(dataset)
        data = serialized.data

        print()
        print("Serialized fields check:")
        for field_name in new_fields:
            if field_name in data:
                value = data[field_name]
                if isinstance(value, list):
                    print(f"  ✓ {field_name}: {value} (length: {len(value)})")
                else:
                    print(f"  ✓ {field_name}: {str(value)[:50]}...")
            else:
                print(f"  ✗ {field_name}: NOT IN OUTPUT")

        print()
        print("Sample keywords:")
        print(f"  keywords (full): {[k.name for k in dataset.keywords.all()]}")
        print(f"  keyword_list: {data.get('keyword_list', 'N/A')}")

        print()
        print("Sample category:")
        if dataset.category:
            print(f"  category: {dataset.category.identifier}")
        else:
            print(f"  category: None")
        print(f"  labels: {data.get('labels', 'N/A')}")

        print()
        print("Sample description:")
        print(f"  abstract: {dataset.abstract[:50] if dataset.abstract else 'N/A'}...")
        print(f"  description: {data.get('description', 'N/A')[:50]}...")

except Exception as e:
    print(f"Error testing with data: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 70)
print("Check Complete")
print("=" * 70)
print()
print("If all fields show '✓', the serializer is configured correctly.")
print("If API still doesn't return fields, restart Django server:")
print("  docker-compose restart django")
print()
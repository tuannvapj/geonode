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
Tests for Dataset Metadata Edit API endpoints.

Tests the GET and PATCH /api/v2/datasets/{id}/metadata_fields/ endpoints
for retrieving and updating dataset metadata.
"""

from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from geonode.layers.models import Dataset
from geonode.base.populate_test_data import create_single_dataset
from geonode.tests.base import GeoNodeBaseTestSupport


class MetadataFieldsAPITestCase(GeoNodeBaseTestSupport, APITestCase):
    """Tests for metadata_fields API endpoint"""

    fixtures = ["initial_data.json", "group_test_data.json", "default_oauth_apps.json"]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        # Create test users
        self.admin_user = get_user_model().objects.get(username="admin")
        self.normal_user = get_user_model().objects.get(username="bobby")

        # Create test dataset
        self.dataset = create_single_dataset("test_metadata_api_dataset", owner=self.admin_user)

        # API URL
        self.url = reverse(
            "datasets-metadata-fields",
            kwargs={"pk": self.dataset.id}
        )

    def tearDown(self):
        # Clean up
        if self.dataset:
            try:
                self.dataset.delete()
            except:
                pass
        super().tearDown()

    # GET Tests

    def test_get_metadata_authenticated(self):
        """Test GET metadata with authenticated user"""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("id", response.data)
        self.assertIn("uuid", response.data)
        self.assertIn("title", response.data)
        self.assertIn("description", response.data)
        self.assertIn("keywords", response.data)
        self.assertIn("labels", response.data)
        self.assertIn("regions", response.data)

    def test_get_metadata_unauthenticated(self):
        """Test GET metadata without authentication"""
        response = self.client.get(self.url)

        # Should return 403 or 401 depending on permission settings
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_get_metadata_nonexistent_dataset(self):
        """Test GET metadata for non-existent dataset"""
        self.client.force_authenticate(user=self.admin_user)

        url = reverse("datasets-metadata-fields", kwargs={"pk": 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # PATCH Tests

    def test_patch_metadata_title_only(self):
        """Test PATCH to update only title"""
        self.client.force_authenticate(user=self.admin_user)

        payload = {"title": "Updated Test Title"}
        response = self.client.patch(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("success"))
        self.assertIn("dataset", response.data)
        self.assertEqual(response.data["dataset"]["title"], "Updated Test Title")

        # Verify in database
        self.dataset.refresh_from_db()
        self.assertEqual(self.dataset.title, "Updated Test Title")

    def test_patch_metadata_description_only(self):
        """Test PATCH to update only description"""
        self.client.force_authenticate(user=self.admin_user)

        payload = {"description": "This is a test description"}
        response = self.client.patch(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("success"))

        # Verify in database (description maps to abstract)
        self.dataset.refresh_from_db()
        self.assertEqual(self.dataset.abstract, "This is a test description")

    def test_patch_metadata_keywords_as_list(self):
        """Test PATCH to update keywords as list"""
        self.client.force_authenticate(user=self.admin_user)

        payload = {"keywords": ["test", "metadata", "api"]}
        response = self.client.patch(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("success"))

        # Verify keywords in response
        dataset_keywords = response.data["dataset"]["keywords"]
        self.assertIn("test", dataset_keywords)
        self.assertIn("metadata", dataset_keywords)
        self.assertIn("api", dataset_keywords)

    def test_patch_metadata_keywords_as_string(self):
        """Test PATCH to update keywords as comma-separated string"""
        self.client.force_authenticate(user=self.admin_user)

        payload = {"keywords": "test,metadata,api"}
        response = self.client.patch(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("success"))

        # Verify keywords
        dataset_keywords = response.data["dataset"]["keywords"]
        self.assertIn("test", dataset_keywords)
        self.assertIn("metadata", dataset_keywords)
        self.assertIn("api", dataset_keywords)

    def test_patch_metadata_vietnamese_labels(self):
        """Test PATCH to update Vietnamese labels"""
        self.client.force_authenticate(user=self.admin_user)

        payload = {"labels": ["Bản đồ nền"]}
        response = self.client.patch(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("success"))

        # Labels are stored as keywords
        dataset_keywords = response.data["dataset"]["keywords"]
        self.assertIn("Bản đồ nền", dataset_keywords)

    def test_patch_metadata_all_fields(self):
        """Test PATCH to update all fields at once"""
        self.client.force_authenticate(user=self.admin_user)

        payload = {
            "title": "Complete Test Dataset",
            "description": "Full description",
            "keywords": ["keyword1", "keyword2"],
            "labels": ["Bản đồ nền"],
            "regions": ["HCMC"]
        }
        response = self.client.patch(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("success"))

        # Verify all fields
        dataset = response.data["dataset"]
        self.assertEqual(dataset["title"], "Complete Test Dataset")
        self.assertEqual(dataset["description"], "Full description")
        self.assertIn("keyword1", dataset["keywords"])
        self.assertIn("keyword2", dataset["keywords"])
        self.assertIn("Bản đồ nền", dataset["keywords"])

    def test_patch_metadata_unauthenticated(self):
        """Test PATCH without authentication"""
        payload = {"title": "Should Fail"}
        response = self.client.patch(self.url, payload, format="json")

        # Should return 403 or 401
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_patch_metadata_without_permission(self):
        """Test PATCH without edit permission"""
        # Login as different user who doesn't own the dataset
        other_user = get_user_model().objects.get(username="norman")
        self.client.force_authenticate(user=other_user)

        payload = {"title": "Should Fail"}
        response = self.client.patch(self.url, payload, format="json")

        # Should return 403 or 404 depending on permission setup
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    # Validation Tests

    def test_patch_metadata_invalid_title_type(self):
        """Test PATCH with invalid title type"""
        self.client.force_authenticate(user=self.admin_user)

        payload = {"title": 12345}  # Should be string
        response = self.client.patch(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_patch_metadata_invalid_keywords_type(self):
        """Test PATCH with invalid keywords type"""
        self.client.force_authenticate(user=self.admin_user)

        payload = {"keywords": 12345}  # Should be list or string
        response = self.client.patch(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_patch_metadata_invalid_payload_format(self):
        """Test PATCH with non-dict payload"""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.patch(self.url, "invalid", format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_metadata_empty_payload(self):
        """Test PATCH with empty payload (should succeed without changes)"""
        self.client.force_authenticate(user=self.admin_user)

        original_title = self.dataset.title

        response = self.client.patch(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("success"))

        # Title should remain unchanged
        self.dataset.refresh_from_db()
        self.assertEqual(self.dataset.title, original_title)

    # Integration Tests

    def test_get_then_patch_workflow(self):
        """Test realistic workflow: GET metadata, modify, PATCH back"""
        self.client.force_authenticate(user=self.admin_user)

        # Step 1: GET current metadata
        get_response = self.client.get(self.url)
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)

        # Step 2: Modify some fields
        metadata = get_response.data
        metadata["title"] = "Modified Title"
        metadata["keywords"] = metadata.get("keywords", []) + ["new_keyword"]

        # Step 3: PATCH updated metadata
        patch_payload = {
            "title": metadata["title"],
            "keywords": metadata["keywords"]
        }
        patch_response = self.client.patch(self.url, patch_payload, format="json")

        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertTrue(patch_response.data.get("success"))

        # Step 4: Verify changes
        self.dataset.refresh_from_db()
        self.assertEqual(self.dataset.title, "Modified Title")
        self.assertIn("new_keyword", [kw.name for kw in self.dataset.keywords.all()])

    def test_patch_preserves_other_fields(self):
        """Test that PATCH only updates specified fields"""
        self.client.force_authenticate(user=self.admin_user)

        # Set initial state
        self.dataset.title = "Original Title"
        self.dataset.abstract = "Original Abstract"
        self.dataset.save()

        # Update only title
        payload = {"title": "New Title"}
        response = self.client.patch(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify title changed but abstract didn't
        self.dataset.refresh_from_db()
        self.assertEqual(self.dataset.title, "New Title")
        self.assertEqual(self.dataset.abstract, "Original Abstract")


class MetadataFieldsPermissionTestCase(GeoNodeBaseTestSupport, APITestCase):
    """Tests for permission checks on metadata_fields endpoint"""

    fixtures = ["initial_data.json", "group_test_data.json", "default_oauth_apps.json"]

    def setUp(self):
        super().setUp()
        self.owner = get_user_model().objects.get(username="admin")
        self.other_user = get_user_model().objects.get(username="bobby")

        self.dataset = create_single_dataset("permission_test_dataset", owner=self.owner)
        self.url = reverse("datasets-metadata-fields", kwargs={"pk": self.dataset.id})

    def tearDown(self):
        if self.dataset:
            try:
                self.dataset.delete()
            except:
                pass
        super().tearDown()

    def test_owner_can_edit(self):
        """Test that dataset owner can edit metadata"""
        self.client.force_authenticate(user=self.owner)

        payload = {"title": "Owner Edit"}
        response = self.client.patch(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("success"))

    def test_non_owner_without_permission_cannot_edit(self):
        """Test that non-owner without permission cannot edit"""
        # Set dataset to private (only owner can access)
        self.dataset.set_permissions({"users": {}})

        self.client.force_authenticate(user=self.other_user)

        payload = {"title": "Should Fail"}
        response = self.client.patch(self.url, payload, format="json")

        # Should fail with 403 or 404
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_user_with_permission_can_edit(self):
        """Test that user with edit permission can edit metadata"""
        # Grant edit permission to other_user
        self.dataset.set_permissions({
            "users": {
                self.other_user.username: ["base.change_resourcebase_metadata"]
            }
        })

        self.client.force_authenticate(user=self.other_user)

        payload = {"title": "Permitted Edit"}
        response = self.client.patch(self.url, payload, format="json")

        # Should succeed
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("success"))

    def test_user_can_view_without_edit_permission(self):
        """Test that user with view permission can GET but not PATCH"""
        # Grant view permission only
        self.dataset.set_permissions({
            "users": {
                self.other_user.username: ["base.view_resourcebase"]
            }
        })

        self.client.force_authenticate(user=self.other_user)

        # GET should succeed
        get_response = self.client.get(self.url)
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)

        # PATCH should fail
        patch_response = self.client.patch(self.url, {"title": "Should Fail"}, format="json")
        self.assertIn(patch_response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

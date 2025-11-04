#########################################################################
#
# Copyright (C) 2020 OSGeo
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
from drf_spectacular.utils import extend_schema

from dynamic_rest.viewsets import DynamicModelViewSet
from dynamic_rest.filters import DynamicFilterBackend, DynamicSortingFilter

from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.authentication import SessionAuthentication, BasicAuthentication

from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from rest_framework.response import Response

from geonode.base.api.filters import DynamicSearchFilter, ExtentFilter
from geonode.base.api.mixins import AdvertisedListMixin
from geonode.base.api.pagination import GeoNodeApiPagination
from geonode.base.api.permissions import UserHasPerms
from geonode.base.api.views import ApiPresetsInitializer
from geonode.layers.api.exceptions import GeneralDatasetException, InvalidDatasetException, InvalidMetadataException
from geonode.layers.metadata import parse_metadata
from geonode.layers.models import Dataset
from geonode.maps.api.serializers import SimpleMapLayerSerializer, SimpleMapSerializer
from geonode.resource.utils import update_resource
from geonode.resource.manager import resource_manager
from rest_framework.exceptions import NotFound

from geonode.storage.manager import StorageManager

from .serializers import (
    DatasetSerializer,
    DatasetListSerializer,
    DatasetMetadataSerializer,
)
from .permissions import DatasetPermissionsFilter

import logging

logger = logging.getLogger(__name__)


class DatasetViewSet(ApiPresetsInitializer, DynamicModelViewSet, AdvertisedListMixin):
    """
    API endpoint that allows layers to be viewed or edited.
    """

    http_method_names = ["get", "patch", "put"]
    authentication_classes = [SessionAuthentication, BasicAuthentication, OAuth2Authentication]
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        UserHasPerms(perms_dict={"default": {"POST": ["base.add_resourcebase"]}}),
    ]
    filter_backends = [
        DynamicFilterBackend,
        DynamicSortingFilter,
        DynamicSearchFilter,
        ExtentFilter,
        DatasetPermissionsFilter,
    ]
    queryset = Dataset.objects.all().order_by("-created")
    serializer_class = DatasetSerializer
    pagination_class = GeoNodeApiPagination

    def get_serializer_class(self):
        if self.action == "list":
            return DatasetListSerializer
        return DatasetSerializer

    def partial_update(self, request, *args, **kwargs):
        result = super().partial_update(request, *args, **kwargs)

        dataset = self.get_object()
        resource_manager.update(dataset.uuid, instance=dataset, notify=True),

        return result

    @extend_schema(
        request=DatasetMetadataSerializer,
        methods=["put"],
        responses={200},
        description="API endpoint to upload metadata file.",
    )
    @action(
        detail=False,
        url_path="(?P<pk>\d+)/metadata",  # noqa
        url_name="replace-metadata",
        methods=["put"],
        serializer_class=DatasetMetadataSerializer,
        permission_classes=[
            IsAuthenticated,
            UserHasPerms(perms_dict={"default": {"PUT": ["base.change_resourcebase_metadata"]}}),
        ],
    )
    def metadata(self, request, pk=None, *args, **kwargs):
        """
        Endpoint to upload ISO metadata
        Usage Example:

        import requests

        dataset_id = 1
        url = f"http://localhost:8080/api/v2/datasets/{dataset_id}/metadata"
        files=[
            ('metadata_file',('metadata.xml',open('/home/user/metadata.xml','rb'),'text/xml'))
        ]
        headers = {
            'Authorization': 'Basic dXNlcjpwYXNzd29yZA=='
        }
        response = requests.request("PUT", url, payload={}, files=files)

        cURL example:
        curl --location --request PUT 'http://localhost:8000/api/v2/datasets/{dataset_id}/metadata' \
        --form 'metadata_file=@/home/user/metadata.xml'
        """
        out = {}
        storage_manager = None
        if not self.queryset.filter(id=pk).exists():
            raise NotFound(detail=f"Dataset with ID {pk} is not available")
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            raise InvalidDatasetException(detail=serializer.errors)
        try:
            data = serializer.data.copy()
            if not data["metadata_file"]:
                raise InvalidMetadataException(detail="A valid metadata file must be specified")
            storage_manager = StorageManager(remote_files=data)
            storage_manager.clone_remote_files()
            file = storage_manager.get_retrieved_paths()
            metadata_file = file["metadata_file"]
            dataset = self.queryset.get(id=pk)
            try:
                dataset_uuid, vals, regions, keywords, _ = parse_metadata(open(metadata_file).read())
            except Exception:
                raise InvalidMetadataException(detail="Unsupported metadata format")
            if dataset_uuid and dataset.uuid != dataset_uuid:
                raise InvalidMetadataException(
                    detail="The UUID identifier from the XML Metadata, is different from the one saved"
                )
            try:
                updated_dataset = update_resource(dataset, metadata_file, regions, keywords, vals)
                updated_dataset.save()  # This also triggers the recreation of the XML metadata file according to the updated values
            except Exception:
                raise GeneralDatasetException(detail="Failed to update metadata")
            out["success"] = True
            out["message"] = ["Metadata successfully updated"]
            return Response(out)
        except Exception as e:
            raise e
        finally:
            if storage_manager:
                storage_manager.delete_retrieved_paths()

    @extend_schema(
        methods=["get", "patch"],
        responses={
            200: {
                "description": "Metadata successfully retrieved or updated",
                "content": {
                    "application/json": {
                        "example": {
                            "id": 28,
                            "title": "HienTrangSDD_2020",
                            "description": "Hiện trạng sử dụng đất 2020",
                            "keywords": ["hiện trạng", "sử dụng đất", "2020"],
                            "labels": ["Bản đồ nền"],
                            "regions": ["HCMC"],
                            "category": "farming",
                            "abstract": "Hiện trạng sử dụng đất 2020"
                        }
                    }
                }
            },
            400: {"description": "Invalid request payload"},
            403: {"description": "Permission denied"},
            404: {"description": "Dataset not found"}
        },
        description="""
        GET: Retrieve editable metadata for a dataset (for pre-filling edit dialogs).
        PATCH: Update metadata fields for an existing dataset.

        Example PATCH payload:
        {
          "title": "HienTrangSDD_2020",
          "description": "Test description",
          "keywords": ["test", "metadata"],
          "labels": ["Bản đồ nền"],
          "regions": ["HCMC"]
        }
        """,
    )
    @action(
        detail=True,
        methods=["get", "patch"],
        url_path="metadata_fields",
        url_name="metadata-fields",
        permission_classes=[
            IsAuthenticated,
            UserHasPerms(perms_dict={
                "default": {
                    "GET": ["base.view_resourcebase"],
                    "PATCH": ["base.change_resourcebase_metadata"]
                }
            }),
        ],
    )
    def metadata_fields(self, request, pk=None, *args, **kwargs):
        """
        GET/PATCH metadata fields for a dataset.

        This endpoint allows QGIS plugin users to:
        1. GET metadata for pre-filling edit dialogs
        2. PATCH metadata after successful upload

        Usage Example (GET):

        import requests

        dataset_id = 28
        url = f"http://localhost:8080/api/v2/datasets/{dataset_id}/metadata_fields/"
        headers = {'Authorization': 'Bearer YOUR_TOKEN'}
        response = requests.get(url, headers=headers)
        metadata = response.json()

        Usage Example (PATCH):

        import requests

        dataset_id = 28
        url = f"http://localhost:8080/api/v2/datasets/{dataset_id}/metadata_fields/"
        headers = {'Authorization': 'Bearer YOUR_TOKEN'}
        payload = {
            "title": "HienTrangSDD_2020",
            "description": "Hiện trạng sử dụng đất 2020",
            "keywords": ["hiện trạng", "sử dụng đất", "2020"],
            "labels": ["Bản đồ nền"]
        }
        response = requests.patch(url, json=payload, headers=headers)

        cURL example (GET):
        curl --location 'http://localhost:8000/api/v2/datasets/28/metadata_fields/' \
        --header 'Authorization: Bearer YOUR_TOKEN'

        cURL example (PATCH):
        curl --location --request PATCH 'http://localhost:8000/api/v2/datasets/28/metadata_fields/' \
        --header 'Content-Type: application/json' \
        --header 'Authorization: Bearer YOUR_TOKEN' \
        --data '{
            "title": "HienTrangSDD_2020",
            "description": "Test description",
            "keywords": ["test", "metadata"],
            "labels": ["Bản đồ nền"]
        }'
        """
        dataset = self.get_object()

        if request.method == "GET":
            # Return current metadata for pre-filling edit dialog
            metadata = {
                "id": dataset.id,
                "uuid": str(dataset.uuid),
                "title": dataset.title or "",
                "description": dataset.abstract or "",
                "abstract": dataset.abstract or "",  # Alias for description
                "keywords": [kw.name for kw in dataset.keywords.all()],
                "category": dataset.category.identifier if dataset.category else None,
                "regions": [region.name for region in dataset.regions.all()],
            }

            # Add labels using same logic as serializer
            labels = []
            category_mapping = {
                'farming': 'Thuỷ lợi',
                'location': 'Bản đồ nền',
                'climatologyMeteorologyAtmosphere': 'Khí tượng thuỷ văn',
                'imageryBaseMapsEarthCover': 'Viễn thám',
                'inlandWaters': 'Thuỷ lợi',
                'transportation': 'Bản đồ nền',
                'boundaries': 'Bản đồ nền',
                'elevation': 'Bản đồ nền',
                'geoscientificInformation': 'Bản đồ nền',
            }

            if dataset.category:
                category_id = dataset.category.identifier if hasattr(dataset.category, 'identifier') else None
                if category_id and category_id in category_mapping:
                    label = category_mapping[category_id]
                    if label not in labels:
                        labels.append(label)

            vietnamese_labels = ['Thuỷ lợi', 'Bản đồ nền', 'Khí tượng thuỷ văn', 'Viễn thám']
            for keyword in dataset.keywords.all():
                if keyword.name in vietnamese_labels and keyword.name not in labels:
                    labels.append(keyword.name)

            metadata["labels"] = labels

            return Response(metadata)

        elif request.method == "PATCH":
            # Update metadata fields
            try:
                payload = request.data

                # Validate payload
                if not isinstance(payload, dict):
                    return Response(
                        {"error": "Request payload must be a JSON object"},
                        status=400
                    )

                # Prepare values for resource_manager.update()
                vals = {}
                keywords_list = []
                regions_list = []

                # Extract and validate fields
                if "title" in payload:
                    title = payload["title"]
                    if not isinstance(title, str):
                        return Response({"error": "title must be a string"}, status=400)
                    vals["title"] = title.strip()

                if "description" in payload:
                    description = payload["description"]
                    if not isinstance(description, str):
                        return Response({"error": "description must be a string"}, status=400)
                    vals["abstract"] = description.strip()
                elif "abstract" in payload:  # Support alias
                    abstract = payload["abstract"]
                    if not isinstance(abstract, str):
                        return Response({"error": "abstract must be a string"}, status=400)
                    vals["abstract"] = abstract.strip()

                if "keywords" in payload:
                    keywords = payload["keywords"]
                    # Support both list and comma-separated string
                    if isinstance(keywords, str):
                        keywords_list = [k.strip() for k in keywords.split(',') if k.strip()]
                    elif isinstance(keywords, list):
                        keywords_list = [str(k).strip() for k in keywords if str(k).strip()]
                    else:
                        return Response({"error": "keywords must be a list or comma-separated string"}, status=400)

                if "regions" in payload:
                    regions = payload["regions"]
                    # Support both list and comma-separated string
                    if isinstance(regions, str):
                        regions_list = [r.strip() for r in regions.split(',') if r.strip()]
                    elif isinstance(regions, list):
                        regions_list = [str(r).strip() for r in regions if str(r).strip()]
                    else:
                        return Response({"error": "regions must be a list or comma-separated string"}, status=400)

                # Handle labels by adding to keywords (Vietnamese labels)
                if "labels" in payload:
                    labels = payload["labels"]
                    vietnamese_labels = ['Thuỷ lợi', 'Bản đồ nền', 'Khí tượng thuỷ văn', 'Viễn thám']

                    if isinstance(labels, str):
                        labels_list = [l.strip() for l in labels.split(',') if l.strip()]
                    elif isinstance(labels, list):
                        labels_list = [str(l).strip() for l in labels if str(l).strip()]
                    else:
                        return Response({"error": "labels must be a list or comma-separated string"}, status=400)

                    # Add valid Vietnamese labels to keywords
                    for label in labels_list:
                        if label in vietnamese_labels and label not in keywords_list:
                            keywords_list.append(label)

                # Apply metadata using resource_manager
                logger.info(f"[METADATA-API] Updating dataset {dataset.id} with metadata:")
                logger.info(f"[METADATA-API]   - vals: {vals}")
                logger.info(f"[METADATA-API]   - keywords: {keywords_list}")
                logger.info(f"[METADATA-API]   - regions: {regions_list}")

                resource_manager.update(
                    uuid=str(dataset.uuid),
                    instance=dataset.get_real_instance(),
                    vals=vals,
                    keywords=keywords_list if keywords_list else None,
                    regions=regions_list if regions_list else None,
                    notify=True
                )

                # Refresh from database
                dataset.refresh_from_db()

                # Return updated metadata
                response_data = {
                    "success": True,
                    "message": "Metadata successfully updated",
                    "dataset": {
                        "id": dataset.id,
                        "uuid": str(dataset.uuid),
                        "title": dataset.title,
                        "description": dataset.abstract,
                        "keywords": [kw.name for kw in dataset.keywords.all()],
                        "regions": [region.name for region in dataset.regions.all()],
                    }
                }

                logger.info(f"[METADATA-API] Successfully updated dataset {dataset.id}")

                return Response(response_data, status=200)

            except Exception as e:
                logger.exception(f"[METADATA-API] Error updating metadata for dataset {dataset.id}: {e}")
                return Response(
                    {"error": f"Failed to update metadata: {str(e)}"},
                    status=500
                )

    @extend_schema(
        methods=["get"],
        responses={200: SimpleMapLayerSerializer(many=True)},
        description="API endpoint allowing to retrieve the MapLayers list.",
    )
    @action(detail=True, methods=["get"])
    def maplayers(self, request, pk=None, *args, **kwargs):
        dataset = self.get_object()
        resources = dataset.maplayers
        return Response(SimpleMapLayerSerializer(many=True).to_representation(resources))

    @extend_schema(
        methods=["get"],
        responses={200: SimpleMapSerializer(many=True)},
        description="API endpoint allowing to retrieve maps using the dataset.",
    )
    @action(detail=True, methods=["get"])
    def maps(self, request, pk=None, *args, **kwargs):
        dataset = self.get_object()
        resources = dataset.maps
        return Response(SimpleMapSerializer(many=True).to_representation(resources))

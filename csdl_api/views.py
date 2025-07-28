from django.shortcuts import render

# Create your views here.
"""
csdl_api.views
--------------
Endpoints for the custom “CSDL ĐBS HCM” plugin.
"""
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from .permissions import CSDLPermission

class DuongBoViewSet(ViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly, CSDLPermission]
    """
    API kiểm tra tích hợp `csdl_api`.
    * `GET /api/csdl/duong-bo/` → trả về thông báo đơn giản
    """
    def list(self, request):
        """Trả về thông báo xác nhận API hoạt động."""
        return Response(
            {"detail": "CSDL API is up and running 🎉"},
            status=status.HTTP_200_OK,
        )
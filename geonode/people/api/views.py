from django.conf import settings
from dynamic_rest.filters import DynamicFilterBackend, DynamicSortingFilter
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from drf_spectacular.utils import extend_schema
from dynamic_rest.viewsets import DynamicModelViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from geonode.base.models import ResourceBase
from geonode.base.api.filters import DynamicSearchFilter
from geonode.groups.models import GroupProfile, GroupMember
from geonode.base.api.permissions import IsOwnerOrAdmin
from geonode.base.api.serializers import GroupProfileSerializer, ResourceBaseSerializer
from geonode.base.api.pagination import GeoNodeApiPagination
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from geonode.security.utils import get_visible_resources
from guardian.shortcuts import get_objects_for_user
from rest_framework.exceptions import PermissionDenied
from geonode.people.utils import check_user_deletion_rules
from geonode.people.api.serializers import UserSerializer, PasswordChangeSerializer
from geonode.people.utils import get_available_users
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404


class UserViewSet(DynamicModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """

    http_method_names = ["get", "post", "patch", "delete"]
    authentication_classes = [SessionAuthentication, BasicAuthentication, OAuth2Authentication]
    permission_classes = [
        IsAuthenticated,
        IsOwnerOrAdmin,
    ]
    filter_backends = [DynamicFilterBackend, DynamicSortingFilter, DynamicSearchFilter]
    serializer_class = UserSerializer
    pagination_class = GeoNodeApiPagination

    def get_queryset(self):
        """
        Filters and sorts users.
        """
        if self.request and self.request.user:
            queryset = get_available_users(self.request.user)
        else:
            queryset = get_user_model().objects.all()
        
        queryset = queryset.prefetch_related("groups")

        # Set up eager loading to avoid N+1 selects
        queryset = self.get_serializer_class().setup_eager_loading(queryset)
        return queryset.order_by("username")

    def create(self, request, *args, **kwargs):
        """
        Create a new user. Only superusers can create users.
        """
        if not request.user.is_superuser:
            return Response({
                "success": False,
                "errors": ["Only superusers can create new users."],
                "code": "permission_denied"
            }, status=403)

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "success": False,
                "errors": self._format_validation_errors(serializer.errors),
                "code": "invalid"
            }, status=400)

        instance = serializer.save()

        # Handle group_profiles if provided
        group_slugs = request.data.get("group_profiles")
        if group_slugs is not None:
            self._update_group_profiles(instance, group_slugs)

        # Return success response with created user data
        response_serializer = self.get_serializer(instance)
        return Response({
            "success": True,
            "data": response_serializer.data,
            "message": "User created successfully"
        }, status=201)

    def _format_validation_errors(self, errors):
        """
        Format validation errors into a list of strings
        """
        formatted_errors = []
        for field, field_errors in errors.items():
            if field == 'non_field_errors':
                formatted_errors.extend(field_errors)
            else:
                for error in field_errors:
                    formatted_errors.append(f"{field}: {error}")
        return formatted_errors

    def perform_create(self, serializer):
        # This method is now handled by the create method above
        pass
    
    def _is_admin_user(self, user):
        """
        Check if user is admin (superuser or has qtv role)
        """
        if user.is_superuser:
            return True

        # Check if user is in qtv group
        from geonode.groups.models import GroupProfile, GroupMember
        try:
            qtv_group = GroupProfile.objects.get(slug='qtv')
            return GroupMember.objects.filter(user=user, group=qtv_group).exists()
        except GroupProfile.DoesNotExist:
            # If qtv group doesn't exist, only superusers can delete
            return False

    def _update_group_profiles(self, user, group_slugs):
        from geonode.groups.models import GroupProfile, GroupMember

        # Xoá hết nhóm cũ
        GroupMember.objects.filter(user=user).delete()

        # Thêm lại nhóm mới từ slug
        for slug in group_slugs:
            try:
                group = GroupProfile.objects.get(slug=slug)
                GroupMember.objects.create(user=user, group=group)
            except GroupProfile.DoesNotExist:
                continue

    @extend_schema(
        methods=["patch", "put"],
        request=UserSerializer,
        responses={
            200: {"description": "User updated successfully"},
            400: {"description": "Validation error"},
            403: {"description": "Permission denied"}
        },
        description="API endpoint for updating user information. Superusers can update any user including group_profiles. Regular users can only update their own profile (email, first_name, last_name). For convenience, users can also use /api/v2/users/me/update/ to update their own profile.",
    )
    def update(self, request, *args, **kwargs):
        """
        Update an existing user. Only superusers can update other users.
        Users can update their own profile (except username).
        """
        instance = self.get_object()

        # Check permissions
        if not request.user.is_superuser and request.user != instance:
            return Response({
                "success": False,
                "errors": ["You can only update your own profile, or you must be a superuser to update other users."],
                "code": "permission_denied"
            }, status=403)

        # For non-superusers updating their own profile, remove restricted fields
        if not request.user.is_superuser and request.user == instance:
            # Remove fields that only superusers can update
            restricted_fields = ['is_superuser', 'is_staff', 'group_profiles']
            for field in restricted_fields:
                if field in request.data:
                    return Response({
                        "success": False,
                        "errors": [f"Only superusers can update the '{field}' field."],
                        "code": "permission_denied"
                    }, status=403)

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({
                "success": False,
                "errors": self._format_validation_errors(serializer.errors),
                "code": "invalid"
            }, status=400)

        # Save the user
        serializer.save()

        # Handle group_profiles if provided (only for superusers)
        if request.user.is_superuser:
            group_slugs = request.data.get("group_profiles")
            if group_slugs is not None:
                self._update_group_profiles(instance, group_slugs)

        # Return success response with updated user data
        response_serializer = self.get_serializer(instance)
        return Response({
            "success": True,
            "data": response_serializer.data,
            "message": "User updated successfully"
        }, status=200)

    @extend_schema(
        methods=["delete"],
        responses={
            200: {"description": "User deleted successfully"},
            403: {"description": "Permission denied"},
            400: {"description": "Cannot delete user - validation rules violated"}
        },
        description="API endpoint allowing admins (superusers or users with 'qtv' role) to delete users. Cannot delete own account or violate deletion rules.",
    )
    def destroy(self, request, *args, **kwargs):
        """
        Delete a user. Only superusers or users with 'qtv' role can delete users.
        Users cannot delete their own account.
        """
        instance = self.get_object()

        # Check if user has admin privileges
        if not self._is_admin_user(request.user):
            return Response({
                "success": False,
                "errors": ["Only superusers or users with 'qtv' role can delete users."],
                "code": "permission_denied"
            }, status=403)

        # Prevent users from deleting their own account
        if request.user == instance:
            return Response({
                "success": False,
                "errors": ["You cannot delete your own account."],
                "code": "permission_denied"
            }, status=403)

        # Check deletion rules
        deletable, errors = check_user_deletion_rules(instance)
        if not deletable:
            return Response({
                "success": False,
                "errors": [f"Cannot delete user: {', '.join(errors)}"],
                "code": "validation_failed"
            }, status=400)

        # Store user info for response
        user_info = {
            "id": instance.id,
            "username": instance.username,
            "email": instance.email
        }

        # Delete the user
        instance.delete()

        return Response({
            "success": True,
            "data": user_info,
            "message": "User deleted successfully"
        }, status=200)

    def perform_destroy(self, instance):
        # This method is now handled by the destroy method above
        pass

    @extend_schema(
        methods=["get"],
        responses={200: ResourceBaseSerializer(many=True)},
        description="API endpoint allowing to retrieve the Resources visible to the user.",
    )
    @action(detail=True, methods=["get"])
    def resources(self, request, pk=None):
        user = self.get_object()
        permitted = get_objects_for_user(user, "base.view_resourcebase")
        qs = ResourceBase.objects.all().filter(id__in=permitted).order_by("title")

        resources = get_visible_resources(
            qs,
            user,
            admin_approval_required=settings.ADMIN_MODERATE_UPLOADS,
            unpublished_not_visible=settings.RESOURCE_PUBLISHING,
            private_groups_not_visibile=settings.GROUP_PRIVATE_RESOURCES,
        )

        paginator = GeoNodeApiPagination()
        paginator.page_size = request.GET.get("page_size", 10)
        result_page = paginator.paginate_queryset(resources, request)
        serializer = ResourceBaseSerializer(result_page, embed=True, many=True, context={"request": request})
        return paginator.get_paginated_response({"resources": serializer.data})

    @extend_schema(
        methods=["get"],
        responses={200: GroupProfileSerializer(many=True)},
        description="API endpoint allowing to retrieve the Groups the user is member of.",
    )
    @action(detail=True, methods=["get"])
    def groups(self, request, pk=None):
        user = self.get_object()
        qs_ids = GroupMember.objects.filter(user=user).values_list("group", flat=True)
        groups = GroupProfile.objects.filter(id__in=qs_ids)
        return Response(GroupProfileSerializer(embed=True, many=True).to_representation(groups))

    @action(detail=True, methods=["post"])
    def remove_from_group_manager(self, request, pk=None):
        user = self.get_object()
        target_ids = request.data.get("groups", [])
        user_groups = []
        invalid_groups = []

        if not target_ids:
            return Response({"error": "No groups IDs were provided"}, status=400)

        if target_ids == "ALL":
            user_groups = GroupProfile.groups_for_user(user)
        else:
            target_ids = set(target_ids)
            user_groups = GroupProfile.groups_for_user(user).filter(group_id__in=target_ids)
            # check for groups that user is not part of:
            invalid_groups.extend(target_ids - set(ug.group_id for ug in user_groups))

        for group in user_groups:
            group.demote(user)
        group_names = [group.title for group in user_groups]

        payload = {"success": f"User removed as a group manager from : {', '.join(group_names)}"}

        if invalid_groups:
            payload["error"] = f"User is not manager of the following groups: : {invalid_groups}"
            return Response(payload, status=400)
        return Response(payload, status=200)

    @action(detail=True, methods=["post"])
    def transfer_resources(self, request, pk=None):
        user = self.get_object()
        admin = get_user_model().objects.filter(is_superuser=True, is_staff=True).first()
        target_user = request.data.get("owner")

        target = None
        if target_user == "DEFAULT":
            if not admin:
                return Response("Principal User not found", status=500)
            target = admin
        else:
            target = get_object_or_404(get_user_model(), id=target_user)

        if target == user:
            return Response("Cannot reassign to self", status=400)

        # transfer to target
        ResourceBase.objects.filter(owner=user).update(owner=target or user)

        return Response("Resources transfered successfully", status=200)

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @extend_schema(
        methods=["patch", "put"],
        request=UserSerializer,
        responses={
            200: {"description": "Profile updated successfully"},
            400: {"description": "Validation error"}
        },
        description="API endpoint allowing users to update their own profile information. Fields: email, first_name, last_name. Username cannot be changed.",
    )
    @action(detail=False, methods=["patch", "put"], url_path="me/update")
    def update_me(self, request):
        """
        Update the authenticated user's own profile.
        Users can update: email, first_name, last_name
        """
        instance = request.user

        # Remove fields that users cannot update themselves
        restricted_fields = ['username', 'is_superuser', 'is_staff', 'group_profiles']
        for field in restricted_fields:
            if field in request.data:
                return Response({
                    "success": False,
                    "errors": [f"You cannot update the '{field}' field. Contact an administrator if needed."],
                    "code": "permission_denied"
                }, status=403)

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({
                "success": False,
                "errors": self._format_validation_errors(serializer.errors),
                "code": "invalid"
            }, status=400)

        # Save the user
        serializer.save()

        # Return success response with updated user data
        response_serializer = self.get_serializer(instance)
        return Response({
            "success": True,
            "data": response_serializer.data,
            "message": "Profile updated successfully"
        }, status=200)

    @extend_schema(
        methods=["post"],
        request=PasswordChangeSerializer,
        responses={
            200: {"description": "Password changed successfully"},
            400: {"description": "Validation error"}
        },
        description="API endpoint allowing users to change their password. Requires current password, new password, and confirm password.",
    )
    @action(detail=False, methods=["post"], url_path="change-password")
    def change_password(self, request):
        """
        Change password for the authenticated user.
        Requires: current_password, new_password, confirm_password
        """
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Password changed successfully"},
                status=200
            )

        return Response(serializer.errors, status=400)
# from geonode.base.api.serializers import BaseDynamicModelSerializer
# import geonode.base.api.serializers as base_serializers
import logging
from django.contrib.auth.password_validation import validate_password
from django.forms import ValidationError as ValidationErrorForm
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.conf import settings
import geonode.base.api.serializers as base_serializers
from geonode.groups.models import GroupMember, GroupProfile

logger = logging.getLogger(__name__)


class UserSerializer(base_serializers.DynamicModelSerializer):

    link = base_serializers.AutoLinkField(read_only=True)
    group_profiles = serializers.SerializerMethodField()
    date_joined = serializers.DateTimeField(read_only=True)

    class Meta:
        ref_name = "UserProfile"
        model = get_user_model()
        name = "user"
        view_name = "users-list"
        fields = (
            "pk",
            "username",
            "first_name",
            "last_name",
            "avatar",
            "perms",
            "is_superuser",
            "is_staff",
            "email",
            "link",
            "group_profiles",
            "date_joined"
        )
    
    def get_group_profiles(self, obj):
        from geonode.base.api.serializers import GroupProfileSerializer
        group_ids = GroupMember.objects.filter(user=obj).values_list("group", flat=True)
        groups = GroupProfile.objects.filter(id__in=group_ids)
        return GroupProfileSerializer(embed=True, many=True).to_representation(groups)

    @staticmethod
    def password_validation(password_payload):
        try:
            validate_password(password_payload)
        except ValidationErrorForm as err:
            raise serializers.ValidationError(detail=",".join(err.messages))
        return make_password(password_payload)

    def validate(self, data):
        request = self.context["request"]
        user = request.user

        # For POST requests (user creation), validate required fields
        if request.method == "POST":
            # Check for required fields
            required_fields = ["username", "email", "password"]
            missing_fields = []

            for field in required_fields:
                if not data.get(field) and not request.data.get(field):
                    missing_fields.append(field)

            if missing_fields:
                raise serializers.ValidationError({
                    field: ["This field is required."] for field in missing_fields
                })

            # Username validation for creation
            username = data.get("username")
            if username and get_user_model().objects.filter(username=username).exists():
                raise serializers.ValidationError({
                    "username": ["A user with that username already exists."]
                })

        # only superusers can edit these permissions
        if not user.is_superuser:
            data.pop("is_superuser", None)
            data.pop("is_staff", None)

        # username cant be changed on updates
        if request.method in ("PUT", "PATCH") and data.get("username"):
            raise serializers.ValidationError({
                "username": ["Username cannot be updated."]
            })

        email = data.get("email")

        # Email validation
        if email:
            # Check if email is unique (excluding current user for updates)
            existing_user = get_user_model().objects.filter(email=email)
            if hasattr(self, 'instance') and self.instance:
                existing_user = existing_user.exclude(id=self.instance.id)

            if existing_user.exists():
                raise serializers.ValidationError({
                    "email": ["A user is already registered with that email."]
                })

        # password validation
        password = request.data.get("password")
        if password:
            data["password"] = self.password_validation(password)
        elif request.method == "POST":
            # Password is required for user creation
            raise serializers.ValidationError({
                "password": ["This field is required."]
            })

        return data

    @classmethod
    def setup_eager_loading(cls, queryset):
        """Perform necessary eager loading of data."""
        queryset = queryset.prefetch_related()
        return queryset

    def to_representation(self, instance):
        # Dehydrate users private fields
        request = self.context.get("request")
        data = super().to_representation(instance)
        if not request or not request.user or not request.user.is_authenticated:
            if "perms" in data:
                del data["perms"]
        elif not request.user.is_superuser and not request.user.is_staff:
            if data["username"] != request.user.username:
                if "perms" in data:
                    del data["perms"]
        return data

    def get_groups(self, obj):
        return list(obj.groups.values_list("name", flat=True))
    
    avatar = base_serializers.AvatarUrlField(240, read_only=True)


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for password change endpoint.
    """
    current_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate_current_password(self, value):
        """
        Validate that the current password is correct.
        """
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        """
        Validate that new password and confirm password match,
        and that new password meets Django's password validation requirements.
        """
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')
        current_password = attrs.get('current_password')

        # Check if new password and confirm password match
        if new_password != confirm_password:
            raise serializers.ValidationError("New password and confirm password do not match.")

        # Check if new password is different from current password
        if new_password == current_password:
            raise serializers.ValidationError("New password must be different from current password.")

        # Validate new password using Django's password validation
        user = self.context['request'].user
        try:
            validate_password(new_password, user)
        except ValidationErrorForm as err:
            raise serializers.ValidationError({
                'new_password': err.messages
            })

        return attrs

    def save(self):
        """
        Save the new password.
        """
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user

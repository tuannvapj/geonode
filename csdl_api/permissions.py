from rest_framework.permissions import BasePermission, SAFE_METHODS

class CSDLPermission(BasePermission):
    """
    • Guest: chỉ GET/HEAD/OPTIONS
    • KTV  : viết được, nhưng chỉ sửa/xoá “của mình” (tạm thời cho phép toàn bộ)
    • QTV  : full quyền
    """

    def has_permission(self, request, view):
        user = request.user

        # 1. Truy cập đọc luôn cho phép
        if request.method in SAFE_METHODS:
            return True

        # 2. Chưa đăng nhập → cấm
        if not user or not user.is_authenticated:
            return False

        # 3. QTV: luôn True
        if user.groups.filter(name="qtv").exists() or user.is_superuser:
            return True

        # 4. KTV: cho phép POST (tạo mới)
        if request.method == "POST" and user.groups.filter(name="ktv").exists():
            return True

        # các method còn lại sẽ kiểm tra mức đối tượng (retrieve/update/delete)
        return True  # tạm chấp nhận, kiểm tra ở has_object_permission

    def has_object_permission(self, request, view, obj):
        """
        • KTV: chỉ sửa/xoá nếu obj.owner == request.user
        • QTV: đã pass từ has_permission
        """
        if request.method in ("PUT", "PATCH", "DELETE"):
            return obj.owner_id == request.user.id or request.user.groups.filter(name="qtv").exists()
        return True
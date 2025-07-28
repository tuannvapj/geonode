from rest_framework import routers
from .views import DuongBoViewSet

router = routers.DefaultRouter()
router.register(r"duong-bo", DuongBoViewSet, basename="duong-bo")
urlpatterns = router.urls
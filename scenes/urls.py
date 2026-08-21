from rest_framework.routers import DefaultRouter
from .views import SceneViewSet

router = DefaultRouter()
router.register('scenes', SceneViewSet, basename='scene')

urlpatterns = router.urls

from rest_framework.routers import DefaultRouter
from .views import EpisodeViewSet

router = DefaultRouter()
router.register('episodes', EpisodeViewSet, basename='episode')

urlpatterns = router.urls

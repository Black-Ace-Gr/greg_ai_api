from rest_framework.routers import DefaultRouter
from .views import VoiceViewSet

router = DefaultRouter()
router.register('voices', VoiceViewSet, basename='voice')

urlpatterns = router.urls

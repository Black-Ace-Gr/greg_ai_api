from rest_framework.routers import DefaultRouter
from .views import VoiceViewSet, VoiceReferenceImageViewSet

router = DefaultRouter()
router.register('voices', VoiceViewSet, basename='voice')
router.register('voice-reference-images', VoiceReferenceImageViewSet, basename='voice-reference-image')


urlpatterns = router.urls

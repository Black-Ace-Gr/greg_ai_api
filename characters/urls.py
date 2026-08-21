from rest_framework.routers import DefaultRouter
from .views import CharacterViewSet, CharacterReferenceImageViewSet

router = DefaultRouter()
router.register('characters', CharacterViewSet, basename='character')
router.register('character-reference-images', CharacterReferenceImageViewSet, basename='character-reference-image')

urlpatterns = router.urls

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Character, CharacterReferenceImage
from .serializers import CharacterSerializer, CharacterReferenceImageSerializer


class CharacterViewSet(viewsets.ModelViewSet):
    queryset = Character.objects.prefetch_related('reference_images')
    serializer_class = CharacterSerializer

    @action(detail=True, methods=['post'], url_path='reference-images')
    def add_reference_image(self, request, pk=None):
        """Upload one reference image for this character's identity anchor set."""
        character = self.get_object()
        serializer = CharacterReferenceImageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(character=character)
        return Response(serializer.data, status=201)

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Character, CharacterReferenceImage
from .serializers import CharacterSerializer, CharacterReferenceImageSerializer
from rest_framework import mixins, viewsets


class CharacterViewSet(viewsets.ModelViewSet):
    queryset = Character.objects.prefetch_related('reference_images')
    serializer_class = CharacterSerializer

    def destroy(self, request, *args, **kwargs):
        character = self.get_object()
        panel_count = character.panels.count()
        line_count = character.dialogue_lines.count()
        if panel_count or line_count:
            return Response(
                {
                    'detail': (
                        f"Can't delete \"{character.name}\" - still used in {panel_count} "
                        f"panel(s) and {line_count} dialogue line(s). Remove it from those "
                        f"scripts first."
                    ),
                },
                status=400,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'], url_path='reference-images')
    def add_reference_image(self, request, pk=None):
        """Upload one reference image for this character's identity anchor set."""
        character = self.get_object()
        serializer = CharacterReferenceImageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(character=character)
        return Response(serializer.data, status=201)


class CharacterReferenceImageViewSet(mixins.DestroyModelMixin, viewsets.GenericViewSet):
    queryset = CharacterReferenceImage.objects.all()
    serializer_class = CharacterReferenceImageSerializer
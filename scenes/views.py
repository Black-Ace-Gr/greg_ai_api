from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Scene, SceneReferenceImage
from .serializers import SceneSerializer, SceneReferenceImageSerializer


class SceneViewSet(viewsets.ModelViewSet):
    queryset = Scene.objects.prefetch_related('reference_images')
    serializer_class = SceneSerializer

    @action(detail=True, methods=['post'], url_path='reference-images')
    def add_reference_image(self, request, pk=None):
        scene = self.get_object()
        serializer = SceneReferenceImageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(scene=scene)
        return Response(serializer.data, status=201)

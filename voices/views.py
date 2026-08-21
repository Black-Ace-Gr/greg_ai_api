from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from starlette.responses import Response
from .models import Voice
from .serializers import VoiceSerializer


class VoiceViewSet(viewsets.ModelViewSet):
    queryset = Voice.objects.all()
    serializer_class = VoiceSerializer
    filterset_fields = ['role']

class VoiceReferenceImageViewSet(mixins.DestroyModelMixin, viewsets.GenericViewSet):
    queryset = Voice.objects.all()
    serializer_class = VoiceSerializer


@action(detail=True, methods=['post'], url_path='sample-audio')
def upload_sample_audio(self, request, pk=None):
    voice = self.get_object()
    sample_audio = request.FILES.get('sample_audio')
    if not sample_audio:
        return Response({'detail': 'sample_audio file is required.'}, status=400)
    voice.sample_audio = sample_audio
    voice.save(update_fields=['sample_audio'])
    return Response(VoiceSerializer(voice, context={'request': request}).data)


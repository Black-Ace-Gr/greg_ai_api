from rest_framework import viewsets
from .models import Voice
from .serializers import VoiceSerializer


class VoiceViewSet(viewsets.ModelViewSet):
    queryset = Voice.objects.all()
    serializer_class = VoiceSerializer
    filterset_fields = ['role']

from rest_framework import serializers
from .models import Voice


class VoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Voice
        fields = ['id', 'name', 'role', 'provider', 'provider_voice_id', 'description', 'sample_audio', 'created_at']

from rest_framework import serializers
from .models import Character, CharacterReferenceImage


class CharacterReferenceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CharacterReferenceImage
        fields = ['id', 'image', 'label', 'order']


class CharacterSerializer(serializers.ModelSerializer):
    reference_images = CharacterReferenceImageSerializer(many=True, read_only=True)

    class Meta:
        model = Character
        fields = ['id', 'name', 'description', 'voice', 'reference_images', 'created_at', 'updated_at']

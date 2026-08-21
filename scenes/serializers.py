from rest_framework import serializers
from .models import Scene, SceneReferenceImage


class SceneReferenceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SceneReferenceImage
        fields = ['id', 'image', 'label', 'order']


class SceneSerializer(serializers.ModelSerializer):
    reference_images = SceneReferenceImageSerializer(many=True, read_only=True)

    class Meta:
        model = Scene
        fields = ['id', 'name', 'description', 'reference_images', 'created_at', 'updated_at']

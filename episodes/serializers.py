from rest_framework import serializers
from .models import Episode, Panel, DialogueLine, GenerationJob
from characters.serializers import CharacterSerializer
from scenes.serializers import SceneSerializer


class DialogueLineWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DialogueLine
        fields = ['character', 'order', 'text']


class DialogueLineReadSerializer(serializers.ModelSerializer):
    character = CharacterSerializer(read_only=True)

    class Meta:
        model = DialogueLine
        fields = ['id', 'character', 'order', 'text', 'audio']


class PanelWriteSerializer(serializers.ModelSerializer):
    """Used when submitting a structured script - accepts nested dialogue lines."""
    dialogue_lines = DialogueLineWriteSerializer(many=True, required=False)

    class Meta:
        model = Panel
        fields = ['order', 'scene', 'characters', 'action_description', 'image_prompt_notes', 'dialogue_lines']

    def create(self, validated_data):
        dialogue_lines_data = validated_data.pop('dialogue_lines', [])
        characters = validated_data.pop('characters', [])
        panel = Panel.objects.create(**validated_data)
        panel.characters.set(characters)
        for line_data in dialogue_lines_data:
            DialogueLine.objects.create(panel=panel, **line_data)
        return panel


class PanelReadSerializer(serializers.ModelSerializer):
    characters = CharacterSerializer(many=True, read_only=True)
    scene = SceneSerializer(read_only=True)
    dialogue_lines = DialogueLineReadSerializer(many=True, read_only=True)

    class Meta:
        model = Panel
        fields = [
            'id', 'order', 'scene', 'characters', 'action_description', 'image_prompt_notes',
            'generated_image', 'narration_audio', 'status', 'dialogue_lines',
        ]


class ScriptSubmitSerializer(serializers.Serializer):
    """Payload shape for POST /episodes/{id}/submit-script/"""
    panels = PanelWriteSerializer(many=True)


class GenerationJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenerationJob
        fields = ['id', 'panel', 'dialogue_line', 'job_type', 'status', 'provider', 'error_message', 'updated_at']


class EpisodeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Episode
        fields = ['id', 'title', 'storyline', 'status', 'final_video', 'created_at', 'updated_at']


class EpisodeDetailSerializer(serializers.ModelSerializer):
    panels = PanelReadSerializer(many=True, read_only=True)

    class Meta:
        model = Episode
        fields = ['id', 'title', 'storyline', 'status', 'final_video', 'panels', 'created_at', 'updated_at']

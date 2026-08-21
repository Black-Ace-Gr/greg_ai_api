from django.db import models


class Voice(models.Model):
    """
    A reusable voice, backed by a TTS provider (e.g. an open-source model
    like Chatterbox). Two kinds:
      - preset stock voices you assign to characters
      - the narrator voice used for scene/action description lines

    provider_voice_id is whatever identifier the TTS provider needs to
    reproduce this voice (a preset name, a cloned voice ID, etc.) - kept
    generic so we can swap TTS providers later without changing the schema.
    """

    class VoiceRole(models.TextChoices):
        CHARACTER = 'character', 'Character voice'
        NARRATOR = 'narrator', 'Narrator voice'

    name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=VoiceRole.choices, default=VoiceRole.CHARACTER)
    provider = models.CharField(max_length=50, default='chatterbox')
    provider_voice_id = models.CharField(max_length=200)
    description = models.TextField(blank=True, help_text="e.g. tone, pitch, accent notes")
    sample_audio = models.FileField(upload_to='voice_samples/', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_role_display()})"

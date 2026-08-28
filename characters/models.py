from django.db import models
from voices.models import Voice


class Character(models.Model):
    """
    A character definition. The actual visual-consistency mechanism lives
    in CharacterReferenceImage - those images are what get passed to the
    image model (e.g. FLUX.2 multi-reference / PuLID) on every generation
    so the character looks the same across panels, no LoRA training
    required to get started.
    """

    name = models.CharField(max_length=100)
    description = models.TextField(
        help_text="Detailed features: appearance, build, clothing, personality, mannerisms"
    )
    voice = models.ForeignKey(
        Voice, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='characters', limit_choices_to={'role': Voice.VoiceRole.CHARACTER}
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class CharacterReferenceImage(models.Model):
    """
    One reference image for a character (e.g. front view, side profile,
    close-up). The full set for a character is what gets sent to the image
    model as identity anchors on every generation involving them.
    """

    character = models.ForeignKey(Character, on_delete=models.PROTECT, related_name='dialogue_lines')
    image = models.ImageField(upload_to='character_references/')
    label = models.CharField(max_length=100, blank=True, help_text="e.g. 'front view', 'three-quarter'")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.character.name} - {self.label or f'ref #{self.order}'}"

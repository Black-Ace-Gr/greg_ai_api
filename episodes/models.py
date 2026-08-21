from django.db import models
from characters.models import Character
from scenes.models import Scene
from voices.models import Voice


class Episode(models.Model):
    """
    Top-level container: your storyline, plus its structured script, plus
    every panel that gets generated and assembled into the final video.
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        SCRIPTED = 'scripted', 'Script submitted'
        GENERATING = 'generating', 'Generating'
        ASSEMBLING = 'assembling', 'Assembling final video'
        COMPLETE = 'complete', 'Complete'
        FAILED = 'failed', 'Failed'

    title = models.CharField(max_length=200)
    storyline = models.TextField(help_text="Your free-form storyline/synopsis for the episode")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    final_video = models.FileField(upload_to='final_videos/', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Panel(models.Model):
    """
    A single panel/beat in the episode - the unit of image generation.
    Roughly one panel per story beat, not a fixed time slice, which is
    what keeps the image-based pipeline cheap (see project notes on
    idea 2 vs idea 1).
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        IMAGE_QUEUED = 'image_queued', 'Image queued'
        IMAGE_READY = 'image_ready', 'Image ready'
        AUDIO_QUEUED = 'audio_queued', 'Audio queued'
        AUDIO_READY = 'audio_ready', 'Audio ready'
        READY = 'ready', 'Ready for assembly'
        FAILED = 'failed', 'Failed'

    episode = models.ForeignKey(Episode, on_delete=models.CASCADE, related_name='panels')
    order = models.PositiveIntegerField(help_text="Position of this panel within the episode")

    scene = models.ForeignKey(Scene, on_delete=models.SET_NULL, null=True, related_name='panels')
    characters = models.ManyToManyField(Character, blank=True, related_name='panels')

    action_description = models.TextField(
        blank=True, help_text="Narration text describing what happens in this panel"
    )
    image_prompt_notes = models.TextField(
        blank=True, help_text="Extra prompt guidance for the image model (camera angle, framing, etc.)"
    )

    generated_image = models.ImageField(upload_to='generated_panels/', blank=True, null=True)
    narration_audio = models.FileField(upload_to='narration_audio/', blank=True, null=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    class Meta:
        ordering = ['episode', 'order']
        unique_together = ('episode', 'order')

    def __str__(self):
        return f"{self.episode.title} - panel {self.order}"


class DialogueLine(models.Model):
    """
    One spoken line within a panel, tied to a character and their voice.
    Rendered both as spoken audio and as an on-panel caption.
    """

    panel = models.ForeignKey(Panel, on_delete=models.CASCADE, related_name='dialogue_lines')
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='dialogue_lines')
    order = models.PositiveIntegerField(default=0)
    text = models.TextField()

    audio = models.FileField(upload_to='dialogue_audio/', blank=True, null=True)

    class Meta:
        ordering = ['panel', 'order']

    def __str__(self):
        return f"{self.character.name}: {self.text[:40]}"


class GenerationJob(models.Model):
    """
    Tracks one async unit of work (an image generation call or a TTS call)
    so a long batch run can resume after an interruption instead of
    restarting from scratch - see the resumability discussion for
    multi-episode generation runs.
    """

    class JobType(models.TextChoices):
        IMAGE = 'image', 'Image generation'
        VOICE = 'voice', 'Voice generation'
        ASSEMBLY = 'assembly', 'Video assembly'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        RUNNING = 'running', 'Running'
        DONE = 'done', 'Done'
        FAILED = 'failed', 'Failed'

    episode = models.ForeignKey(Episode, on_delete=models.CASCADE, related_name='jobs')
    panel = models.ForeignKey(Panel, on_delete=models.CASCADE, null=True, blank=True, related_name='jobs')
    dialogue_line = models.ForeignKey(
        DialogueLine, on_delete=models.CASCADE, null=True, blank=True, related_name='jobs'
    )

    job_type = models.CharField(max_length=20, choices=JobType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    provider = models.CharField(max_length=50, blank=True, help_text="e.g. 'flux2', 'chatterbox'")
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.job_type} job for {self.episode.title} [{self.status}]"

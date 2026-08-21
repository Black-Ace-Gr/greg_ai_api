"""
Pipeline orchestration for an Episode: turning submitted panels/dialogue
into GenerationJobs, and (eventually) driving the actual image/voice
provider calls + FFmpeg assembly.

This module is intentionally the seam between "our own logic" and
"external paid providers". Everything above generate_episode() is free -
it's plain Django ORM work. generate_episode() and the provider calls it
triggers are the only place that ever costs money or needs a rented GPU.

Wiring notes for when you move this behind Celery:
  - Each job created here should become one Celery task.
  - Mark the job RUNNING when the task starts, DONE/FAILED when it ends,
    so a long batch run (see the multi-episode cost discussion) can be
    resumed by re-queuing only jobs still PENDING/RUNNING/FAILED.
"""

from django.db import transaction
from .models import Episode, Panel, GenerationJob


def submit_script(episode: Episode, panels_data: list) -> Episode:
    """
    Replace this episode's panels with the structured script data the
    client submitted, then mark it SCRIPTED. Called from
    EpisodeViewSet.submit_script.

    panels_data is already-validated data from ScriptSubmitSerializer (via
    the nested PanelWriteSerializer), so scene/characters have already been
    resolved to real model instances - build the records directly rather
    than re-running them through the serializer's own validation, which
    expects raw primary keys, not instances.
    """
    from .models import DialogueLine

    with transaction.atomic():
        episode.panels.all().delete()
        for panel_data in panels_data:
            dialogue_lines_data = panel_data.pop('dialogue_lines', [])
            characters = panel_data.pop('characters', [])
            panel = Panel.objects.create(episode=episode, **panel_data)
            panel.characters.set(characters)
            for line_data in dialogue_lines_data:
                DialogueLine.objects.create(panel=panel, **line_data)
        episode.status = Episode.Status.SCRIPTED
        episode.save(update_fields=['status'])
    return episode


def queue_generation_jobs(episode: Episode) -> list[GenerationJob]:
    """
    Create one GenerationJob per unit of billable work:
      - one IMAGE job per panel
      - one VOICE job per dialogue line, plus one per panel with narration
    Nothing here calls a provider yet - it just lays out the work so it
    can be picked up (by a Celery worker, or manually for now) and so
    progress/resume state has somewhere to live.
    """
    jobs = []
    for panel in episode.panels.all():
        jobs.append(GenerationJob.objects.create(
            episode=episode, panel=panel, job_type=GenerationJob.JobType.IMAGE,
        ))
        if panel.action_description:
            jobs.append(GenerationJob.objects.create(
                episode=episode, panel=panel, job_type=GenerationJob.JobType.VOICE,
            ))
        for line in panel.dialogue_lines.all():
            jobs.append(GenerationJob.objects.create(
                episode=episode, panel=panel, dialogue_line=line,
                job_type=GenerationJob.JobType.VOICE,
            ))
    episode.status = Episode.Status.GENERATING
    episode.save(update_fields=['status'])
    return jobs


def run_image_job(job: GenerationJob):
    """
    Calls the inference server (see inference_server/) running on your
    rented GPU instance to generate this panel's image, using the scene's
    and characters' reference images as identity anchors.
    """
    import requests
    from django.conf import settings
    from django.core.files.base import ContentFile

    panel = job.panel
    reference_image_urls = []
    if panel.scene:
        reference_image_urls += [ri.image.path for ri in panel.scene.reference_images.all()]
    for character in panel.characters.all():
        reference_image_urls += [ri.image.path for ri in character.reference_images.all()]

    character_descriptions = "; ".join(
        f"{c.name}: {c.description}" for c in panel.characters.all()
    )
    prompt = (
        f"Realistic, cinematic illustration. Scene: {panel.scene.description if panel.scene else ''}. "
        f"Characters present: {character_descriptions}. Action: {panel.action_description}. "
        f"{panel.image_prompt_notes}"
    ).strip()

    files = [('reference_images', open(p, 'rb')) for p in reference_image_urls]
    try:
        response = requests.post(
            f"{settings.GPU_WORKER_URL}/generate-image",
            data={'prompt': prompt},
            files=files if files else None,
            timeout=300,
        )
        response.raise_for_status()
    finally:
        for _, fh in files:
            fh.close()

    panel.generated_image.save(f"panel_{panel.id}.png", ContentFile(response.content), save=False)
    panel.status = Panel.Status.IMAGE_READY
    panel.save(update_fields=['generated_image', 'status'])
    job.provider = 'flux2'
    job.save(update_fields=['provider'])


def run_voice_job(job: GenerationJob):
    """
    Calls the inference server (see inference_server/) to generate audio
    for either a panel's narration or one dialogue line, using the
    appropriate Voice record.
    """
    import requests
    from django.conf import settings
    from django.core.files.base import ContentFile

    panel = job.panel
    if job.dialogue_line:
        character = job.dialogue_line.character
        voice = character.voice
        text = job.dialogue_line.text
    else:
        # Narration for the panel - needs a narrator Voice to exist.
        from voices.models import Voice
        voice = Voice.objects.filter(role=Voice.VoiceRole.NARRATOR).first()
        text = panel.action_description

    if voice is None:
        raise ValueError("No voice assigned - create a Voice record and link it first.")

    response = requests.post(
        f"{settings.GPU_WORKER_URL}/generate-voice",
        json={
            'text': text,
            'provider_voice_id': voice.provider_voice_id,
        },
        timeout=120,
    )
    response.raise_for_status()

    if job.dialogue_line:
        job.dialogue_line.audio.save(
            f"line_{job.dialogue_line.id}.mp3", ContentFile(response.content), save=False
        )
        job.dialogue_line.save(update_fields=['audio'])
    else:
        panel.narration_audio.save(
            f"panel_{panel.id}_narration.mp3", ContentFile(response.content), save=False
        )
        panel.save(update_fields=['narration_audio'])
    job.provider = 'chatterbox'
    job.save(update_fields=['provider'])


def assemble_episode(episode: Episode):
    """
    Once every panel has an image and every line has audio, render each
    panel as: narration segment (if any) + one clip per dialogue line
    (image + that line's audio + caption), then concatenate every panel's
    clips in order into the final motion comic.

    Pure FFmpeg/CPU work - runs the same whether the image/audio came from
    a real provider or the placeholder generator used for testing.
    """
    import tempfile
    from pathlib import Path
    from django.core.files import File
    from . import ffmpeg_utils

    episode.status = Episode.Status.ASSEMBLING
    episode.save(update_fields=['status'])

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        panel_clip_paths = []

        for panel in episode.panels.all():
            if not panel.generated_image:
                raise ValueError(f"Panel {panel.order} has no generated image yet.")

            image_path = Path(panel.generated_image.path)
            segment_paths = []

            if panel.narration_audio:
                narration_clip = tmp / f"panel{panel.order}_narration.mp4"
                ffmpeg_utils.render_panel_clip(
                    image_path, Path(panel.narration_audio.path), narration_clip,
                    caption_text=None,
                )
                segment_paths.append(narration_clip)

            for line in panel.dialogue_lines.all():
                if not line.audio:
                    raise ValueError(f"Dialogue line {line.id} has no audio yet.")
                line_clip = tmp / f"panel{panel.order}_line{line.order}.mp4"
                caption = f"{line.character.name}: {line.text}"
                ffmpeg_utils.render_panel_clip(
                    image_path, Path(line.audio.path), line_clip,
                    caption_text=caption,
                )
                segment_paths.append(line_clip)

            if not segment_paths:
                raise ValueError(f"Panel {panel.order} has no narration or dialogue audio.")

            if len(segment_paths) == 1:
                panel_clip_paths.append(segment_paths[0])
            else:
                panel_combined = tmp / f"panel{panel.order}_combined.mp4"
                ffmpeg_utils.concatenate_clips(segment_paths, panel_combined)
                panel_clip_paths.append(panel_combined)

        final_path = tmp / "final_episode.mp4"
        ffmpeg_utils.concatenate_clips(panel_clip_paths, final_path)

        with open(final_path, 'rb') as f:
            episode.final_video.save(f"episode_{episode.id}_final.mp4", File(f), save=False)

    episode.status = Episode.Status.COMPLETE
    episode.save(update_fields=['status', 'final_video'])
    return episode

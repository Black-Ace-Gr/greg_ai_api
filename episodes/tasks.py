"""
Celery tasks - the async execution layer around episodes/services.py.
Each task wraps one GenerationJob: mark RUNNING, do the work, mark
DONE/FAILED. This is what actually gets dispatched when you call
queue_generation_jobs() for real, instead of jobs just sitting PENDING.
"""

from celery import shared_task
from django.utils import timezone
from .models import GenerationJob, Episode
from . import services


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def run_job(self, job_id: int):
    job = GenerationJob.objects.get(id=job_id)
    job.status = GenerationJob.Status.RUNNING
    job.save(update_fields=['status'])

    try:
        if job.job_type == GenerationJob.JobType.IMAGE:
            services.run_image_job(job)
        elif job.job_type == GenerationJob.JobType.VOICE:
            services.run_voice_job(job)
        else:
            raise ValueError(f"Unknown job_type {job.job_type}")

        job.status = GenerationJob.Status.DONE
        job.error_message = ''
        job.save(update_fields=['status', 'error_message'])

    except Exception as exc:
        job.status = GenerationJob.Status.FAILED
        job.error_message = str(exc)
        job.save(update_fields=['status', 'error_message'])
        raise self.retry(exc=exc)

    maybe_assemble_episode.delay(job.episode_id)


@shared_task
def maybe_assemble_episode(episode_id: int):
    """
    After each job finishes, check whether every job for this episode is
    DONE - if so, kick off assembly. This is what makes a multi-hour batch
    run resumable: re-queuing only the PENDING/FAILED jobs and calling
    this again picks up right where it left off.

    Several jobs can finish within milliseconds of each other, so this
    uses an atomic compare-and-swap (only flip GENERATING -> ASSEMBLING if
    it's still GENERATING) to guarantee assembly runs exactly once, even
    if multiple jobs trigger this check at nearly the same time.
    """
    episode = Episode.objects.get(id=episode_id)
    jobs = episode.jobs.all()
    if not jobs.exists():
        return
    if jobs.exclude(status=GenerationJob.Status.DONE).exists():
        return  # still work left to do

    claimed = Episode.objects.filter(
        id=episode_id, status=Episode.Status.GENERATING
    ).update(status=Episode.Status.ASSEMBLING)
    if not claimed:
        return  # another task already claimed assembly (or it's done/failed)

    episode.refresh_from_db()
    services.assemble_episode(episode)


@shared_task
def queue_and_dispatch(episode_id: int):
    """Queue every job for an episode and immediately dispatch each as a task."""
    episode = Episode.objects.get(id=episode_id)
    jobs = services.queue_generation_jobs(episode)
    for job in jobs:
        run_job.delay(job.id)
    return len(jobs)

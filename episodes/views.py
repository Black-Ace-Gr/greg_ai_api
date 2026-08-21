from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Episode, GenerationJob
from .serializers import (
    EpisodeListSerializer, EpisodeDetailSerializer,
    ScriptSubmitSerializer, GenerationJobSerializer,
)
from . import services


class EpisodeViewSet(viewsets.ModelViewSet):
    queryset = Episode.objects.prefetch_related('panels__dialogue_lines', 'panels__characters', 'panels__scene')

    def get_serializer_class(self):
        if self.action in ('retrieve', 'submit_script', 'generate'):
            return EpisodeDetailSerializer
        return EpisodeListSerializer

    @action(detail=True, methods=['post'], url_path='submit-script')
    def submit_script(self, request, pk=None):
        """Insert story is already the Episode itself; this is 'insert scripts and dialogues'."""
        episode = self.get_object()
        payload = ScriptSubmitSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        episode = services.submit_script(episode, payload.validated_data['panels'])
        return Response(EpisodeDetailSerializer(episode, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='generate')
    def generate(self, request, pk=None):
        """Kick off generation: queues + dispatches a job per panel/dialogue line."""
        from . import tasks

        episode = self.get_object()
        if episode.status not in (Episode.Status.SCRIPTED, Episode.Status.FAILED):
            return Response(
                {'detail': f"Episode must be SCRIPTED first (currently {episode.status})."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        tasks.queue_and_dispatch.delay(episode.id)
        return Response(
            {'detail': 'Generation dispatched.', 'episode': EpisodeListSerializer(episode).data},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=['get'], url_path='status')
    def episode_status(self, request, pk=None):
        episode = self.get_object()
        jobs = episode.jobs.all()
        counts = {}
        for choice, _ in GenerationJob.Status.choices:
            counts[choice] = jobs.filter(status=choice).count()
        return Response({
            'episode_status': episode.status,
            'job_counts': counts,
            'total_jobs': jobs.count(),
        })

    @action(detail=True, methods=['get'], url_path='jobs')
    def episode_jobs(self, request, pk=None):
        episode = self.get_object()
        return Response(GenerationJobSerializer(episode.jobs.all(), many=True).data)

from django.db import models


class Scene(models.Model):
    """
    A recurring setting/location. Like characters, a scene can carry
    reference images so a location (e.g. 'the family's living room')
    stays visually consistent across panels/episodes.
    """

    name = models.CharField(max_length=100)
    description = models.TextField(help_text="Setting details: environment, lighting, mood")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class SceneReferenceImage(models.Model):
    scene = models.ForeignKey(Scene, on_delete=models.CASCADE, related_name='reference_images')
    image = models.ImageField(upload_to='scene_references/')
    label = models.CharField(max_length=100, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.scene.name} - {self.label or f'ref #{self.order}'}"

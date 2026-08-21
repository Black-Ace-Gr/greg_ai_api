from django.contrib import admin
from .models import Scene, SceneReferenceImage


class SceneReferenceImageInline(admin.TabularInline):
    model = SceneReferenceImage
    extra = 1


@admin.register(Scene)
class SceneAdmin(admin.ModelAdmin):
    list_display = ['name']
    inlines = [SceneReferenceImageInline]

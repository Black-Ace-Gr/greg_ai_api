from django.contrib import admin
from .models import Episode, Panel, DialogueLine, GenerationJob


class DialogueLineInline(admin.TabularInline):
    model = DialogueLine
    extra = 0


class PanelInline(admin.TabularInline):
    model = Panel
    extra = 0
    show_change_link = True


@admin.register(Episode)
class EpisodeAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'created_at']
    inlines = [PanelInline]


@admin.register(Panel)
class PanelAdmin(admin.ModelAdmin):
    list_display = ['episode', 'order', 'status']
    inlines = [DialogueLineInline]


admin.site.register(GenerationJob)

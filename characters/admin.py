from django.contrib import admin
from .models import Character, CharacterReferenceImage


class CharacterReferenceImageInline(admin.TabularInline):
    model = CharacterReferenceImage
    extra = 1


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ['name', 'voice']
    inlines = [CharacterReferenceImageInline]

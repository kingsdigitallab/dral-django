from django.contrib import admin
from dral_text.models import Text, Chapter


@admin.register(Text)
class TextAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'is_public', 'pointer',
                    'language',
                    'original_publication_year')
    list_editable = ('is_public', 'pointer', 'language',
                     'original_publication_year')
    list_display_links = ('id', 'code')


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'display_order')
    list_editable = ('name', 'display_order')
    list_display_links = ('id', 'slug')

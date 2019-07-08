from django.contrib import admin
from dral_text.models import Text


@admin.register(Text)
class TextAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'is_public', 'pointer',
                    'language',
                    'original_publication_year')
    list_editable = ('is_public', 'pointer', 'language',
                     'original_publication_year')
    list_display_links = ('id', 'code')

from django.contrib import admin
from dral_text.models import Text


@admin.register(Text)
class TextAdmin(admin.ModelAdmin):
    list_display = ('id', 'is_public', 'code', 'pointer',
                    'original_publication_date')
    list_display_links = list_display

from wagtail.contrib.modeladmin.options import (
    ModelAdmin, modeladmin_register)
from .models import Text, Chapter, Visualisation


class TextAdmin(ModelAdmin):
    model = Text
    menu_label = 'Texts'
    menu_icon = 'pilcrow'
    menu_order = 200  # will put in 3rd place (000 being 1st, 100 2nd)
    add_to_settings_menu = False  #
    # or True to exclude pages of this type from Wagtail's explorer view
    exclude_from_explorer = False
    list_display = ('id', 'code', 'is_public', 'pointer',
                    'language',
                    'original_publication_year')
    list_filter = ('is_public',)
    search_fields = ('reference', 'authors', 'code',
                     'pointer', 'original_publication_year')


modeladmin_register(TextAdmin)


class ChapterAdmin(ModelAdmin):
    model = Chapter
    menu_label = 'Chapters'
    menu_icon = 'pilcrow'
    menu_order = 210  # will put in 3rd place (000 being 1st, 100 2nd)
    add_to_settings_menu = False  #
    # or True to exclude pages of this type from Wagtail's explorer view
    exclude_from_explorer = False
    list_display = ('id', 'name', 'slug', 'display_order')
    list_filter = ()


modeladmin_register(ChapterAdmin)


class VisualisationAdmin(ModelAdmin):
    model = Visualisation
    menu_label = 'Visualisations'
    menu_icon = 'pilcrow'
    menu_order = 220  # will put in 3rd place (000 being 1st, 100 2nd)
    add_to_settings_menu = False  #
    # or True to exclude pages of this type from Wagtail's explorer view
    exclude_from_explorer = False
    list_display = ('id', 'name', 'type', 'display_order', 'visibility')
    list_filter = ()


modeladmin_register(VisualisationAdmin)

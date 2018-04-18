# from django.db import models
from wagtail.core.fields import RichTextField
from django.db.models.fields import CharField
from wagtail.core.models import Page
from wagtail.admin.edit_handlers import FieldPanel, MultiFieldPanel
from wagtail.search import index

# ===================================================================
#                            STATIC PAGES
# ===================================================================


class RichPage(Page):
    '''
    The base class for all other pages
    '''

    class Meta:
        abstract = True

    is_creatable = False

    body = RichTextField(blank=True)

    short_title = CharField(
        'Menu label',
        max_length=32,
        blank=True,
        null=True,
        default=None,
        help_text='A very short label used to represent this page in a menu'
    )

    content_panels = Page.content_panels + [
        FieldPanel('body', classname="full"),
    ]

    promote_panels = Page.promote_panels + [
        MultiFieldPanel([
            FieldPanel('short_title')
        ],
            heading='Presentation',
            classname='collapsible'
        ),
    ]

    def body_highlightable(self):
        from django.utils.html import strip_tags
        return strip_tags((self.body or ''))

    search_fields = Page.search_fields + [
        # we don't index body directly, Elasticsearch isn't XML aware
        # e.g. search 'strong' returns pages with <strong> and highlighting
        # tags generate invalid XML e.g. <<hl>strong</hl>>
        index.SearchField('body_highlightable'),
        # index.FilterField('date'),
    ]

    def get_shortest_title(self):
        return self.short_title or self.title


class HomePage(RichPage):
    pass


class StaticPage(RichPage):
    pass


class VisualisationSetPage(RichPage):
    pass


class VisualisationPage(RichPage):
    pass

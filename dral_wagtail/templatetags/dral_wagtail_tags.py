from django import template
from wagtail.core.models import Site
# from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag(takes_context=True)
def get_site_root(context):
    # NB this returns a core.Page, not the implementation-specific model used
    # so object-comparison to self will return false as objects would differ
    ret = None

    site = getattr(context['request'], 'site', None)
    if not site:
        # no reference, let's get ANY site
        site = Site.objects.first()

    if site:
        ret = site.root_page

    return ret
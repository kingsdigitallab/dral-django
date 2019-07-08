# -*- coding: utf-8 -*-
# Generated by Django 2.0 on 2018-04-18 18:06
from __future__ import unicode_literals

from django.db import migrations
from wagtail.core.models import Site


def load_json_content(apps, schema_editor):
    from django.core import management

    if 0:
        # remove all existing content types to avoid duplicate keys
        ContentType = apps.get_model("contenttypes", "ContentType")
        for ct in ContentType.objects.all():
            ct.delete()

        Site = apps.get_model("wagtailcore", "Site")
        for site in Site.objects.all():
            site.delete()

        management.call_command(
            'loaddata',
            'basic_site.json',
            verbosity=0
        )


class Migration(migrations.Migration):

    dependencies = [
        ('dral_wagtail', '0002_visualisationsetpage'),
        ('sessions', '0001_initial'),
        ('wagtaildocs', '0007_merge'),
        ('wagtailusers', '0006_userprofile_prefered_language'),
        ('wagtailadmin', '0001_create_admin_access_permissions'),
        ('wagtailembeds', '0003_capitalizeverbose'),
        ('wagtailsearch', '0003_remove_editors_pick'),
        ('wagtailredirects', '0005_capitalizeverbose'),
        ('wagtailimages', '0019_delete_filter'),
    ]

    operations = [
        migrations.RunPython(load_json_content),
    ]

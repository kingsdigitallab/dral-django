# Generated by Django 2.1.5 on 2019-06-12 23:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dral_text', '0025_auto_20190613_0047'),
    ]

    operations = [
        migrations.RenameField(
            model_name='text',
            old_name='name',
            new_name='code',
        ),
    ]
# Generated by Django 2.1.5 on 2019-02-11 18:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dral_text', '0019_chapter_display_order'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sheetstyle',
            name='color',
            field=models.CharField(default='', max_length=15),
        ),
    ]
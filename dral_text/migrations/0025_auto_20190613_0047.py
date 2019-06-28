# Generated by Django 2.1.5 on 2019-06-12 23:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dral_text', '0024_auto_20190612_2007'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='text',
            name='slug',
        ),
        migrations.AddField(
            model_name='text',
            name='authors',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='text',
            name='internal_note',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='text',
            name='language',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='text',
            name='original_publication_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='text',
            name='pointer',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='text',
            name='production_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='text',
            name='public_note',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='text',
            name='reference',
            field=models.CharField(blank=True, max_length=300, null=True),
        ),
        migrations.AlterField(
            model_name='text',
            name='name',
            field=models.SlugField(max_length=20, unique=True),
        ),
    ]
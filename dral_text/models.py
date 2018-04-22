from django.db import models

'''
TODO: add chapters

lemma
    string
    language

occurrence
    word
    context
    sentence_index
    language_id
    lemma_group=color
    lemma_id

sentence
    index
    string

language
    name

OR

|| lemma
    || sentence
        || language
            word
'''


class Lemma(models.Model):
    string = models.CharField(max_length=20, unique=True)
    language = models.ForeignKey('Language', on_delete=models.PROTECT)


class Occurence(models.Model):
    # FIELDS IMPORTED STRAIGHT FROM THE SPREADSHEET
    cell = models.CharField(max_length=80, blank=True)
    cell_style = models.CharField(max_length=10, blank=True)
    cell_line = models.IntegerField(default=0)
    cell_col = models.IntegerField(default=0)
    freq = models.IntegerField(default=0)
    lemma = models.ForeignKey(
        'Lemma',
        null=True,
        blank=True,
        default=None,
        on_delete=models.PROTECT)

    # DERIVED/INTERPRETED FROM THE ABOVE FIELDS
    string = models.CharField(max_length=20, null=True, blank=True)
    sentence_index = models.IntegerField()
    context = models.CharField(max_length=50, blank=True)
    replace = models.BooleanField(default=False)
    zero = models.BooleanField(default=False)
    paraphrase = models.BooleanField(default=False)
    language = models.ForeignKey('Language', on_delete=models.PROTECT)
    chapter = models.CharField(max_length=10, blank=True)
    lemma_group = models.IntegerField()


class SheetStyle(models.Model):
    name = models.CharField(max_length=10)
    color = models.CharField(max_length=15)
    chapter = models.CharField(max_length=10, blank=True)


class Sentence(models.Model):
    string = models.CharField(max_length=500)
    index = models.IntegerField()
    language = models.ForeignKey('Language', on_delete=models.PROTECT)
    chapter = models.CharField(max_length=10, blank=True)


class Language(models.Model):
    name = models.CharField(max_length=20, unique=True)

    @classmethod
    def add_default_languages(cls):
        for name in ['EN', 'LT', 'POL', 'RU']:
            obj, _ = cls.objects.get_or_create(name=name)

    @classmethod
    def get_languages(cls):
        return {o.name: o for o in cls.objects.all()}

from django.db import models

'''
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
    string = models.CharField(max_length=20)
    sentence_index = models.IntegerField()
    context = models.CharField(max_length=30, blank=True)
    language = models.ForeignKey('Language', on_delete=models.PROTECT)
    lemma = models.ForeignKey(
        'Lemma',
        null=True,
        blank=True,
        default=None,
        on_delete=models.PROTECT)
    lemma_group = models.IntegerField()


class Sentence(models.Model):
    string = models.CharField(max_length=500)
    index = models.IntegerField()
    language = models.ForeignKey('Language', on_delete=models.PROTECT)


class Language(models.Model):
    name = models.CharField(max_length=20, unique=True)

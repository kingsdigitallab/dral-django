from django.db import models
import re

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
    '''Represents a lemma in English'''
    string = models.CharField(max_length=20)
    '''Comma separated list of forms'''
    forms = models.CharField(max_length=200, blank=True)
    '''This will be EN'''
    language = models.ForeignKey('Language', on_delete=models.PROTECT)

    class Meta:
        unique_together = [['string', 'forms']]


class Chapter(models.Model):
    slug = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=60)
    display_order = models.IntegerField(default=0, blank=False, null=False)

    def __str__(self):
        return '{}'.format(self.name)

    @classmethod
    def update_or_create_from_table_name(self, table_name):
        '''
        e.g. update_or_create_from_table_name('Chapter Two #2')

        creates or update a Chapter with the following values:

        .slug = 'chapter-two'
        .name = 'Chapter Two'
        .display_order = 2

        If the chapter with that slug already exists, data will be updated.
        '''

        ret = None

        from django.utils.text import slugify

        # parse table_name
        data = {}
        data['name'] = table_name.strip()
        data['name'], data['display_order'] = re.findall(
            r'^(.*?)[\s_]*(?:#(\d+))?$', data['name']
        )[0]
        data['display_order'] = int(data['display_order'] or 0)
        data['slug'] = slugify(data['name'])

        ret, _ = Chapter.objects.update_or_create(
            slug=data['slug'],
            defaults=data
        )

        return ret


class Occurence(models.Model):
    '''An particular occurrence of a word in sentence of a text.
    This comes from the spreadsheet, so the first set of fields
    represents metadata about the spreadsheet cell.
    '''
    # FIELDS IMPORTED STRAIGHT FROM THE SPREADSHEET

    # the text content of the cell
    cell = models.CharField(max_length=200, blank=True)
    # the style code (-> SheetStyle.name)
    cell_style = models.CharField(max_length=10, blank=True)
    # row
    cell_line = models.IntegerField(default=0)
    # column
    cell_col = models.IntegerField(default=0)
    # max number of occurrences for that lemma
    freq = models.IntegerField(default=0)
    # link to the English lemma
    lemma = models.ForeignKey(
        'Lemma',
        null=True,
        blank=True,
        default=None,
        on_delete=models.PROTECT)
    # chapter code (e.g. BENJY)
    chapter = models.ForeignKey(
        'Chapter',
        null=True,
        blank=True,
        default=None,
        on_delete=models.PROTECT
    )

    # language of the word
    language = models.ForeignKey('Language', on_delete=models.PROTECT)

    # DERIVED/INTERPRETED FROM THE ABOVE FIELDS

    # occurrence of the word in the text, without context
    string = models.CharField(max_length=20, null=True, blank=True)
    # the index of the sentence the word occurs
    sentence_index = models.IntegerField()
    # the context (surrounding words)
    context = models.CharField(max_length=50, blank=True)
    # translation replaced that word?
    replace = models.BooleanField(default=False)
    # omitted?
    zero = models.BooleanField(default=False)
    # paraphrased?
    paraphrase = models.BooleanField(default=False)
    # an arbitrary index representing the lemma the word belongs to
    # it is the lemma in the language of the text (i.e. different from .lemma)
    lemma_group = models.IntegerField()

    def update_derived_fields(self):
        '''Set derived field from spreadsheet fields (see above)'''
        pass

    class Meta:
        unique_together = [['chapter', 'lemma', 'cell_col', 'language']]


class SheetStyle(models.Model):
    '''A style in a sheet'''
    name = models.CharField(max_length=10)
    # e.g. #ffff00, transparent
    color = models.CharField(max_length=15, default='')
    # chapter code (e.g. BENJY)
    chapter = models.ForeignKey(
        'Chapter',
        null=True,
        blank=True,
        default=None,
        on_delete=models.PROTECT
    )


class Sentence(models.Model):
    string = models.CharField(max_length=500)
    index = models.IntegerField()
    #
    language = models.ForeignKey('Language', on_delete=models.PROTECT)
    chapter = models.CharField(max_length=10, blank=True)
    cell_line = models.IntegerField(default=0, blank=True)
    cell = models.CharField(max_length=500, blank=True)


class Language(models.Model):
    name = models.CharField(max_length=20, unique=True)

    @classmethod
    def add_default_languages(cls):
        for name in ['EN', 'LT', 'POL', 'RU']:
            obj, _ = cls.objects.get_or_create(name=name)

    @classmethod
    def get_languages(cls):
        return {o.name: o for o in cls.objects.all()}

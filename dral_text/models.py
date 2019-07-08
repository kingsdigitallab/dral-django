from django.db import models
import re

'''
lemma
    string
    text

occurrence
    word
    context
    sentence_index
    text_id
    lemma_group=color
    lemma_id

sentence
    index
    string

text
    name

OR

|| lemma
    || sentence
        || text
            word
'''
from django.utils.text import slugify


class Lemma(models.Model):
    '''Represents a lemma in English'''
    string = models.CharField(max_length=20)
    '''Comma separated list of forms'''
    forms = models.CharField(max_length=200, blank=True)
    '''This will be EN'''
    text = models.ForeignKey('Text', on_delete=models.PROTECT)

    class Meta:
        unique_together = [['string', 'forms']]


class Chapter(models.Model):
    slug = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=60)
    display_order = models.IntegerField(default=0, blank=False, null=False)

    class Meta:
        ordering = ['display_order']

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

        If the chapter order is missing it won't be changed in the database.
        '''

        ret = None

        from django.utils.text import slugify

        # parse table_name
        data = {}
        data['name'] = table_name.strip()
        data['name'], display_order = re.findall(
            r'^(.*?)[\s_]*(?:#(\d+))?$', data['name']
        )[0]
        display_order = int(display_order or 0)
        if display_order:
            data['display_order'] = display_order

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

    # text of the word
    text = models.ForeignKey('Text', on_delete=models.PROTECT)

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
        unique_together = [['chapter', 'lemma', 'cell_col', 'text']]


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
    text = models.ForeignKey(
        'Text', on_delete=models.PROTECT, related_name='sentences')
    chapter = models.ForeignKey(
        'Chapter',
        null=True,
        blank=True,
        default=None,
        on_delete=models.PROTECT
    )
    cell_line = models.IntegerField(default=0, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['index']),
            models.Index(fields=['chapter']),
            models.Index(fields=['text']),
        ]


class Text(models.Model):
    # e.g. RU2
    code = models.SlugField(max_length=20, null=False, unique=True)
    # e.g. RU2001
    pointer = models.CharField(max_length=20, null=True, blank=True)
    # Faulkner, W. (1990) The Sound and the Fury. New York: Vintage Books.
    reference = models.CharField(max_length=300, null=True, blank=True)
    original_publication_year = models.IntegerField(null=True, blank=True)
    production_year = models.IntegerField(null=True, blank=True)
    # comma separated values: surname, initials
    authors = models.CharField(max_length=200, null=True, blank=True)
    # Russian
    language = models.CharField(max_length=20, null=True, blank=True)
    public_note = models.TextField(null=True, blank=True)
    internal_note = models.TextField(null=True, blank=True)
    is_public = models.BooleanField(null=False, default=False)

    @classmethod
    def add_default_texts(cls):
        # for code in ['en', 'lt', 'pol', 'ru']:
        for code in ['en']:
            cls.objects.get_or_create(code=code)

    def __str__(self):
        return self.reference or self.get_label()

    @classmethod
    def get_texts(cls):
        return {o.code: o for o in cls.objects.all()}

    def get_label(self):
        ret = None

        if self.language:
            ret = self.language
            if self.original_publication_year:
                ret += ' ({})'.format(self.original_publication_year)
        if not ret:
            if self.pointer:
                ret = self.pointer
        if not ret:
            ret = self.code.upper()

        return ret

    @classmethod
    def get_all(cls):
        '''Returns all text instances as a list.
        In alphabetical order of the code
        But english is at the end
        because it allows us to delete all other referring
        records first.
        '''
        ret = list(cls.objects.all())

        ret = sorted(ret, key=lambda t: (t.code.lower() == 'en', t.code))

        return ret

    @classmethod
    def get_or_create_from_code(cls, code):
        slug = slugify(code)
        ret, _ = cls.objects.get_or_create(
            code=slug,
            # defaults={
            #     'name': name
            # }
        )

        return ret

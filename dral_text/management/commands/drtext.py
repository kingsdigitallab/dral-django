'''
Created on 19 April 2018

@author: Geoffroy Noel
'''

from dral_wagtail.management.commands._kdlcommand import KDLCommand
import xml.etree.ElementTree as ET
import re
import os
from dral_text.models import (
    Language, Lemma, Occurence, Sentence, SheetStyle, Chapter
)
from collections import OrderedDict

MAX_CELL_PER_ROW = 2000
MAX_CELL_LENGTH = 200


class Command(KDLCommand):
    help = '''
DRaL research data management toolbox

Usage: ACTION [OPTIONS]

ACTIONS:

import PATH_TO_CONTENT.XML
    import occurence data from a spreadsheet into the relational DB
    PATH_TO_CONTENT.XML: is a content.xml obtained by unzipping a .ods file
    The .ods file is a spreadsheet saved with LibreOffice Calc.
    e.g. ./manage.py drtext import research_data/private/benjy/content.xml

clean
    compute occurence fields derived from occurence data imported from
    spreadsheet research_data/private/spreadsheets/S_F_alligned_ru.ods

clear
    remove all the occurence data from the database

import_sentences PATH_TO_CONTENT.XML
    import_sentences

    ce52 is yellow
    '''

    def action_clear(self):
        for model in [Occurence, Sentence, Lemma, SheetStyle]:
            model.objects.all().delete()

    def action_import(self):
        Language.add_default_languages()
        self.languages = Language.get_languages()
        from django.conf import settings
        self.DRAL_REFERENCE_LANGUAGE = settings.DRAL_REFERENCE_LANGUAGE

        file_path = self.aargs.pop()

        root = self.get_element_tree_from_file(file_path)

        if root is not None:
            for table in root.findall(".//table"):
                self.import_table(table, root)
                # break
        else:
            self.show_message(
                'File "{}" is empty or not found.'.format(file_path),
                0,
                'ERROR'
            )

    def _init_import_table(self, chapter):
        '''
        Initialise the import statistics.
        Read and cache all occurrences and Lemmas from DB to speed up
        the import of a table.
        '''

        self.first_block_line_types = None

        self.stats = {
            'cells.created': 0,
            'cells.updated': 0,
            'cells.deleted': 0,
            'lemmas.created': 0,
            'lemmas.updated': 0,
        }

        self.occurences_to_create = []
        self.lemmas_to_create = []

        # read all the occurrences records for that chapter
        self.occurrences = {
            '%s:%s (%s):%s:%s' % (
                obj.chapter.slug,
                obj.lemma.string,
                obj.lemma.forms,
                obj.language_id,
                obj.cell_col
            ): obj
            for obj
            in Occurence.objects.filter(chapter=chapter)
        }

        self.lemmas = {
            '%s (%s)' % (lemma.string, lemma.forms): lemma
            for lemma
            in Lemma.objects.all()
        }

    def import_table(self, xml_table, xml_root):
        '''
        Import the spreadsheet/table rows;
        identify blocks of rows that belong to the same english lemma
        extract and import the occurrence strings and metadata
        '''
        table_name = xml_table.attrib['name']
        skipped = ''
        if (table_name.startswith('_') or
                table_name.lower().startswith('sheet')):
            skipped = ' (skipped)'
        print('> Table "%s"%s' % (table_name, skipped))
        if skipped:
            return

        self.chapter = Chapter.update_or_create_from_table_name(table_name)

        self._init_import_table(self.chapter)

        print('Importing styles...')
        self.reimport_table_styles(xml_root, self.chapter)

        # root = tree.getroot()
        # <table:table table:name="BENJY" table:style-name="ta1">

        print('Importing strings...')

        values = [None for i in range(0, MAX_CELL_PER_ROW)]

        line = 0

        block = []
        for row in self.get_rows_from_xml_table(xml_table, values):
            line += 1

            added = False
            anchor = values[4][0].strip()

            # we add each line into the block
            # if there is no value in col 3: we process this block and
            # issue a new empty one
            if anchor:
                if not values[3][0]:
                    # contains sentence numbers, we add it to the block first
                    if re.match(r'\d+', anchor):
                        added = True
                        block.append(values[:])
                    if block:
                        self.process_lemma_block(block, line - len(block))
                    block = []

            # add the line to the block
            if anchor and not added:
                block.append(values[:])

        self._post_import_table()

    def _post_import_table(self):
        '''
        Bulk creation of new occurrences in DB.
        Delete unused occurrences from DB.
        Print import stats.
        '''

        Occurence.objects.bulk_create(
            self.occurences_to_create
        )
        self.stats['cells.created'] = len(self.occurences_to_create)

        # delete occurrences that are no longer in the imported sheet
        for occurrence in self.occurrences.values():
            if not getattr(occurrence, 'keep', False):
                occurrence.delete()
                self.stats['cells.deleted'] += 1

        # remove unused lemma
        from django.db.models import Count
        Lemma.objects.annotate(
            num_occs=Count('occurence')
        ).filter(num_occs__lt=1).delete()

        # remove unused chapters
        Chapter.objects.annotate(
            num_occs=Count('occurence')
        ).filter(num_occs__lt=1).delete()

        print(
            'Cells: (C:%s U:%s D:%s); Lemmas: (C:%s U:%s)' % (
                self.stats['cells.created'],
                self.stats['cells.updated'],
                self.stats['cells.deleted'],
                self.stats['lemmas.created'],
                self.stats['lemmas.updated'],
            )
        )

    def process_lemma_block(self, block, line_number):
        '''
        Process a lemma block from the spreadsheet
        The block contains an array or rows.
        Format of each row describe in get_values_next_row()
        '''

        # print('\n'.join([l[4][0] for l in block]))

        lines = OrderedDict()

        freq = 0

        lemma = ''
        forms = ''
        for line in block:
            # line[1][0] => 1: second cell, 0: text content
            front_words = line[1][0].strip()
            if front_words:
                afreq = re.match(r'\d+', line[2][0])
                if afreq:
                    if lemma:
                        self.show_message(
                            'block has more than one lemma',
                            line_number
                        )
                    else:
                        lemma = front_words
                        freq = int(afreq.group(0))
                else:
                    if (
                        front_words.startswith('(') and
                        front_words.endswith(')')
                    ):
                        forms = front_words

            if re.match(r'\d+', line[4][0]):
                lines['locations'] = line[4:]
            elif line[3][0]:
                # string occurrences in one language
                lines[line[3][0]] = line[4:]
            elif line[4][0]:
                # string occurrences in English
                lines[self.DRAL_REFERENCE_LANGUAGE] = line[4:]

        # normalise the forms
        forms = re.sub(r'^\((.*)\)$', r'\1', forms)
        forms = ', '.join([f.strip() for f in forms.split(',')])

        if not self.first_block_line_types:
            self.first_block_line_types = lines.keys()

        differences = (
            set(lines.keys()) ^ self.first_block_line_types
        )

        if differences:
            self.show_message(
                'Different languages: ' + ','.join(differences),
                line_number
            )

        if not lemma:
            self.show_message(
                'block doesn\'t have a lemma',
                line_number
            )
        else:
            lemma_forms = '%s (%s)' % (lemma, forms)
            print('Block %s, %s' % (line_number, lemma_forms))
            lemma_obj = self.lemmas.get(lemma_forms, None)
            if not lemma_obj:
                lemma_obj = Lemma(
                    string=lemma,
                    forms=forms,
                    language=self.languages[self.DRAL_REFERENCE_LANGUAGE],
                )
                lemma_obj.save()
                self.stats['lemmas.created'] += 1
                # self.lemmas_to_create.append(lemma_obj)
            lemma = lemma_obj

            locations = lines.get('locations', None)

            median = 100000

            if locations:
                length = len(locations)
                while length and (
                    locations[length - 1] is None or
                    not re.match(r'^\s*\d+\s*$', locations[length - 1][0])
                ):
                    length -= 1
                median = length
            else:
                for line in lines.values():
                    if locations:
                        line = locations
                    length = 0
                    # stop if blank value AND no number in next cell
                    while line[length][0] or (
                        (length + 1) < len(line) and
                        re.match(r'\d+', line[length + 1][0])
                    ):
                        length += 1

                    if length < median:
                        median = length
                    if locations:
                        break

            for lg, line in lines.items():
                if lg is 'locations':
                    continue
                # todo: remove this once the error has been corrected in file
                # PL => POL
                if lg == 'PL':
                    lg = 'POL'
                styles = {}

                i = 0
                for v in line:
                    if i >= median:
                        break
                    # removed that cnd as some strings can be blank
                    # in the sequence... (benjy, come*, lt)
                    if 0 and not v[0]:
                        break

                    if v[1] not in styles:
                        styles[v[1]] = len(styles.keys())

                    options = dict(
                        cell_line=line_number,
                        cell_col=i,
                        language=self.languages[lg],
                        chapter=self.chapter
                    )

                    # occurence = Occurence.objects\
                    # .filter(**options).first()
                    occurence = self.occurrences.get(
                        '%s:%s:%s:%s' % (
                            self.chapter.slug,
                            lemma_forms,
                            options['language'].id,
                            options['cell_col']
                        ),
                        None
                    )

                    options['lemma'] = lemma
                    options['freq'] = freq

                    try:
                        options['sentence_index'] = int(
                            locations[i][0] if locations else 0
                        )
                    except ValueError:
                        options['sentence_index'] = 0

                    options['lemma_group'] = styles[v[1]]
                    if len(v[0]) > 80:
                        pass
                        # print(v[0])
                    options['cell'] = v[0][:MAX_CELL_LENGTH]
                    options['cell_style'] = v[1] or ''
                    if lg == self.DRAL_REFERENCE_LANGUAGE:
                        options['string'] = '?'
                        options['context'] = options['cell'][:50]
                    else:
                        options['string'] = options['cell'][:20]
                        if len(v[0]) > 20:
                            print(v[0])

                    if occurence:
                        occurence.keep = 1
                        has_changed = 0
                        for k in options.keys():
                            if getattr(occurence, k, None) != options[k]:
                                has_changed = 1
#                                 print(k, repr(getattr(occurence, k, None)),
#                                       repr(options[k]))
                                setattr(occurence, k, options[k])
                        if has_changed:
                            occurence.save()
                            self.stats['cells.updated'] += 1
                    else:
                        occurence = Occurence(**options)
                        self.occurences_to_create.append(occurence)
                    i += 1

    def action_import_sentences(self):
        print('Delete all sentences')
        [o.delete() for o in Sentence.objects.all()]

        self.languages = Language.get_languages()

        import os

        while self.aargs:
            ods_path = self.aargs.pop()
            file_path = '/tmp/dral_sent_content.xml'
            os.system('unzip -p %s content.xml > %s' % (ods_path, file_path))
            content = self._read_file(file_path, encoding='utf-8')

            import re
            content = re.sub(
                r'(table|office|style|text|draw|fo):', '', content
            )

            root = ET.fromstring(content)

            for table in root.findall(".//table"):
                table_name = table.attrib['name']

                match = re.match(
                    '^(BENJY|QUENTIN|JASON|DILSEY)_([A-Z]{2,3})$',
                    table_name
                )
                if not match:
                    print('WARNING: Skipped table %s' % table_name)
                    continue
                chapter, language_name = match.group(1), match.group(2)
                print(chapter, language_name)

                if language_name == 'PL':
                    language_name = 'POL'

                language = Language.objects.filter(name=language_name).first()

                if not language:
                    print(
                        'WARNING: Skipped table %s (unrecognised language %s)'
                        % (table_name, language_name)
                    )
                    continue

                # import table
                values = [None for i in range(0, MAX_CELL_PER_ROW)]

                line = 0

                for cols in self.get_values_next_row(table, values):
                    line += 1

                    if line % 2 == 0:
                        # print(line)

                        string = string = values[1][0]
                        if string is None:
                            string = ''
                        if len(string) > 500:
                            string = string[0:500]

                        index = int(values[0][0] or 0)

                        sentence = Sentence(
                            string=string,
                            language=language,
                            index=index,
                            chapter=chapter,
                            cell_line=line,
                            cell=string,
                        )
                        sentence.save()

    def action_clean(self):
        import difflib
        self.languages = Language.get_languages()

        # todo: move this to the model
        # todo: call it during import
        if 1:
            c = 0
            for occurence in Occurence.objects.filter(
                language__name=self.DRAL_REFERENCE_LANGUAGE
            ).select_related('lemma'):
                lemmas = occurence.lemma.string.lower()
                lemmas = lemmas.replace('*', '').split('/')

                best_score = 0
                v = ''

                cell = occurence.cell.lower()
                cell = re.sub(r'\W', ' ', cell)

                for word in cell.split(' '):
                    for lemma in lemmas:
                        s = difflib.SequenceMatcher(None, lemma, word)
                        ratio = s.ratio()
                        # print(word, lemma, ratio)
                        if ratio > best_score:
                            best_score = ratio
                            v = word

                if not v:
                    v = None
                else:
                    v = v[:20]
                if occurence.string != v:
                    occurence.string = v
                    occurence.save()

                # print(occurence.cell, '=>', v)

                c += 1
                if 0 and c > 300:
                    exit()

        for occurence in Occurence.objects.exclude(
                language__name=self.DRAL_REFERENCE_LANGUAGE):
            v = occurence.cell.lower()

            # categories
            v0 = v
            v = re.sub(r'\bzerr?o\b', '', v)
            occurence.zero = v0 != v
            v0 = v
            v = re.sub(r'\b(replace|replacement)\b', '', v)
            occurence.replace = v0 != v
            v0 = v
            v = re.sub(r'\b(paraphrase|paraphrasing)\b', '', v)
            occurence.paraphrase = v0 != v

            # remove '/'
            v = v.replace('/', ' ')

            # remove parentheses
            v = re.sub(r'\s*\([^\)]*\)\s*', '', v)

            # reduce double spaces
            v = re.sub(r'\s+', ' ', v.strip())

            if not v:
                v = None
            else:
                v = v[:20]
            if 0 and v and re.search(r'\W', v):
                self.show_message(v, 0)

            occurence.string = v

            occurence.save()

    def show_message(self, message, line_number, status='WARNING'):
        print('{}: line {}, {}'.format(status, line_number, message))
        if status == 'ERROR':
            exit()

    def get_rows_from_xml_table(self, xml_table, values):
        '''
        Yield the column count for each row in <table>.
        And update <values> with array of pairs.
        One pair for each cell.
        pair = (textual_content, style)
        '''
        for row in xml_table.findall('table-row'):
            col = 0
            for cell in row.findall('table-cell'):
                # number-columns-repeated="2" table:style-name="ce2"
                repeated = cell.attrib.get('number-columns-repeated', 1)
                value = self.get_value_from_cell(cell)
                style = cell.attrib.get('style-name', None)
                for i in range(1, int(repeated) + 1):
                    if col >= len(values):
                        break
                    values[col] = [
                        value.strip(),
                        style
                    ]
                    col += 1
            row_repeated = int(row.attrib.get('number-rows-repeated', 1))
            for i in range(1, min(row_repeated, 2) + 1):
                yield col

    def get_value_from_cell(self, cell):
        ret = ''

        para = cell.findall('p')
        if para:
            ret = self.get_text_from_element(para[0])

        return ret

    def get_text_from_element(self, element):
        '''
        Returns plain text content of the element
        (and sub-elements)
        '''
        ret = element.text or ''
        for child in element:
            if child.tag == 's':
                ret += ' '
            elif child.tag == 'span':
                ret += self.get_text_from_element(child)
            else:
                if 0:
                    raise Exception(
                        'Unknown element in <cell><p> {}'.format(
                            child.tag))
            ret += child.tail or ''

        return ret.strip()

    def get_element_tree_from_file(self, file_path):
        '''
        Returns the root of an ElementTree object loaded with the content
        of the given file at file_path.
        The file can be an .ods file or its constituent content.xml file.
        '''
        if not os.path.exists(file_path):
            return None

        if file_path.endswith('.ods'):
            from zipfile import ZipFile
            content = ZipFile(file_path).read(name='content.xml')
            content = content.decode('utf-8')
        elif file_path.endswith('.xml'):
            content = self._read_file(file_path, encoding='utf-8')
        else:
            self.print_error(
                'Unsupported file extension, only accept .xml or .ods.'
            )
            exit()

        import re
        content = re.sub(r'(table|office|style|text|draw|fo):', '', content)

        return ET.fromstring(content)

    def reimport_table_styles(self, xml_root, chapter):
        root = xml_root

        # Todo: update instead of removing each time
        SheetStyle.objects.filter(chapter=self.chapter).delete()

        for style in root.findall(".//style"):
            name = style.attrib['name']
            properties = style.find('table-cell-properties')
            color = '?'
            if properties is not None:
                color = properties.attrib.get('background-color', color)
            style, _ = SheetStyle.objects.get_or_create(
                name=name, chapter=self.chapter)
            style.color = color
            style.save()

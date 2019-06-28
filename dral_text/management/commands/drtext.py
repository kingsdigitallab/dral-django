'''
Created on 19 April 2018

@author: Geoffroy Noel
'''

from dral_wagtail.management.commands._kdlcommand import KDLCommand
import xml.etree.ElementTree as ET
import re
import os
from dral_text.models import (
    Lemma, Occurence, Sentence, SheetStyle, Chapter, Text
)
from collections import OrderedDict
from django.utils.text import slugify

MAX_CELL_PER_ROW = 2000
MAX_CELL_LENGTH = 200
MAX_STTRING_LENGTH = 20


class DRTEXTException(Exception):
    pass


class Command(KDLCommand):
    help = '''
DRaL research data management toolbox

Usage: ACTION [OPTIONS]

ACTIONS:

import PATH_TO_FILE.ODS
    import occurrence data from a spreadsheet into the relational DB
    PATH_TO_CONTENT.XML: is a content.xml obtained by unzipping a .ods file
    The .ods file is a spreadsheet saved with LibreOffice Calc.
    e.g. ./manage.py drtext import research_data/private/benjy/content.xml

clean
    compute occurrence fields derived from occurrence data imported from
    spreadsheet research_data/private/spreadsheets/S_F_alligned_ru.ods

clear
    remove all the occurrence data from the database

import_sentences PATH_TO_FILE.ODS
    import sentences

import_texts PATH_TO_FILE.ODS
    import text metadata

    (ce52 is yellow)
    '''

    # =============================================================
    # MAIN ACTIONS from command line

    def action_clean(self):
        self._pre_action()
        self._action_clean()

    def action_clear(self):
        self._pre_action()
        for model in [Occurence, Sentence, Lemma, SheetStyle, Chapter]:
            model.objects.all().delete()

    def action_import(self):
        def import_table_handler(table, root):
            return self.import_table_occurrences(table, root)

        self.import_sheets_from_file_arg(import_table_handler)

    def action_import_sentences(self):
        def import_table_handler(table, root):
            return self.import_table_sentences(table, root)

        self.import_sheets_from_file_arg(import_table_handler)

    def action_import_texts(self):
        def import_table_handler(table, root):
            return self.import_table_texts(table, root)

        self.import_sheets_from_file_arg(import_table_handler)

    # =============================================================
    # ACTIONS from other python modules

    def import_occurrences_from_file(self, file_path):
        def import_table_handler(table, root):
            return self.import_table_occurrences(table, root)

        self.import_sheets_from_file(file_path, import_table_handler)

    def import_sentences_from_file(self, file_path):
        def import_table_handler(table, root):
            return self.import_table_sentences(table, root)

        self.import_sheets_from_file(file_path, import_table_handler)

    def import_texts_from_file(self, file_path):
        def import_table_handler(table, root):
            return self.import_table_texts(table, root)

        self.import_sheets_from_file(file_path, import_table_handler)

    # =============================================================
    # OCCURENCES

    def _init_import_table_occurrences(self, chapter):
        '''
        Initialise the import statistics.
        Read and cache all occurrences and Lemmas from DB to speed up
        the import of a table.
        '''

        self.previous_block_line_types = None

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
                obj.text_id,
                obj.cell_col
            ): obj
            for obj
            in Occurence.objects.filter(chapter=chapter).select_related(
                'lemma', 'chapter'
            )
        }

        self.lemmas = {
            '%s (%s)' % (lemma.string, lemma.forms): lemma
            for lemma
            in Lemma.objects.all()
        }

    def import_table_occurrences(self, xml_table, xml_root):
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
        self.msg('> Table "%s"%s' % (table_name, skipped))
        if skipped:
            return

        self.chapter = Chapter.update_or_create_from_table_name(table_name)

        self._init_import_table_occurrences(self.chapter)

        self.msg('Importing styles...')
        self.reimport_table_styles(xml_root, self.chapter)

        # root = tree.getroot()
        # <table:table table:name="BENJY" table:style-name="ta1">

        self.msg('Importing strings...')

        values = [None for i in range(0, MAX_CELL_PER_ROW)]

        line = 0

        # process each row one at a time and group them into lemma blocks
        block = []
        for row_len in self.get_rows_from_xml_table(xml_table, values):
            line += 1

            added = False
            anchor = values[4][0]

            # we add each line into the block
            # if there is no value in col 3: we process this block and
            # issue a new empty one
            if anchor:
                if not values[3][0]:
                    # contains sentence numbers, we add it to the block first
                    if re.match(r'\d+', anchor):
                        added = True
                        block.append(values[:row_len])
                    if block:
                        self.process_lemma_block(block, line - len(block) + 1)
                    block = []

            # add the line to the block
            if anchor and not added:
                block.append(values[:row_len])

        self._post_import_table_occurrences()

    def _post_import_table_occurrences(self):
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
            num_occs=Count('occurence'), num_sentences=Count('sentence')
        ).filter(num_occs__lt=1, num_sentences__lt=1).delete()

        self.msg(
            'Cells: (C:%s U:%s D:%s); Keywords: (C:%s U:%s)' % (
                self.stats['cells.created'],
                self.stats['cells.updated'],
                self.stats['cells.deleted'],
                self.stats['lemmas.created'],
                self.stats['lemmas.updated'],
            )
        )

    def _get_lines_from_lemma_block(self, block, line_number):
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
                        self.warn(
                            'block has more than one keyword',
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
                lines[self.DRAL_REFERENCE_CODE] = line[4:]

        # normalise the forms
        forms = re.sub(r'^\((.*)\)$', r'\1', forms)
        forms = ', '.join([f.strip() for f in forms.split(',')])

        if self.previous_block_line_types:
            differences = (
                set(lines.keys()) ^ self.previous_block_line_types
            )

            if differences:
                self.warn(
                    'Block with mising or unexpected row: ' +
                    ','.join(differences),
                    line_number
                )

        # report discrepancies in line lengths within a block
        line_lens = [len(line) for line in lines.values()]
        min_line_len = min(line_lens)
        if sum(line_lens) != (len(lines) * min_line_len):
            self.warn(
                'Block with variation in row lengths: {}'.format(
                    ', '.join([
                        '{}: {} cols'.format(lg, len(line))
                        for lg, line
                        in lines.items()
                    ])
                ),
                line_number
            )

        self.previous_block_line_types = lines.keys()

        return lines, lemma, forms, freq, min_line_len

    def process_lemma_block(self, block, line_number):
        '''
        Process a lemma block from the spreadsheet
        The block contains an array or rows.
        Format of each row describe in get_values_next_row()

        string:
            ?: for empty cell
            ??: for EN cell that doesn't contain a form
        '''

        lines, lemma, forms, freq, min_line_len =\
            self._get_lines_from_lemma_block(
                block, line_number
            )

        # lemma record
        if not lemma:
            return self.warn('block doesn\'t have a keyword', line_number)

        if not forms:
            return self.warn('block doesn\'t have forms', line_number)

        if len(lemma) > 20:
            self.warn('keyword is longer than 20 characters', line_number)

        lemma_forms = '%s (%s)' % (lemma, forms)
        self.msg('Keyword block %s' % lemma_forms, line_number)
        lemma_obj = self.lemmas.get(lemma_forms, None)
        if not lemma_obj:
            lemma_obj = Lemma(
                string=lemma[:20],
                forms=forms,
                text=self.texts[self.DRAL_REFERENCE_CODE],
            )
            lemma_obj.save()
            self.stats['lemmas.created'] += 1
            # self.lemmas_to_create.append(lemma_obj)
        lemma = lemma_obj

        # forms as a list
        forms_list = [
            re.sub(r'[() ]', '', f).lower()
            for f in forms.split(',')
        ]
        forms_list = sorted(forms_list, key=lambda f: -len(f))

        locations = lines.get('locations', None)

        line_offset = 0
        for code, line in lines.items():
            line_offset += 0
            if code is 'locations':
                continue
            # todo: remove this once the error has been corrected in file
            # PL => POL
            code = code.strip().upper()
            if code == 'PL':
                code = 'POL'

            if code not in self.texts:
                self.texts[code] = Text.get_or_create_from_code(code)

            styles = {}

            for i, v in enumerate(line):
                if i >= min_line_len:
                    break

                if v[1] not in styles:
                    styles[v[1]] = len(styles.keys())

                is_ref_lang = (code == self.DRAL_REFERENCE_CODE)

                occurence_data = dict(
                    cell_line=line_number + line_offset,
                    cell_col=i,
                    cell=v[0][:MAX_CELL_LENGTH],
                    cell_style=v[1] or '',
                    text=self.texts[code],
                    chapter=self.chapter,
                    lemma=lemma,
                    lemma_group=styles[v[1]],
                    freq=freq,
                    sentence_index=self._get_int(
                        locations[i][0], 0) if locations else 0,
                    string=v[0][:20] if is_ref_lang else '?',
                    context=v[0][:50] if is_ref_lang else '',
                )

                self.import_cell(occurence_data, lemma_forms, forms_list)

    def import_cell(self, occurence_data, lemma_forms, forms_list):

        self._clean_occurrence_data(occurence_data, forms_list)

        occurence = self.occurrences.get(
            '%s:%s:%s:%s' % (
                occurence_data['chapter'].slug,
                lemma_forms,
                occurence_data['text'].id,
                occurence_data['cell_col']
            ),
            None
        )

        if occurence:
            occurence.keep = 1
            has_changed = 0
            for k in occurence_data.keys():
                if getattr(occurence, k, None) != occurence_data[k]:
                    has_changed = 1
                    setattr(occurence, k, occurence_data[k])
            if has_changed:
                occurence.save()
                self.stats['cells.updated'] += 1
        else:
            occurence = Occurence(**occurence_data)
            self.occurences_to_create.append(occurence)

    def _clean_occurrence_data(self, data, forms_list):
        # todo: move this to the model

        cell = data['cell']
        v = cell.lower()

        # categories
        v0 = v
        v = re.sub(r'\bzerr?o\b', '', v)
        data['zero'] = v0 != v

        if data['text'].code.lower() == self.DRAL_REFERENCE_CODE.lower():
            if v and not data['zero']:
                # string = first used form in the cell
                form_found = None
                for form in forms_list:
                    if form in v:
                        form_found = form
                        break

                if form_found is None:
                    v = '??'

                if 0 and v == '??':
                    print('?? ', cell, forms_list)

        else:
            v0 = v
            v = re.sub(r'\b(replace|replacement)\b', '', v)
            data['replace'] = v0 != v
            v0 = v
            v = re.sub(r'\b(paraphrase|paraphrasing)\b', '', v)
            data['paraphrase'] = v0 != v

            # remove '/'
            v = v.replace('/', ' ')

            # remove parentheses
            v = re.sub(r'\s*\([^\)]*\)\s*', '', v)

        # reduce double spaces
        v = re.sub(r'\s+', ' ', v.strip())

        if 0 and v and re.search(r'\W', v):
            self.warn(v, 0)

        if v:
            v = v[:MAX_STTRING_LENGTH]
        else:
            v = None

        data['string'] = v

    # ===============================================================
    # TEXT METADATA

    def import_table_texts(self, xml_table, xml_root):
        table_name = xml_table.attrib['name'].rstrip('_').strip(' ')
        skipped = ''
        if (table_name.startswith('_')):
            skipped = ' (skipped)'
        self.msg('> Table "%s"%s' % (table_name, skipped))
        if skipped:
            return

        imported_count = 0

        def get_int_from_str(st, default=None):
            ret = None
            try:
                ret = int(st)
            except ValueError:
                pass
            return ret

        values = [None] * MAX_CELL_PER_ROW
        headings = []
        for row_len in self.get_rows_from_xml_table(xml_table, values):
            if row_len < 1:
                continue
            # normalise the row in a short list of strings
            vals = [
                (v[0] if v is not None else '').strip()
                for v
                in values[:row_len]
            ]
            #
            if not headings:
                # parse heading
                headings = [slugify(v) for v in vals]
                if 'code' not in headings:
                    headings = []
            else:
                # parse a row with meta about a text
                # convert the row to a dictionary
                meta = {
                    h: (vals[i] if i < len(vals) else '')
                    for i, h
                    in enumerate(headings)
                }

                # find the corresponding text record
                text = None
                if meta['code']:
                    text = Text.get_or_create_from_code(meta['code'])

                if text:
                    # update the record
                    text.pointer = meta['display-code']
                    text.reference = meta['edition-used']
                    text.original_publication_year = get_int_from_str(
                        meta['date-of-original-publication'])
                    text.production_year = get_int_from_str(
                        meta['date-of-production'])
                    text.authors = meta['authors']
                    text.language = meta['language']
                    text.internal_note = meta['note']

                    self.msg(' Import meta for "{}"'.format(text.code))

                    imported_count += 1

                    text.save()

        self.msg(' Imported {} rows'.format(imported_count))

        # print(values[0], len(vals), row_len)

    # ===============================================================
    # SENTENCES

    def import_table_sentences(self, xml_table, xml_root):
        '''
        (Re)Import the sentences from a spreadsheet;
        '''
        table_name = xml_table.attrib['name'].rstrip('_').strip(' ')
        skipped = ''
        if (table_name.startswith('_') or
                table_name.lower().startswith('sheet')):
            skipped = ' (skipped)'
        self.msg('> Table "%s"%s' % (table_name, skipped))
        if skipped:
            return

        # split
        # 'BENJY_EN' 'BENJY EN'
        matches = re.findall(
            r'^(.*?)[_ ]+(\w+)$', table_name
        )
        if not matches:
            self.warn(
                (
                    'Unsupported sheet name "%s".' +
                    ' Must have following format: "BENJY EN"'
                ).format(table_name),
            )
            return

        chapter = Chapter.update_or_create_from_table_name(matches[0][0])
        text = Text.get_or_create_from_code(matches[0][1])

        self.msg('Import all sentences')
        # values = [None for i in range(0, MAX_CELL_PER_ROW)]
        values = [None] * MAX_CELL_PER_ROW

        line = 0
        index = 0

        # process each row one at a time
        sentence_count = 0
        for row_len in self.get_rows_from_xml_table(xml_table, values):
            line += 1
            if line < 2:
                # skip the headers
                continue

            string = string = values[1][0]
            if string is None:
                string = ''
            if len(string) > 500:
                string = string[0:500]

            if not ((values[0][0] or '') + (values[1][0] or '')).strip():
                # empty line
                continue

            try:
                index = int(values[0][0])
            except ValueError:
                self.warn('Invalid sentence number (row {})'.format(
                    line
                ))
                continue

            Sentence.objects.update_or_create(
                text=text,
                chapter=chapter,
                index=index,
                defaults=dict(
                    string=string,
                    cell_line=line
                )
            )
            sentence_count += 1

        self.msg(' {} sentences'.format(sentence_count))

        self.msg('Delete left-over sentences')
        Sentence.objects.filter(
            chapter=chapter, text=text, index__gt=index
        ).delete()

    # ===============================================================
    # styles

    def reimport_table_styles(self, xml_root, chapter):
        root = xml_root

        self.styles = {
            s.name: s
            for s
            in SheetStyle.objects.filter(chapter=chapter)
        }

        for style in root.findall(".//style"):
            properties = style.find('table-cell-properties')
            color = ''
            if properties is not None:
                color = properties.attrib.get('background-color', color)
            name = style.attrib['name']
            data = {
                'name': name,
                'chapter': chapter,
                'color': color
            }

            has_changed = 0
            style_model = self.styles.get(name)
            if style_model:
                for f, v in data.items():
                    if getattr(style_model, f) != v:
                        setattr(style_model, f, v)
                        has_changed = 1
            else:
                has_changed = 1
                self.styles[name] = style_model = SheetStyle(**data)

            if has_changed:
                # print('updated' if style_model.pk else 'created')
                style_model.save()

    # ===============================================================
    # CLEAN

    def _action_clean(self):
        import difflib

        # todo: move this to the model
        # todo: call it during import
        c = 0
        for occurence in Occurence.objects.filter(
            text__code=self.DRAL_REFERENCE_CODE
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
                    # self.msg(word, lemma, ratio)
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

            # self.msg(occurence.cell, '=>', v)

            c += 1
            if 0 and c > 300:
                exit()

        for occurence in Occurence.objects.exclude(
                text__CODE=self.DRAL_REFERENCE_CODE):
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
                self.warn(v, 0)

            occurence.string = v

            occurence.save()

    # =============================================================
    # INPUT FILE PROCESSING

    def _pre_action(self):
        from django.conf import settings
        self.DRAL_REFERENCE_CODE = settings.DRAL_REFERENCE_LANGUAGE
        Text.add_default_texts()
        self.texts = Text.get_texts()
        self.messages = {
            'error': '',
            'messages': []
        }

    def import_sheets_from_file_arg(self, import_table_handler):
        try:
            file_path = self.aargs.pop()
            self.import_sheets_from_file(file_path, import_table_handler)
        except DRTEXTException:
            pass

    def import_sheets_from_file(self, file_path, import_table_handler):
        self._pre_action()

        root = self.get_element_tree_from_file(file_path)

        if root is not None:
            for table in root.findall(".//table"):
                import_table_handler(table, root)
                # break
        else:
            self.warn(
                'File "{}" is empty or not found.'.format(file_path),
                0,
                'ERROR'
            )

    def get_messages(self):
        return self.messages

    def warn(self, message, line_number=None, status='WARNING'):
        self.msg(message, line_number, status=status)
        return False

    def msg(self, message, line_number=None, status=''):
        if line_number:
            message = '(at row {}) {}'.format(line_number, message)
        if status:
            message = '{}: {}'.format(status, message)

        self.messages['messages'].append(message)

        print(message)

        if status == 'ERROR':
            self.messages['error'] = message
            raise DRTEXTException(message)

        return message

    def get_rows_from_xml_table(self, xml_table, values):
        '''
        Yield the column count for each row in <table>.
        And update <values> with array of pairs.
        One pair for each cell.
        pair = (textual_content, style)
        '''
        for row in xml_table.findall('table-row'):
            col = 0
            row_len = 0
            for cell in row.findall('table-cell'):
                # number-columns-repeated="2" table:style-name="ce2"
                repeated = cell.attrib.get('number-columns-repeated', 1)
                value = self.get_value_from_cell(cell)
                style = cell.attrib.get('style-name', None)
                for i in range(1, int(repeated) + 1):
                    if col >= len(values):
                        break
                    if value:
                        row_len = col + 1
                    values[col] = [
                        value,
                        style
                    ]
                    col += 1
            row_repeated = int(row.attrib.get('number-rows-repeated', 1))
            for i in range(1, min(row_repeated, 2) + 1):
                yield row_len

    def get_value_from_cell(self, cell):
        ret = ''

        para = cell.findall('p')
        if para:
            ret = self.get_text_from_element(para[0]).strip()

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
            self.warn(
                'Unsupported file extension, only accept .xml or .ods.',
                status='ERROR'
            )

        content = re.sub(r'(table|office|style|text|draw|fo):', '', content)

        return ET.fromstring(content)

    def _get_int(self, integer_str, default=0):
        try:
            ret = int(integer_str)
        except ValueError:
            ret = default
        return ret

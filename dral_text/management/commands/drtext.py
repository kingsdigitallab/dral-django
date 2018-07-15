'''
Created on 19 April 2018

@author: Geoffroy Noel
'''

from dral_wagtail.management.commands._kdlcommand import KDLCommand
import xml.etree.ElementTree as ET
import re
from dral_text.models import Language, Lemma, Occurence, Sentence, SheetStyle


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
        [o.delete() for o in Occurence.objects.all()]
        [o.delete() for o in Sentence.objects.all()]
        [o.delete() for o in Lemma.objects.all()]
        [o.delete() for o in SheetStyle.objects.all()]

    def action_import(self):
        Language.add_default_languages()
        self.languages = Language.get_languages()

        file_path = self.aargs.pop()
        content = self._read_file(file_path, encoding='utf-8')

        import re
        content = re.sub(r'(table|office|style|text|draw|fo):', '', content)

        root = ET.fromstring(content)

        table = root.find(".//table")

        self.chapter = table.attrib['name']

        # ### COLORS
        print('Importing sheet styles...')

        [o.delete() for o in SheetStyle.objects.filter(chapter=self.chapter)]

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
            # print(name, color)

        # return

        # ### STRINGS
        # Import the spreadsheet rows
        # identify blocks of rows that belong to the same english lemma
        # extract and import the occurence strings and metadata
        print('Importing strings...')

        # root = tree.getroot()
        # <table:table table:name="BENJY" table:style-name="ta1">

        values = [None for i in range(0, 2024)]

        line = 0

        block = []
        for cols in self.get_values_next_row(table, values):
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
                values = [None for i in range(0, 2024)]

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

        if 1:
            c = 0
            for occurence in Occurence.objects.filter(
                    language__name='EN').select_related('lemma'):
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

        for occurence in Occurence.objects.exclude(language__name='EN'):
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

    def process_lemma_block(self, block, line_number):
        '''
        Process a lemma block from the spreadsheet
        The block contains an array or rows.
        Format of each row describe in get_values_next_row()
        '''

        # print('\n'.join([l[4][0] for l in block]))

        lines = {}

        freq = 0

        lemma = ''
        for line in block:
            lemma_value = line[1][0]
            if lemma_value:
                afreq = re.match(r'\d+', line[2][0])
                if afreq:
                    if lemma:
                        self.show_message(
                            'block has more than one lemma',
                            line_number
                        )
                    else:
                        lemma = lemma_value
                        freq = int(afreq.group(0))

            if re.match(r'\d+', line[4][0]):
                lines['locations'] = line[4:]
            elif line[3][0]:
                lines[line[3][0]] = line[4:]
            elif line[4][0]:
                lines['EN'] = line[4:]

        differences = (
            set(lines.keys()) ^
            {'EN', 'RU', 'POL', 'LT', 'locations'}
        )

        if differences:
            self.show_message(','.join(differences), line_number)

        if not lemma:
            self.show_message(
                'block doesn\'t have a lemma',
                line_number
            )
        else:
            print('Block %s, %s' % (line_number, lemma))
            lemma, _ = Lemma.objects.get_or_create(
                string=lemma,
                language=self.languages['EN']
            )

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

            # read all the occurence records for that lemma
            occurrences = {
                '%s:%s' % (obj.language_id, obj.cell_col): obj
                for obj
                in Occurence.objects.filter(lemma=lemma, chapter=self.chapter)
            }

            for lg in ['EN', 'RU', 'LT', 'POL']:
                line = lines.get(lg)
                styles = {}
                if line:
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
                        occurence = occurrences.get(
                            '%s:%s' % (
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
                            print(v[0])
                        options['cell'] = v[0]
                        options['cell_style'] = v[1] or ''
                        if lg == 'EN':
                            options['string'] = '?'
                            options['context'] = options['cell'][:50]
                        else:
                            options['string'] = options['cell'][:20]
                            if len(v[0]) > 20:
                                print(v[0])

                        if occurence:
                            save = 0
                            for k in options.keys():
                                if getattr(occurence, k, None) != options[k]:
                                    save = 1
                                    setattr(occurence, k, options[k])
                        else:
                            occurence = Occurence(**options)
                            save = 1
                        if save:
                            occurence.save()
                        i += 1

    def get_values_next_row(self, table, values):
        '''
            Yield the column count for each row in <table>.
            And update values with array of pairs.
            One pair for each cell.
            pair = (textual_content, style)
        '''
        for row in table.findall('table-row'):
            col = 0
            for cell in row.findall('table-cell'):
                # number-columns-repeated="2" table:style-name="ce2"
                repeated = cell.attrib.get('number-columns-repeated', 1)
                value = self.get_value_from_cell(cell)
                style = cell.attrib.get('style-name', None)
                for i in range(1, int(repeated) + 1):
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
        '''Returns plain text content of the element
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

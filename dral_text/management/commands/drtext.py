'''
Created on 19 April 2018

@author: Geoffroy Noel
'''

from dral_wagtail.management.commands._kdlcommand import KDLCommand
import xml.etree.ElementTree as ET
import re
from dral_text.models import Language, Lemma, Occurence, Sentence, SheetStyle


class Command(KDLCommand):
    '''
    Usage:
    ./manage.py drtext import research_data/private/benjy/content.xml

    ce52 is yellow
    '''
    help = 'DRaL Text Processing'

    def action_clear(self):
        [o.delete() for o in Occurence.objects.all()]
        [o.delete() for o in Sentence.objects.all()]
        [o.delete() for o in Lemma.objects.all()]
        [o.delete() for o in SheetStyle.objects.all()]

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
            for line in lines.values():
                length = 0
                while line[length][0]:
                    length += 1
                if length < median:
                    median = length

            for lg in ['EN', 'RU', 'LT', 'POL']:
                line = lines.get(lg)
                styles = {}
                if line:
                    i = 0
                    for v in line:
                        if i >= median:
                            break
                        if not v[0]:
                            break

                        if v[1] not in styles:
                            styles[v[1]] = len(styles.keys())

                        options = dict(
                            cell_line=line_number,
                            cell_col=i,
                            language=self.languages[lg],
                            chapter=self.chapter
                        )

                        occurence = Occurence.objects.filter(**options).first()

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
                            for k in options.keys():
                                setattr(occurence, k, options[k])
                        else:
                            occurence = Occurence(**options)
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
                raise Exception(
                    'Unknown element in <cell><p> {}'.format(
                        child.tag))
            ret += child.tail or ''

        return ret.strip()

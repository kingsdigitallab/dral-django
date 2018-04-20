'''
Created on 19 April 2018

@author: Geoffroy Noel
'''

from dral_wagtail.management.commands._kdlcommand import KDLCommand
import xml.etree.ElementTree as ET
import re


class Command(KDLCommand):
    '''
    Usage:
    ./manage.py drtext import research_data/private/benjy/content.xml
    '''
    help = 'DRaL Text Processing'

    def action_import(self):
        file_path = self.aargs.pop()
        content = self._read_file(file_path, encoding='utf-8')

        import re
        content = re.sub(r'(table|office|style|text|draw):', '', content)

        root = ET.fromstring(content)
        table = root.find(".//table[@name='BENJY']")

        # root = tree.getroot()
        # <table:table table:name="BENJY" table:style-name="ta1">

        values = [None for i in range(0, 2024)]

        line = 0

        block = []
        for cols in self.get_values_next_row(table, values):
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

        lemma = ''
        for line in block:
            lemma_value = line[1][0]
            if lemma_value and re.match(r'\d+', line[2][0]):
                if lemma:
                    self.show_message(
                        'block has more than one lemma',
                        line_number
                    )
                else:
                    lemma = lemma_value

        if not lemma:
            self.show_message(
                'block doesn\'t have a lemma',
                line_number
            )

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

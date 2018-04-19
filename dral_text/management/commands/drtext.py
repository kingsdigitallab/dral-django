'''
Created on 19 April 2018

@author: Geoffroy Noel
'''

from dral_wagtail.management.commands._kdlcommand import KDLCommand
import xml.etree.ElementTree as ET


class Command(KDLCommand):
    '''
    '''
    help = 'DRaL Text Processing'

    def action_import(self):
        file_path = self.aargs.pop()
        content = self._read_file(file_path, encoding='utf-8')

        import re
        content = re.sub(r'(table|office|style|text|draw):', '', content)

        root = ET.fromstring(content)
        table = root.find(".//table[@name='BENJY']")
        print(table)

        # root = tree.getroot()
        # <table:table table:name="BENJY" table:style-name="ta1">
        for row in table.findall('table-row'):
            col = 0
            for cell in row.findall('table-cell'):
                # number-columns-repeated="2" table:style-name="ce2"
                span = cell.attrib.get('number-columns-repeated', None)
                if span:
                    col += int(span) - 1
                    print(span)
                col += 1
                pass
            print(row)

'''
Created on 15 Feb 2018

@author: Geoffroy Noel
'''

from django.core.management.base import BaseCommand
import os
import re
from django.db import transaction


class DryRunRollBackException(Exception):
    pass


class KDLCommand(BaseCommand):
    help = 'Import wordpress xml dump into wagtail'

    def add_arguments(self, parser):
        parser.add_argument('action', nargs=1, type=str)
        parser.add_argument('aargs', nargs='*', type=str)
        parser.add_argument(
            '-n', '--dry-run', action='store_true', dest='dry_run',
            help="Do everything except modify the database.",
        )

    def handle(self, *args, **options):
        self.options = options
        self.action = options['action'][0]
        self.aargs = options['aargs']

        show_help = True

        action_method = getattr(self, 'action_' + self.action, None)

        if action_method:
            show_help = False
            import time
            try:
                with transaction.atomic():
                    t0 = time.time()
                    action_method()
                    d = time.time() - t0
                    print(
                        'END of command "{}" ({:.2f} s.)'.format(
                            self.action, d)
                    )
                    if self.is_dry_run():
                        raise DryRunRollBackException
            except DryRunRollBackException:
                print('-' * 50)
                print('INFO: DRY RUN, nothing written to the database')
                print('-' * 50)

        if show_help:
            self.print_help(
                'manage.py',
                re.sub(r'^.*?([^/]+)\.py$', r'\1', __file__)
            )
            self.show_help()

    def is_dry_run(self):
        return self.options.get('dry_run', False)

    def _fetch_url(self, url):
        ret = None

        # read or download the page
        file_prefix = 'file://'
        if url.startswith(file_prefix):
            ret = self._read_file(url.replace(file_prefix, '/'))
        else:
            import requests
            res = requests.get(url)
            ret = res.content

        return ret

    def _read_file(self, filepath, encoding='utf-8'):
        import codecs
        f = codecs.open(filepath, 'r', encoding)
        ret = f.read()
        f.close()

        return ret

    def _write_path_and_file(self, file_path, content, path, encoding='utf8'):
        file_path = os.path.join(path, file_path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        self._write_file(file_path, content, encoding)

    def _write_file(self, file_path, content, encoding='utf8'):
        f = open(file_path, 'wb')
        if encoding:
            content = content.encode(encoding)
        f.write(content)
        f.close()

    def print_error(self, message):
        self.stdout.write('ERROR: {}'.format(message))

    def show_help(self):
        ret = '''
actions:

  download URL
    download all the assets referenced by URL into the assets folder
        '''

        self.stdout.write(ret)

        return ret

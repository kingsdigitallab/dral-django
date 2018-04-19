#!/usr/bin/env python
import os
import sys
import re
from random import randint
from os import makedirs


class Encryptor(object):

    data_dir = 'research_data'
    private_dir = 'private'
    archive_name = 'private_data.7z'
    archiver = '7z'
    archiver_install = 'sudo apt-get install p7zip-full'
    archiver_encrypt = '7z u ../{archive} -p\'{password}\' -mhe -up3 *'
    archiver_decrypt = '7z x ../{archive} -p\'{password}\' -aoa'
    archiver_list = '7z l ../{archive} -p\'{password}\''

    password_setting = 'KDLENCRYPT_KEY'
    password_length = 32

    help = '''usage: COMMAND [OPTIONS]

purpose: management tool for encrypted research data

Commands:
  init
    create the research data folders
  status
    show status information about encrypted files
  encrypt
    encrypt the files
  decrypt
    decrypt the files
  list
    list all encrypted files
  auto
    automatically encrypt or decrypt
  make_key
    create a new encryption key
'''

    def print_help(self):
        print(self.help)

    def run(self):
        found = False

        if len(sys.argv) > 1:
            self.command = sys.argv[1]
            self.options = sys.argv[2:]

            method_name = 'action_{}'.format(self.command)
            method = getattr(self, method_name, None)
            if method:
                method()
                found = True

        if not found:
            self.print_help()
        else:
            print('done')

    def action_make_key(self):
        chars = 'abcdefghijklmnopqrstuvwxyz'
        chars += chars.upper()
        chars += '1234567890!;-._@#'
        ret = ''.join([chars[randint(0, len(chars) - 1)]
                       for i in range(0, self.password_length)])
        print('# Add this line to your local.py')
        print("{} = '{}'".format(self.password_setting, ret))
        return ret

    def action_status(self):
        # akey = self.get_encrypt_key()
        pass

    def get_encrypt_key(self, silent=False):
        ret = None

        settings_path = os.popen(
            '''find -iname 'local.py' | grep 'settings/' '''
        ).read()

        if settings_path:
            command = '''grep '{}' {}'''.\
                format(self.password_setting, settings_path.strip(' \n'))
            code, res = self.exec(command)
            ret = re.findall("'([^']+)'", res)
            if ret:
                ret = ret[0]
            else:
                ret = None

        if not ret and not silent:
            print(
                'ERROR: Encryption key {} not found in your local.py file.'.
                format(self.password_setting))
            return

        return ret

    def action_decrypt(self):
        self.crypt(self.archiver_decrypt)

    def action_encrypt(self):
        self.crypt(self.archiver_encrypt)

    def action_list(self):
        self.crypt(self.archiver_list, show=True)

    def crypt(self, command, show=False):
        if not self.check_archiver():
            return

        self.recreate_dirs()

        password = self.get_encrypt_key()
        if not password:
            exit()

        command = command.format(**{
            'dir': os.path.join(self.data_dir, self.private_dir),
            'archive': self.archive_name,
            'password': password,
        })

        cwd = os.getcwd()
        os.chdir(os.path.join(self.data_dir, self.private_dir))
        code, output = self.exec(command)
        os.chdir(cwd)

        if code != 0:
            print('ERROR:')
            print(output)
        else:
            if show:
                print(output)

    def check_archiver(self, silent=False):
        res = os.system('{} > /dev/null'.format(self.archiver))
        if res != 0 and not silent:
            print('ERROR: archiver ({}) not found '.format(self.archiver))
        return res == 0

    def recreate_dirs(self):
        path = os.path.join(self.data_dir, self.private_dir)

        if not os.path.exists(path):
            print('Create path: {}'.format(path))
            try:
                makedirs(path)
            except FileExistsError:
                pass

    def action_init(self):
        self.recreate_dirs()

        if not self.get_encrypt_key():
            self.action_make_key()

        if not self.check_archiver(silent=True):
            print('# Installing archiver: {}'.format(self.archiver_install))
            os.system(self.archiver_install)

        # TODO: check that .gitignore has the following entry
        # research_data/private

    def exec(self, command):
        import subprocess

        # list of strings representing the command
        args = [p.replace('"', '').replace("'", '')
                for p in command.split(' ')]

        try:
            # stdout = subprocess.PIPE lets you redirect the output
            res = subprocess.Popen(args, stdout=subprocess.PIPE)
        except OSError:
            print("error: popen")
            # if the subprocess call failed, there's not much point in
            # continuing
            exit(-1)

        res.wait()
        code = res.returncode

        output = res.stdout.read().decode()

        return code, output


if __name__ == "__main__":
    Encryptor().run()

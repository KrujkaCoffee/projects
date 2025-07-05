'''Программа для создания архива с последней обновленной версии любой из программ MES'''

import os
import zipfile


class Main():
    def __init__(self):
        self.current_dir, self.current_file = os.path.split(os.path.abspath(__file__))
        self.ignore_files = [self.current_file, '.gitignore', 'python']  # 'run.bat''window_free.vbs', 'window.vbs',  игонрируются _*
        self.ignore_dirs = ['venv', 'clients_errors', '__pycache__', '.idea', '.git', 'Scripts', '.vscode'] # , 'Lib'
        self.ignor_fileends = ['.zip', '.pickle', '.dll', '.swp', '.un', '~', '.swo', '.pth', '.pyd']


    def none_or_val(self, val):
        return val if val != {} else None
    

    def check_file_end(self, file: str):
        for end_file in self.ignor_fileends:
            if file.endswith(end_file):
                return True


    def file_ignore_condition(self, file: str):
        path, file = os.path.split(file)
        if file.startswith('_'):
            return True
        elif self.check_file_end(file):
            return True
        return False


    def get_files(self, check_dir=None): 
        my_files = []
        if not check_dir:
            check_dir = self.current_dir
        for root, dirs, files in os.walk(check_dir):
            dirs[:] = [dir for dir in dirs if dir not in self.ignore_dirs]
            
            files[:] = [file for file in files if (file not in self.ignore_files) and not self.file_ignore_condition(file)]
            for fname in files:
                filename = os.path.join(root, fname)
                my_files.append(filename.replace(check_dir, '')[1:])
        return my_files


    def run(self, check_dir=None):
        files = self.get_files(check_dir)
        with zipfile.PyZipFile('archive.zip', mode='w') as zf:
            zf.debug = 3
            for file in files:
                zf.write(file)


if __name__ == '__main__':
    m = Main()
    m.run()

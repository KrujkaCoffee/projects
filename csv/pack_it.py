'''Программа для создания архива с последней обновленной версии любой из программ MES'''

import os
import shutil
from pathlib import Path
import zipfile


DEVELOP_SAFTY = True  # Защита от накатывания разработчику от диска Z
MY_ERRORS = 'my_errors.txt' # персональный файл ошибки минии гита для каждого клиента


class Main():
    def __init__(self):
        self.current_dir, self.current_file = os.path.split(os.path.abspath(__file__))
        # if DEVELOP_SAFTY:
        #     self.developers = ['g.sviridov', 'a.belyakov']
        # else:
        #     self.developers = []
        # self.who_im()
        # self.is_windows = True
        # self.pickle_name = 'hashed_files.pickle'
        self.ignore_files = [MY_ERRORS, self.current_file, '.gitignore', 'python', 'window_free.vbs', 'window.vbs', 'run.bat']  #  игонрируются _*
        self.ignore_dirs = ['venv', 'clients_errors', '__pycache__', '.idea', '.git', 'Scripts', 'Lib']
        # self.server_dir = r"Z:\Tehkarti\embed"
        # self.pickle_path = os.path.join(self.server_dir, self.pickle_name)


    # def test_func(self):
    #     '''Принудительное задание роли'''
    #     self.is_server = True


    # def run(self):
    #     if self.is_server:
    #         self.server_actions()  # успешно
    #     else:
            # self.client_actions()  # успешно

    # def who_im(self):
    #     self.is_server = None
    #     self.is_client_or_test = None
    #     pc_login = getpass.getuser()

    #     if self.current_dir.startswith("Z:"):
    #         self.is_server = True
    #     elif pc_login in self.developers:
    #         raise ValueError('сработала защита накатывания обновления разработчику от сервера(диска Z)')
    #     else:
    #         self.is_client_or_test = None


    # def run(self):
    #     print('client actions')
        # if os.path.exists(self.pickle_path):
            # srv_files, srv_dirs = self.load_pickle(self.pickle_path)
            # client_files, client_dirs = self.get_hashed_files()
            # res_check_dirs = self.difference_dirs(srv_dirs, client_dirs)
        #     if res_check_dirs:
        #         create_dirs, del_dirs = res_check_dirs
        #         if create_dirs:
        #             self.make_dirs(create_dirs, self.current_dir)
        #     self.check_files(srv_files, client_files, self.current_dir, self.server_dir, del_file=False)
        # # else:
        #     print(f'на сервере нет {self.pickle_name} клиент не имеет право его там создавать')
        
    # def server_actions(self):
    #     print('server_actions')
    #     files, dirs = self.get_hashed_files()
    #     self.save_hashed_fils(files, dirs)

    # def del_file(self, full_path):
    #     if os.path.exists(full_path):
    #         if self.is_windows:
    #             os.chmod(full_path, 0o777)
    #         os.remove(full_path)

    # def del_dir(self, dir_path):
    #     try:
    #         shutil.rmtree(dir_path)
    #     except OSError as e:
    #         print(f'папка уже была удалена ранним проходом {e}')

    def copy_file(self, file_path, source, distanation, del_file=True):
        source = os.path.join(source, file_path)
        distinct = os.path.join(distanation, file_path)
        if del_file and os.path.exists(distinct):
            self.del_file(distinct)
        shutil.copy(source, distinct)

    def make_dirs(self, create_dirs, path):
        for dir in create_dirs:
            path = os.path.join(path, dir)
            Path(path).mkdir(parents=True, exist_ok=True)

    def del_dirs(self, del_dirs, destanation):
        for dir in del_dirs:
            path = os.path.join(destanation, dir)
            try:
                shutil.rmtree(path)
            except (FileNotFoundError, PermissionError) as e:
                print(f'папка уже была удалена ранним проходом {e}')    

    def difference_dirs(self, mast_be_dirs, check_dirs):
        '''различия между папками, получить папки на удаление и на создание'''
        if mast_be_dirs != check_dirs:
            set_mast_be_dirs = set(mast_be_dirs)
            set_check_dirs = set(check_dirs)
            create_dirs = set_mast_be_dirs.difference(set_check_dirs)
            del_dirs = set_check_dirs.difference(set_mast_be_dirs)
            return self.none_or_val(create_dirs), self.none_or_val(del_dirs)

    def none_or_val(self, val):
        return val if val != {} else None

    def file_ignore_condition(self, file: str):
        path, file = os.path.split(file)
        if file.startswith('_'):
            return True
        elif file.endswith('.dll') or file.endswith('.pickle') or file.endswith('.zip'):
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

import os 
import sys
import pickle

def name_of_executable_file_c():
    try: #18.08.25 во время запуска через редактор __file__ в интерактиве отсутствует (так же интерактив
        if getattr(sys, 'frozen', False):
            return os.path.basename(sys.executable)
        elif hasattr(sys.modules['__main__'], '__file__'):
            return os.path.basename(sys.modules['__main__'].__file__)
        elif sys.argv[0]:
            return os.path.basename(sys.argv[0])
        else:
            return None
    except Exception as e:
        return None
PATH_USR = os.path.expanduser('~')
def existence_file_c(putf:str)->bool:
    putf = os.path.normpath(putf)
    return os.path.exists(putf)

def create_dir_c(path:str)->bool:
    try:
        os.makedirs(path)
        return True
    except:
        print(f'PermissionError: [WinError 5] Отказано в доступе: {path}')
        return False

def tmp_dir():
    name_module = name_of_executable_file_c().split('.')[0]
    if existence_file_c(os.sep.join([PATH_USR, 'mes_tmp'])) == False:
        create_dir_c(os.sep.join([PATH_USR, 'mes_tmp']))
    if existence_file_c(os.sep.join([PATH_USR, 'mes_tmp', name_module])) == False:
        create_dir_c(os.sep.join([PATH_USR, 'mes_tmp', name_module]))
    return os.sep.join([PATH_USR, 'mes_tmp', name_module])

def load_file_pickle(putima)->dict:
    try:
        with open(putima, 'rb') as f:
            return pickle.load(f)
    except pickle.UnpicklingError as e:
        print(f'Ошибка десериализации файла: {putima!r}\n {e}')


def load_tmp_stukt(ima, default_val=None):
    puth_name = tmp_dir() + os.sep + ima + '.pickle'
    if existence_file_c(puth_name) == True:
        val = load_file_pickle(puth_name)
        return val
    return default_val

def save_file_pickle(putima, obj):
    with open(putima, 'wb') as f:
        pickle.dump(obj, f)

def save_tmp_stukt(data, name):
    puth_name = tmp_dir() + os.sep + name + '.pickle'
    save_file_pickle(puth_name, data)

class UserCache():
    _tmp_dir = tmp_dir()
    _name = 'UserCache'
    def __init__(self):
        self._data:dict = None

    def load(self):
        self._data = load_tmp_stukt(self._name,None)
        if self._data is None:
            self._data = dict()
        for k,v in self.__dict__.items():
            if k.startswith('_'):
                continue
            if k in self._data:
                setattr(self,k,self._data[k])
        pass

    def save(self):
        for k,v in self.__dict__.items():
            if k.startswith('_'):
                continue
            self._data[k] = v
        save_tmp_stukt(self._data,self._name)
    
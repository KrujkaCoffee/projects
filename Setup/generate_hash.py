import sys
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

import hashlib
import pickle
import pathlib
import tempfile

"""
Генерирует хэш из зависимостей КЛИЕНТСКОГО интерпретатора (pip freeze)
Необходим запуск от клиентского (python.exe) 
"""


def get_installed_packages():
    import importlib.metadata
    installed_packages = importlib.metadata.distributions()
    return sorted([f"{pkg.metadata['Name']}=={pkg.version}" for pkg in installed_packages if pkg.metadata['Name'] != 'pip'])

def generate_hash(package_list):
    hash_object = hashlib.sha256()
    hash_object.update('\n'.join(package_list).encode('utf-8'))
    return hash_object.hexdigest()

def pack_hash():
    temp = tempfile.gettempdir()
    folder = pathlib.Path(temp) / 'mes_libs'
    folder.mkdir(exist_ok=True, parents=True)
    path = folder / 'lib_hash.pickle'
    
    print(f'Задан путь для сохранения хэша интерпретатора: "{path}"')
    with open(str(path), 'wb+') as desc:
        packages = get_installed_packages()
        package_hash = generate_hash(packages)
        pickle.dump({'packages_hash': package_hash, 'packages': packages}, desc)
        print(f'Хэш библиотек успешно сгенерирован: {package_hash}')

if __name__ == '__main__':
    pack_hash()
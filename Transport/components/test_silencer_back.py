import project_cust_38.Cust_Functions as F
from calc_silencer_input_params import list_dicts_data_input as list_dicts_data_input
from calc_silencer_output_params import OUTPUT_PARAMS as OUTPUT_PARAMS
import calc_silencer_functions_M5_M400 as silencer_functions
import ast
import re
from collections import defaultdict, deque, OrderedDict


def extract_params_from_functions(filepath):
    """
    Возвращает словарь:
    {имя_функции_без_calc_: [список ключей params, которые она использует]}
    """

    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()

    tree = ast.parse(code)
    result = {}

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("calc_"):
            func_name = node.name[5:]  # убираем префикс "calc_"
            used_keys = set()

            # обходим все узлы функции
            for subnode in ast.walk(node):
                # варианты params["..."] и params['...']
                if isinstance(subnode, ast.Subscript):
                    if (isinstance(subnode.value, ast.Name) and subnode.value.id == "params"):
                        if isinstance(subnode.slice, ast.Constant) and isinstance(subnode.slice.value, str):
                            used_keys.add(subnode.slice.value)

                # вариант params.get("...")
                if isinstance(subnode, ast.Call):
                    if (isinstance(subnode.func, ast.Attribute)
                        and isinstance(subnode.func.value, ast.Name)
                        and subnode.func.value.id == "params"
                        and subnode.func.attr == "get"):
                        if len(subnode.args) > 0 and isinstance(subnode.args[0], ast.Constant):
                            used_keys.add(subnode.args[0].value)

                # проверки вида "key" in params
                if isinstance(subnode, ast.Compare):
                    for comp in subnode.comparators:
                        if isinstance(comp, ast.Name) and comp.id == "params":
                            if isinstance(subnode.left, ast.Constant) and isinstance(subnode.left.value, str):
                                used_keys.add(subnode.left.value)

            # f-строки — парсим как текст и выдёргиваем через regex
            fstring_keys = re.findall(r'params\[(?:\'|")([^\'"]+)(?:\'|")\]', code[node.lineno-1:node.end_lineno])
            fstring_keys += re.findall(r'params\.get\((?:\'|")([^\'"]+)(?:\'|")', code[node.lineno-1:node.end_lineno])
            used_keys.update(fstring_keys)

            result[func_name] = sorted(used_keys)

    return result

def sort_by_dependencies(dep_dict):
    """
    dep_dict: словарь {ключ: [зависимости]}
    возвращает список ключей в порядке уровней зависимостей
    """

    # строим граф и считаем количество зависимостей (in-degree)
    graph = defaultdict(list)
    indegree = {k: 0 for k in dep_dict}

    for key, deps in dep_dict.items():
        for d in deps:
            if d in dep_dict:  # учитывать только если зависимость тоже в словаре
                graph[d].append(key)
                indegree[key] += 1

    # очередь для узлов без зависимостей
    q = deque([k for k, deg in indegree.items() if deg == 0])
    sorted_keys = []

    while q:
        node = q.popleft()
        sorted_keys.append(node)

        for nei in graph[node]:
            indegree[nei] -= 1
            if indegree[nei] == 0:
                q.append(nei)

    # добавляем те, что остались (циклические или внешние зависимости)
    remaining = [k for k in dep_dict if k not in sorted_keys]
    sorted_keys.extend(remaining)

    return sorted_keys

def reorder_dict(dep_dict, sorted_keys):
    """
    dep_dict: исходный словарь {ключ: значение}
    sorted_keys: список ключей в порядке зависимостей (из sort_by_dependencies)
    возвращает OrderedDict с тем же содержимым, но в новом порядке
    """
    return OrderedDict((k, dep_dict[k]) for k in sorted_keys if k in dep_dict)


#filepath = "calc_silencer_functions_M5_M400.py"
#mapping = extract_params_from_functions(filepath)
#sorted_keys = sort_by_dependencies(mapping)
#CALC_FUNCTIONS = reorder_dict(silencer_functions.CALC_FUNCTIONS, sorted_keys)
#for item, val in CALC_FUNCTIONS.items():
#    part2 = "{" + f'"fnc": {val['fnc'].__name__}, "cell": "{val['cell']}"' + "})," #('edinica_rashoda_imya', {'fnc': calc_edinica_rashoda_imya, 'cell': 'Excel O5'}),
#    print(f'("{item}", {part2}')
def calc_new_data(input_data: dict) -> list | dict:
    list_err = []
    calculated = {}

    # Константы
    constants = {
        'gas_constant': 287,
        'gravity': 9.81,
        'pi': 3.14,
        'accel_zone_coef': 2.2,
        'compressor_efficiency': 0.65,
        'compressor_pressure_loss': 0.3,
        'atm_pressure': 1.033,
        'safety_factor': 1.2
    }

    # Объединяем входные данные с константами
    params = {**constants, **input_data}

    # Вспомогательные функции проверки
    def check_positive(name, value, header):
        if value <= 0:
            list_err.append({
                'header': header,
                'val': value,
                'Exception': f"{header} должно быть положительным числом"
            })
            return False
        return True

    def check_range(name, value, min_val, max_val, header):
        if not (min_val <= value <= max_val):
            list_err.append({
                'header': header,
                'val': value,
                'Exception': f"{header} должно быть в диапазоне [{min_val}, {max_val}]"
            })
            return False
        return True

    # Выполняем расчеты
    counter_err = 0
    for num, keyfn in enumerate(silencer_functions.CALC_FUNCTIONS.items()):
        key, info = keyfn
        fn = info['fnc']
        try:
            calculated[key] = fn({**params, **calculated})
        except Exception as e:
            counter_err += 1
            calculated[key] = None

            counter_err_2= 0
            for num_2, keyfn_2 in enumerate(silencer_functions.CALC_FUNCTIONS.items()):
                key_2, info_2 = keyfn_2
                fn_2 = info_2['fnc']
                if key_2 == e.args[0]:
                    break
                counter_err_2 += 1
            if counter_err_2 == len(silencer_functions.CALC_FUNCTIONS):
                coords = ''
            else:
                coords = f' из {counter_err_2} перед {num} , '
            print(f"[ERROR {counter_err}] row:{coords}key: {key}, fn: {fn.__name__},: {e} ")

    # Возвращаем результат в зависимости от наличия ошибок
    if list_err:
        return list_err
    else:
        return calculated

def test_datas():
    data_params = {_['name']: (F.valm(_['default_val']) if not _['type'] == 'str' else _['default_val'] ) for _ in list_dicts_data_input }
    rez = calc_new_data(data_params)
    print( rez)



if __name__ == "__main__":

    test_datas()
def strtodate(str, format="%Y-%m-%d %H:%M:%S"):#"%d.%m.%Y"   "%Y-%m-%dT%H:%M:%S"
    if len(format) > 11:
        if len(str) < 11:
            str += ' 00:00:00'
    return DT.strptime(str, format)

def datetostr(date, format="%Y-%m-%d %H:%M:%S"):#"%d.%m.%Y"   "%Y-%m-%dT%H:%M:%S"
    return date.strftime(format)

def is_numeric(string: any):
    # уже число
    if isinstance(string, (int, float)):
        return True
    # не строка — сразу нет
    if not isinstance(string, str):
        return False
    # нормализация
    val = string.replace(',', '.')
    # попытка преобразования
    try:
        float(val)
        return True
    except ValueError:
        return False

def boolm(str_data)->bool:
    if isinstance(str_data, bool):
        return str_data
    if str_data is None:
        return False
    if isinstance(str_data, str):
        if str_data.lower() in {'false','0',''}:
            return False
        if str_data.lower() in {'true','1'}:
            return True
    elif isinstance(str_data, int):
        if str_data == 0:
            return False
        else:
            return True
    else:
        return True

    raise Exception(f"boolm Не могу распознать '{str_data}'")

def valm(ch):
    if isinstance(ch,bool):
        return int(ch)
    if ch == 'None':
        return 0
    if isinstance(ch,str):
        boolmval = None
        try:
            boolmval  =  boolm(ch)
        except:
            pass
        if boolmval != None:
            return int(boolmval)
        ch = ch.replace(',', '.')
        if 'e'  in ch.lower():
            try:
                return float(ch)
            except:
                return 1
        if ch == '':
            return 0
        try:
            if '.' in ch:
                ch = float(ch.replace(' ', ''))
            else:
                ch = int(ch)
        except:
            return 0
    return ch

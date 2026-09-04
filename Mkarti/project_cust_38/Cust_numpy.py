from numpy import array as arrnum


def faster_arr(spisok, stolb, tip_int_float='int'):
    """from numba import njit

@njit(fastmath=True, cache=True)
def foo(tmp):"""
    tmp = []
    for i in range(len(spisok)):
        tmp.append(spisok[i][stolb])
    tmp = arrnum(tmp, 'int')
    return tmp

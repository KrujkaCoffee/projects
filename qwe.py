import sys

from PyQt5 import QtWidgets

from project_cust_38 import Cust_Qt as CQT


test_data = [
    ['№', 'Наименование'],
    [1, 'Первая строка'],
    [2, 'Вторая строка'],
]

pm = CQT.PageManager(page_size=20)

data = [
    {
        '№': i + 1,
        'Наименование': f'Строка {i + 1}',
    }
    for i in range(235)
]


if __name__ == '__main__':
    from project_cust_38 import Cust_application as CAPP
    app = CAPP.SafeApplication(sys.argv)
    CAPP.install_crash_guard(app, app_name='', user_name='')
    window = QtWidgets.QMainWindow()

    CQT.msgboxg_get_table(
        window,
        'длинное сообщение' * 666,

        data,
        page_manager=pm
    )

    app.exec()
    # pm.set_data(data)
    #
    # print(pm.current_page)
    # print(pm.count_pages)
    # print(len(pm.page_data()[0]))
    #
    # pm.next()
    #
    # print(pm.current_page)
    # print(len(pm.page_data()[0]))
    #
    # pm.last()
    #
    # print(pm.current_page)
    # print(len(pm.page_data()[0]))
    #
    # print(pm.next())
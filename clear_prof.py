


from project_cust_38 import Cust_SQLite as CSQ

path = r'Z:\Data\mag.db'
blocks = CSQ.custom_request_c(
    path,
    'select Запись, Пномер from blocks where poki = 0',
    rez_dict=True
)

for block in blocks:
    pk = block['Пномер']
    body = block['Запись']
    if '12837.1.1' in body:
        print(pk)
        body = body.replace('12837.1.1', '12837.1')
        result = CSQ.custom_request_c(path, 'UPDATE blocks SET Запись = ? WHERE Пномер = ?',
                             list_of_lists_c=[body, pk])
        print(result)


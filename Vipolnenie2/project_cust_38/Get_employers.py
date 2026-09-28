import datetime

import requests
from requests.auth import HTTPBasicAuth


class Main:
    def __init__(self):
        self.full_users = {}
        self.basic = HTTPBasicAuth('ipmorozov2', '777')

    def preparate_users(self, users, date=None):
        if not date:
            date = f'{datetime.datetime.now().date()}'
        parsed_users = {}
        for user in users:
            if parsed_users[user['ID']]:
                user_di = parsed_users[user['ID']]
                for k, v in user:
                    if k not in ('ФИО', 'ID'):
                        user_di[k].append(v)
                parsed_users[user['ID']] = user_di  # по идее он и так вставляется в словарь протестировать что не надо переприсваивать
            else:
                id_user = user.get('ID')
                inner_di = {}
                for k, v in user.items():
                    if k in ('ФИО', 'ID'):
                        inner_di[k] = v
                    else:
                        inner_di[k] = [v]
                parsed_users[id_user] = inner_di

        self.full_users[date] = parsed_users
        print(f'Получено {len(parsed_users)} пользователей, на {date}')


    def run(self, fio=None, date=None, id=None):
        current_date = f'{datetime.datetime.now().date()}'
        users_in_date = self.full_users.get(current_date if not date else date)
        if not users_in_date:
            try:
                if not date:
                    res = requests.get('http://novgorod/IPMorozov/hs/SDE/Staff/', auth=self.basic)
                elif date:
                    res = requests.get(f'http://novgorod/IPMorozov/hs/SDE/work_in_date/?find_day={date}', auth=self.basic)
                res = res.json()
                
                self.preparate_users(res, date)
            except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout, requests.exceptions.JSONDecodeError):
                print('ошибка соединения')
                return None
        
        if fio:
            for users_di in self.full_users[current_date if not date else date]:
                find_user = []
                for user in users_di:
                    if user.get('ФИО') == fio:
                        find_user.append(user)
                return find_user
        elif id:
            return self.full_users[current_date if not date else date].get(id)
        else:
            return self.full_users[current_date if not date else date]


if __name__ == '__main__':
    m = Main()
    m.run()  # получить всех на сегодня
    m.run(fio="Петров Петр Петрович")  # получить одного на сегодня
    m.run(fio="Петров Петр Петрович", date='2024-04-27')  # получить одного на дату
    m.run(date='2024-04-27')  # получить всех на дату


    # # или fio или ID
    # m.run(date='2024-04-27', id=2342342)  # получить одного на дату
    # m.run(id=2342342)  # получить одного на сегодня
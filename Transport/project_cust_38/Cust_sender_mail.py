import getpass

import requests

def sender(to_addr, file_path, text=None, subject=None):
    data = {}
    data['login'] = getpass.getuser()
    data['subject'] = "MES оповещение" if not subject else subject
    data['text'] = ' ' if not text else text
    data['to_addr'] = to_addr
    with open(file_path, 'rb') as file:
        # url = "http://localhost:5055/send_file/"
        url = "http://192.168.50.44:5055/email/send_file/"
        files = {"file": (file.name, file, "multipart/form-data")}
        response = requests.post(url, data = data, files = files)
    print(response.status_code)
    print(response.json())
    if response.status_code == 200:
        print('отправка успешна')
        return True
    else:
        print('ошибка отправки')
        return False

import logging
import typing

import urllib3
import requests

import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_config as CFG
import project_cust_38.Cust_Functions as F

urllib3.disable_warnings()
"""https://dev.1c-bitrix.ru/learning/course/index.php?COURSE_ID=93&LESSON_ID=11479&LESSON_PATH=7657.7685.11477.11479"""

id  ='chat49451'
logging.basicConfig(level=logging.INFO)

class B24Config:
    BASE_REST_URL = 'https://bitrix24.kelast.ru/rest/'

    USER_ID_ADMIN = 1
    USER_ID_BOTAPI = 3342

    AUTH_TOKEN_LANDING = 'stno5v2z4n6qfu98'

    # enpoints
    END_CHANGE_LANDING_BLOCK = 'landing.block.updatecontent'


class BaseSender:
    def _make_table_body(self,
                         lst_of_lists: list[list] | list[dict],
                         have_header: bool = True,
                         horizontal: bool = True) -> dict[str, list[dict]]:
        display_view = 'LINE' if horizontal else 'COLUMN'

        if len(lst_of_lists) == 0:
            return False
        msg = []
        header = lst_of_lists[0]
        if isinstance(header, dict):
            lst_of_lists = F.list_of_dicts_to_list_of_lists(lst_of_lists)
            header = lst_of_lists[0]

        _slice = slice(None, None)
        if have_header:
            _slice = slice(1, None)
        for column_idx in range(len(header)):
            column_data = []
            for row_data in lst_of_lists[_slice]:
                column_data.append(str(row_data[column_idx]))
            msg.append({'NAME': header[column_idx], 'VALUE': '\n'.join(column_data), 'DISPLAY': display_view})
        return {'GRID': msg}


class B24Sender(BaseSender):
    _URL = f'{B24Config.BASE_REST_URL}1/ebehb6fsejx39kj2/'
    _NOTIFY_ENDPOINT = 'im.notify.personal.add'
    _SEND_MESSAGE_ENDPOINT = 'im.message.add'
    _EDIT_MESSAGE_ENDPOINT = 'im.message.update'

    def get_chat_id_by_action(self, action: str):
        if CFG.Config.user_config.is_developer:
            return 'chat90445'
        if action.startswith('chat') and F.is_numeric(action[4:]):
            return action
        db_naryad = CFG.Config.project.db_naryad
        poki = CFG.Config.place.poki
        result = CSQ.custom_request_c(
            db_naryad,
            f'SELECT chat_id FROM place_chat_info WHERE name = {action!r} AND poki = {poki}',
            rez_dict=True,
            one=True
        )
        if isinstance(result, dict) and 'chat_id' in result:
            return result['chat_id']

    def send_msg_by_action(self, action: str, msg: str,form_dict:dict=None,msg_bold:bool=False,basement_msg:str=None,
                           attach: list = None) -> bool:
        chat_id = self.get_chat_id_by_action(action) #chat_id = 'chat88696'
        if chat_id:
            return self.send_msg_by_chat_id(chat_id, msg,form_dict=form_dict,msg_bold=msg_bold,basement_msg=basement_msg, attach=attach)
        logging.error('[b24-chat]Ошибка отправки сообщения')
        return False

    def send_msg_table_by_action(self, action: str,title:str, tbl: list[dict],chat_id:str|None=None) -> bool:
        if chat_id is None:
            chat_id = self.get_chat_id_by_action(action)
        if chat_id:
            return self.send_msg_table(tbl, chat_id, title, bold_title = False  )
        logging.error('[b24-chat]Ошибка отправки сообщения')
        return False

    def send_msg_by_chat_id(self, chat_id: str, msg: str, attach = None,form_dict:dict=None,msg_bold:bool=False,basement_msg:str=None,
                            message_id: int = None) -> bool:
        if msg_bold:
            msg = f'[B]{msg}[/B]'
        if form_dict:
            msg = f'{msg}\n' + '\n'.join([f'>> {k}: {v}' for k, v in form_dict.items()])
        if basement_msg:
            msg = f'{msg}\n{basement_msg}'
        body = {
            'DIALOG_ID': chat_id,
            'MESSAGE': msg,
        }
        if attach is not None:
            body['ATTACH'] = attach
        endpoint = self._SEND_MESSAGE_ENDPOINT
        if message_id is not None:
            endpoint = self._EDIT_MESSAGE_ENDPOINT
            body['MESSAGE_ID'] = message_id
        response = requests.post(f'{self._URL}{endpoint}', json=body, verify=False)
        data = response.json()
        match data:
            case {'result': chat_id}:
                return chat_id
            case _:
                return False

    def send_msg_table( #03.09.25
            self,
            lst_of_lists: list[list] | list[dict],
            chat_id: str,
            title: str = '',
            bold_title: bool = True,
            have_header: bool = True,
            horizontal: bool = True,
            message_id: int = None
    ) -> bool:
        """
            Отправка табличной части как сообщение в чат Б24
            @example
                send_msg_table(
                    lst_of_lists=[['header1', 'header2'], ['message1', 'message2']],
                    chat_id='chat123123',
                    title='Тест Тестович удалил(а) базу данных')
        """
        if len(lst_of_lists) == 0:
            return False
        if title and bold_title:
            title = f'[B]{title}[/B]'
        attach_body = self._make_table_body(lst_of_lists=lst_of_lists, have_header=have_header, horizontal=horizontal)
        return self.send_msg_by_chat_id(chat_id, title, [attach_body], message_id=message_id)

    def send_notify(self, user_id: int, message: str, message_for_mail: str = '', tag: str = 'MES'): #04.08.25
        """
        @user_id            id пользователя в битрикс
        @message            message сообщение из оповещения
        @message_for_mail   оповещение для почты (выключено)
        @tag                тэг оповещения
        """
        body = {
            'USER_ID': user_id,
            'MESSAGE': message,
            'MESSAGE_OUT': message_for_mail,
            'TAG': tag,
        }
        response = requests.post(f'{self._URL}{self._NOTIFY_ENDPOINT}', json=body, verify=False)
        return response.ok

class MessageBuilder:
    """
        @example
            table1 = [{
                'Наименование': 'Чехол защитный D600-800',
                'Количество': 2
            }]
            table2 = [{
                    'Операция': 'Раскрой',
                    'Тшт': 46.8,
                    'Тпз': 5.0,
                    'КР': 1,
                    'Профессия': 'Раскройщик 2 разряда'
                },
                {
                    'Операция': 'Швейные работы',
                    'Тшт': 32.8,
                    'Тпз': 0.01,
                    'КР': 1,
                    'Профессия': 'Швея 3 разряда'
            }]

            template = CB24.MessageBuilder('Таблица с дсе') Инициализация (базовое сообщение)
            template.add_table(table1)                      Добавить табличную часть
            template.add_delimiter()                        Добавить разделитель
            template.add_message('Таблица с операциями')    Добавить сообщение
            template.add_table(table2)                      Добавить таблицу 2
            template.send_by_chat_id('chat78766')           Итоговая отправка
    """

    def __init__(
            self,
            init_title: str,
            bold_title: bool = True
    ) -> None:
        if bold_title:
            init_title = f'[B]{init_title}[/B]'
        self.title = init_title
        self.sandwich = []
        self.__sender = B24Sender()

    def add_table(self,
        lst_of_lists: list[list] | list[dict],
        have_header: bool = True,
        horizontal: bool = True
    ):
        table_body = self.__sender._make_table_body(lst_of_lists, have_header=have_header, horizontal=horizontal)
        self.sandwich.append(table_body)

    def add_message(self, message: str, bold: bool = False):
        """Добавить сообщение."""
        if bold:
            message = f'[B]{message}[/B]'
        self.sandwich.append({'MESSAGE': message})

    def add_delimiter(self, size: int = 400, color: str = "#ffffff"):
        """Добавляет разделитель.
            :size - ширина линии.
            :color цвет линии (по дефолту прозрачная).
        """
        self.sandwich.append({'DELIMITER': {'SIZE': size,'COLOR': color}})

    def add_link(self, name: str, url: str):
        """Добавляет кликабельную ссылку.
            :name - Наименование ссылки.
            :url ссылка.
        """
        self.sandwich.append({'LINK': {'NAME': name,'LINK': url}})

    def send_by_action(self, action: str):
        """Отправка сообщения по наименованию action (Все action содержаться в Naryad.db->place_chat_info"""
        self.__sender.send_msg_by_action(action, self.title, attach=self.sandwich)

    def send_by_chat_id(self, chat_id: str):
        """Отправка сообщения по chat_id"""
        self.__sender.send_msg_by_chat_id(chat_id, self.title, attach=self.sandwich)

class HtmlContentDeployer:
    def pick_html_into_landing_block(self, *, html, matrix_id_landing_b24, matrix_id_landing_table_block_b24) -> bool:
        """Прикрепить html к блоку объекта landing"""
        url = f'{B24Config.BASE_REST_URL}{B24Config.USER_ID_BOTAPI}/{B24Config.AUTH_TOKEN_LANDING}/{B24Config.END_CHANGE_LANDING_BLOCK}'
        response = requests.post(
            url,
            json={
                'lid': matrix_id_landing_b24,
                'block': matrix_id_landing_table_block_b24,
                'content': html,
                'scope': 'knowledge'
            },
            verify=False
        )
        return response.ok


# https://bitrix24.kelast.ru/online/?IM_DIALOG=chat41228
if __name__ == '__main__':
    #b24 = B24(id)
    #b24.msg('test2')
    quit()

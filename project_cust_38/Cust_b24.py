import logging

import urllib3
import requests

import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_config as CFG
import project_cust_38.Cust_Functions as F

urllib3.disable_warnings()
"""https://dev.1c-bitrix.ru/learning/course/index.php?COURSE_ID=93&LESSON_ID=11479&LESSON_PATH=7657.7685.11477.11479"""

id  ='chat49451'
logging.basicConfig(level=logging.INFO)


class B24Sender:
    _URL = 'https://bitrix24.kelast.ru/rest/1/ebehb6fsejx39kj2/'
    _NOTIFY_ENDPOINT = 'im.notify.personal.add'

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

    def send_msg_by_action(self, action: str, msg: str,form_dict:dict=None,msg_bold:bool=False,basement_msg:str=None) -> bool:
        chat_id = self.get_chat_id_by_action(action)
        if chat_id:
            return self.send_msg_by_chat_id(chat_id, msg,form_dict=form_dict,msg_bold=msg_bold,basement_msg=basement_msg)
        logging.error('[b24-chat]Ошибка отправки сообщения')
        
    def send_msg_table_by_action(self, action: str,title:str, tbl: list[dict]) -> bool:
        chat_id = self.get_chat_id_by_action(action)
        if chat_id:
            return self.send_msg_table(tbl, chat_id, title, bold_title = False  )
        logging.error('[b24-chat]Ошибка отправки сообщения')

    def send_msg_by_chat_id(self, chat_id: str, msg: str, attach = None,form_dict:dict=None,msg_bold:bool=False,basement_msg:str=None) -> bool:
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
        response = requests.post(f'{self._URL}im.message.add', json=body, verify=False)
        return response.ok

    def send_msg_table( #03.09.25
            self,
            lst_of_lists: list[list],
            chat_id: str,
            title: str = '',
            bold_title: bool = True,
            have_header: bool = True,
            horizontal: bool = True,
    ) -> bool:
        """
            Отправка табличной части как сообщение в чат Б24
            send_msg_table(
                lst_of_lists=[['header1', 'header2'], ['message1', 'message2']],
                chat_id='chat123123',
                title='Тест Тестович удалил(а) базу данных')

            COLOR_TOKEN primary синий secondary серый alert красный base прозрачный
        """
        display_view = 'LINE' if horizontal else 'COLUMN'

        if len(lst_of_lists) == 0:
            return False
        header = lst_of_lists[0]
        if isinstance(header, dict):
            lst_of_lists = F.list_of_dicts_to_list_of_lists(lst_of_lists)
            header = lst_of_lists[0]

        if title and bold_title:
            title = f'[B]{title}[/B]'
        msg = []
        _slice = slice(None, None)
        if have_header:
            _slice = slice(1, None)
        for column_idx in range(len(header)):
            column_data = []
            for row_data in lst_of_lists[_slice]:
                column_data.append(str(row_data[column_idx]))
            msg.append({'NAME': header[column_idx], 'VALUE': '\n'.join(column_data), 'DISPLAY': display_view})
        return self.send_msg_by_chat_id(chat_id, title, [{'GRID': msg}])

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

# https://bitrix24.kelast.ru/online/?IM_DIALOG=chat41228
if __name__ == '__main__':
    #b24 = B24(id)
    #b24.msg('test2')
    quit()

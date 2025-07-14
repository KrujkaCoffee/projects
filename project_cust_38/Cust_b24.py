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

    def get_chat_id_by_action(self, action: str):
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

    def send_msg_by_action(self, action: str, msg: str) -> bool:
        chat_id = self.get_chat_id_by_action(action)
        if chat_id:
            return self.send_msg_by_chat_id(chat_id, msg)
        logging.error('[b24-chat]Ошибка отправки сообщения')

    def send_msg_by_chat_id(self, chat_id: str, msg: str) -> bool:
        return True
        response = requests.post(f'{self._URL}im.message.add', json={
            'DIALOG_ID': chat_id,
            'MESSAGE': msg,
        }, verify=False)
        return response.ok

    def send_msg_table(self, lst_of_lists: list[list], chat_id: str, title: str = ''):
        if title:
            title = f'[B]{title}[/B]'
        column_widths = [max(len(str(item)) for item in column) for column in zip(*lst_of_lists)]
        msg = []
        header_length = len(lst_of_lists[0])
        lengths = {}
        for idx_col in range(header_length):
            max_length = 0
            for article in lst_of_lists:
                length = len(str(article[idx_col]))
                max_length = length if length > max_length else max_length
            lengths[idx_col] = max_length
        for idx_row, row in enumerate(lst_of_lists):
            msg.append('|'.join(
                str(col) + (' ' * (lengths[idx] - len(str(col)))) for idx, col in enumerate(row)
            ))
        user = F.user_full_namre()
        msg.insert(0, title)
        return self.send_msg_by_chat_id(chat_id, '\n'.join(msg))

# https://bitrix24.kelast.ru/online/?IM_DIALOG=chat41228
if __name__ == '__main__':
    #b24 = B24(id)
    #b24.msg('test2')
    quit()

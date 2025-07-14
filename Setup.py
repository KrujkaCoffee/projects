import os

from docxtpl import DocxTemplate, RichText
from project_cust_38 import Cust_Functions as F



# TBL_INPUT = Table_data()
# TBL_INPUT.append_column_desc(name='name', header='Имя', hidden=True, editable=False, unique=True)
# TBL_INPUT.append_column_desc(name='header', header='Параметр', hidden=False, editable=False, width=300)
# TBL_INPUT.append_column_desc(name='dimension', header='Ед.изм', hidden=False, editable=False)
# TBL_INPUT.append_column_desc(name='val', header='Значение', hidden=False, editable=True, width=130)
#
# TBL_OUTPUT_ERR = Table_data()
# TBL_OUTPUT_ERR.append_column_desc(name='name', header='№', hidden=False, editable=False, width=50, unique=True)
# TBL_OUTPUT_ERR.append_column_desc(name='header', header='Параметр', hidden=False, editable=False, width=300)
# TBL_OUTPUT_ERR.append_column_desc(name='val', header='Значение', hidden=False, editable=False, width=130)
# TBL_OUTPUT_ERR.append_column_desc(name='err', header='Ошибка', hidden=False, editable=False, width=300)
#
# TBL_OUTPUT = Table_data()
# TBL_OUTPUT.append_column_desc(name='name', header='Имя', hidden=True, editable=False, unique=True)
# TBL_OUTPUT.append_column_desc(name='header', header='Параметр', hidden=False, editable=False, width=300)
# TBL_OUTPUT.append_column_desc(name='val', header='Значение', hidden=False, editable=False, width=130)
# TBL_OUTPUT.append_column_desc(name='dimension', header='Ед.изм', hidden=False, editable=False)
# TBL_OUTPUT.append_column_desc(name='comment', header='Примечание', hidden=False, editable=False, width=500)

def prepare_docx_data(data, bold_header: bool):
    if len(data) == 0:
        return
    if isinstance(data[0], dict):
        list_of_lists = F.list_of_dicts_to_list_of_lists(data)
    list_of_lists[0] = [
        RichText(head, bold=bold_header)
        for head in data[0]
    ]
    return list_of_lists


def make_docx_report(
        # Данные
        report_name: str,
        input_rows: list[dict],
        output_rows: list[dict],
        input_capture: str = 'Исходные данные',
        output_capture: str = 'Расчётные данные',
        # Настройки оформления
        bold_input_headers: bool = True,
        bold_input_capture: bool = True,
        bold_output_headers: bool = True,
        bold_output_capture: bool = True,
        # Пути используемых файлов
        template_name: str = "report.docx",
        output_docx_path: str = "output.docx"
):
    doc = DocxTemplate(template_name)
    output_data = prepare_data(output_rows, bold_output_headers)
    input_data = prepare_data(input_rows, bold_input_headers)
    data = {
        'report_name': report_name,
        'input': input_data,
        'i_capture': RichText(input_capture, bold=bold_input_capture),
        'i_len': len(input_data[0]),
        'output': output_data,
        'o_capture': RichText(output_capture, bold=bold_output_capture),
        'o_len': len(output_data[0]),
    }
    doc.render(data)
    doc.save(output_docx_path)
    return output_docx_path

if __name__ == '__main__':
    # doc = DocxTemplate('test_template.docx')
    # output_data = [            {'test_key': 'qweqwe', 'test_key2': 'asdasd'},
    #                            {'test_key': 'qweqwe44', u'test_key2': 'asdasd66'},
    #                            {'test_key': 'qweqwe55', 'test_key2': 'asdasd77'}]
    # converted_output_data = F.list_of_dicts_to_list_of_lists(output_data)
    # if len(converted_output_data) > 1:
    #     converted_output_data[0] = [RichText(head, bold=True) for head in converted_output_data[0]]
    #
    # data = {
    #     'output_rows': converted_output_data
    # }
    # doc.render(data)
    # doc.save('test.docx')
    # os.startfile('test.docx')
    make_docx_report(
        report_name='Тест тестович',
        input_rows=[                                                # Исходные данные
            {'header': 'qwe', 'dimension': 'м', 'val': '233'},
            {'header': 'qwe', 'dimension': 'м', 'val': '233'},
            {'header': 'qwe', 'dimension': 'м', 'val': '233'},
        ],
        output_rows=[                                               # Расчётные данные
            {'header': 'Ширина', 'dimension': 'м', 'val': '233', 'comment': '123123'},
            {'header': 'Ширина', 'dimension': 'м', 'val': '233', 'comment': '123123'},
            {'header': 'Ширина', 'dimension': 'м', 'val': '233', 'comment': '123123'},
        ]
    )

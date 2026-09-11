import typing
import dataclasses

from PyQt5 import QtWidgets, QtCore

from project_cust_38.sub_mes.resource_planning import catalog_link as CL
from project_cust_38.sub_mes.resource_planning import attribute_binding as AB
from project_cust_38.sub_mes.resource_planning import catalog_choices as CC

class CatalogEndpointEditor(QtWidgets.QGroupBox):
    selection_changed = QtCore.pyqtSignal()

    def __init__(
            self,
            title: str,
            choices: typing.Iterable[CC.CatalogFieldChoice],
            parent=None
    ):
        super().__init__(title, parent)

        self.__choices = tuple(choices) # todo валидацию

        self.cmb_provider = QtWidgets.QComboBox(self)
        self.cmb_source = QtWidgets.QComboBox(self)
        self.cmb_entity = QtWidgets.QComboBox(self)
        self.cmb_field = QtWidgets.QComboBox(self)

        layout = QtWidgets.QFormLayout(self)
        layout.addRow('Тип источника', self.cmb_provider)
        layout.addRow('Источник', self.cmb_source)
        layout.addRow('Справочник', self.cmb_entity)
        layout.addRow('Поле', self.cmb_field)

        self.cmb_provider.currentIndexChanged.connect(self.__reload_sources)
        self.cmb_source.currentIndexChanged.connect(self.__reload_entities)
        self.cmb_entity.currentIndexChanged.connect(self.__reload_fields)
        self.cmb_field.currentIndexChanged.connect(self.selection_changed.emit)
        self.__reload_providers()

    def current_endpoint(self) -> CL.CatalogLinkEndpoint | None:
        choice = self.cmb_field.currentData()
        if not isinstance(choice, CC.CatalogFieldChoice):
            return None
        return choice.endpoint

    def set_endpoint(self, endpoint: CL.CatalogLinkEndpoint) -> bool:
        if not self.set_provider(endpoint.provider):
            combos = (
                (self.cmb_source, endpoint.source_key),
                (self.cmb_entity, endpoint.entity_key),
            )
            for combobox, value in combos:
                index = combobox.findData(value)
                combobox.setCurrentIndex(index)
                if index < 0:
                    return False
            for index in range(self.cmb_field.count()):
                choice: CC.CatalogFieldChoice = self.cmb_field.itemData(index)
                if choice.endpoint.lookup_key == endpoint.lookup_key:
                    self.cmb_field.setCurrentIndex(index)
                    return True

        self.cmb_field.setCurrentIndex(-1)
        return False

    def set_provider(self, provider: AB.SourceProvider) -> bool:
        try:
            provider = AB.SourceProvider(provider)
        except Exception:
            return False
        index = self.cmb_provider.findData(provider)
        if index < 0:
            return False
        self.cmb_provider.setCurrentIndex(index)
        return True

    def __reload_providers(self):
        providers = []
        seen = set()

        for choice in self.__choices:
            provider = choice.endpoint.provider
            if provider in seen:
                continue
            seen.add(provider)
            providers.append((
                provider,
                provider
            ))
        self.__set_items(self.cmb_provider, providers)
        self.__reload_sources()

    def __reload_sources(self):
        provider = self.cmb_provider.currentData()
        sources = []
        seen = set()

        for choice in self.__choices:
            endpoint = choice.endpoint
            if endpoint.provider != provider:
                continue
            if endpoint.source_key in seen:
                continue
            seen.add(endpoint.source_key)
            sources.append((
                choice.source_text,
                endpoint.source_key
            ))
        self.__set_items(self.cmb_source, sources)
        self.__reload_entities()

    def __reload_entities(self):
        provider = self.cmb_provider.currentData()
        source_key = self.cmb_source.currentData()
        entities = []
        seen = set()

        for choice in self.__choices:
            endpoint = choice.endpoint
            if endpoint.provider != provider:
                continue
            if endpoint.source_key != source_key:
                continue
            if endpoint.entity_key in seen:
                continue
            seen.add(endpoint.entity_key)
            entities.append((
                choice.entity_text,
                endpoint.entity_key
            ))
        self.__set_items(self.cmb_entity, entities)
        self.__reload_fields()

    def __set_items(self, combobox, items: list[tuple[str, str]]):
        previous_data = combobox.currentData()
        with QtCore.QSignalBlocker(combobox):
            combobox.clear()

            for text, data in items:
                combobox.addItem(text, data)
            previous_index = combobox.findData(previous_data)
            if previous_index >= 0:
                combobox.setCurrentIndex(previous_index)

    def __reload_fields(self):
        provider = self.cmb_provider.currentData()
        source_key = self.cmb_source.currentData()
        entity_key = self.cmb_entity.currentData()
        fields = []

        for choice in self.__choices:
            endpoint = choice.endpoint
            if endpoint.provider != provider:
                continue
            if endpoint.source_key != source_key:
                continue
            if endpoint.entity_key != entity_key:
                continue
            fields.append((endpoint.display_name, choice))
        self.__set_items(self.cmb_field, fields)
        self.selection_changed.emit()

class CatalogLinkEditor(QtWidgets.QDialog):
    def __init__(
            self,
            choices: typing.Iterable[CC.CatalogFieldChoice],
            parent=None,
            *,
            link_spec: CL.CatalogLinkSpec
    ):
        super().__init__(parent)

        choices = tuple(choices)
        self.__link_spec = None
        self.__original_link = link_spec


        self.resize(920, 330)
        self.setWindowTitle('Связь между справочниками')

        self.left_editor = CatalogEndpointEditor(
            'Откуда берем значение',
            choices,
            self
        )
        self.right_editor = CatalogEndpointEditor(
            'Где ищем значение',
            choices,
            self
        )

        arrow = QtWidgets.QLabel('->')
        arrow.setAlignment(QtCore.Qt.AlignCenter)
        arrow.setStyleSheet('font-size: 28px;')

        endpoints_layout = QtWidgets.QHBoxLayout()
        endpoints_layout.addWidget(self.left_editor)
        endpoints_layout.addWidget(arrow)
        endpoints_layout.addWidget(self.right_editor)

        # todo
        relations = (
            ('Многие -> к одному', CL.CatalogLinkCardinality.MANY_TO_ONE),
            ('Один -> к одному', CL.CatalogLinkCardinality.ONE_TO_ONE),
        )
        self.cmb_cardinality = QtWidgets.QComboBox()

        for cap, data in relations:
            self.cmb_cardinality.addItem(cap, data)

        self.edt_caption = QtWidgets.QLineEdit()
        self.edt_caption.setPlaceholderText('Наименование связи...')
        options_layout = QtWidgets.QFormLayout()
        options_layout.addRow('Связи',
                              QtWidgets.QLabel('Левое поле = правое поле'))
        options_layout.addRow('Соотношение', self.cmb_cardinality)
        options_layout.addRow('Название', self.edt_caption)

        self.lbl_preview = QtWidgets.QLabel()
        self.lbl_preview.setWordWrap(True)

        self.lbl_error = QtWidgets.QLabel()
        self.lbl_error.setWordWrap(True)
        self.lbl_error.setStyleSheet('color: #b00020')

        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save
            | QtWidgets.QDialogButtonBox.Cancel
        )
        self.btn_save = self.buttons.button(QtWidgets.QDialogButtonBox.Save)
        self.btn_save.setText('Сформировать связь')
        self.buttons.button(QtWidgets.QDialogButtonBox.Cancel).setText('Отмена')

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addLayout(endpoints_layout)
        main_layout.addLayout(options_layout)
        main_layout.addWidget(self.lbl_preview)
        main_layout.addWidget(self.lbl_error)
        main_layout.addWidget(self.buttons)

        self.left_editor.selection_changed.connect(self.__refresh_state)
        self.right_editor.selection_changed.connect(self.__refresh_state)
        self.buttons.accepted.connect(self.__accept_link)
        self.buttons.rejected.connect(self.reject)
        # self.__select_initial_providers()
        self.cmb_cardinality.currentIndexChanged.connect(self.__refresh_state)
        if self.__original_link is None:
            self.__select_initial_providers()
        else:
            self.setWindowTitle('Редактирование связи справочников')
            self.btn_save.setText('Сохранить изменения')
            self.__restore_link

        self.__refresh_state()

    def __restore_link(self):
        link = self.__original_link

        self.left_editor.set_endpoint(link.left)
        self.right_editor.set_endpoint(link.right)
        self.edt_caption.setText(link.caption)

        self.cmb_cardinality.setCurrentIndex(self.cmb_cardinality.findData(link.cardinality))

    def build_spec(self) -> CL.CatalogLinkSpec:
        error = self.__selection_error()
        if error:
            raise ValueError(error)
        left = self.left_editor.current_endpoint()
        right = self.right_editor.current_endpoint()
        caption = self.edt_caption.text()
        cardinality = self.cmb_cardinality.currentData()

        if self.__original_link is not None:
            return dataclasses.replace(
                self.__original_link,
                left=left,
                right=right,
                caption=caption,
            )
        manager = CL.CatalogLinkManager()
        return manager.create(
            left,
            right,
            caption=caption,
            cardinality=cardinality,
        )

    @property
    def link_spec(self) -> CL.CatalogLinkSpec | None:
        return self.__link_spec

    def build_spec(self) -> CL.CatalogLinkSpec:
        error = self.__selection_error()
        if error:
            raise ValueError(error)
        manager = CL.CatalogLinkManager()
        return manager.create(
            self.left_editor.current_endpoint(),
            self.right_editor.current_endpoint(),
            caption=self.edt_caption.text(),
            cardinality=self.cmb_cardinality.currentData(),
        )

    def __select_initial_providers(self) -> None:
        self.left_editor.set_provider(AB.SourceProvider.MES)
        self.right_editor.set_provider(AB.SourceProvider.ERP)

    def __accept_link(self):
        try:
            self.__link_spec = self.build_spec()
        except Exception as error:
            self.lbl_error.setText(str(error))
            return
        self.accept()

    def __refresh_state(self):
        left = self.left_editor.current_endpoint()
        right = self.right_editor.current_endpoint()
        error = self.__selection_error()
        self.lbl_preview.setText(f'{self.__endpoint_text(left)} -> {self.__endpoint_text(right)}')
        self.lbl_error.setText(error)
        self.btn_save.setEnabled(not error)

    def __selection_error(self):
        left = self.left_editor.current_endpoint()
        right = self.right_editor.current_endpoint()
        if left is None or right is None:
            return 'Выберите оба поля связи'
        if left.catalog_key == right.catalog_key:
            return 'Выбраны одинаковые левый и правой справочник'
        if self.cmb_cardinality.currentData() is None:
            return 'Выберите соотношение'
        return ''

    def __endpoint_text(self, endpoint: CL.CatalogLinkEndpoint) -> str:
        if endpoint is None:
            return 'не выбрано'
        return ' / '.join((
            endpoint.provider,
            endpoint.source_key,
            endpoint.entity_key,
            endpoint.display_name
        ))

if __name__ == '__main__':
    import sys

    def demo():
        return (
            CC.CatalogFieldChoice(
                CL.CatalogLinkEndpoint(
                provider=AB.SourceProvider.MES,
                source_key='План',
                entity_key='знпр',
                field_key='client_order_Key',
                caption='Ссылка на заказ клиента'
            ),
                source_caption='Планировщик мес',
                entity_caption='План'
            ),
            CC.CatalogFieldChoice(
                CL.CatalogLinkEndpoint(
                provider=AB.SourceProvider.MES,
                source_key='План',
                entity_key='знпр',
                field_key='Ref_Key_py',
                caption='Ссылка на заказ на производство'
            ),
                source_caption='Планировщик мес',
                entity_caption='План'
            ),
            CC.CatalogFieldChoice(
                CL.CatalogLinkEndpoint(
                provider=AB.SourceProvider.MES,
                source_key='План',
                entity_key='plan',
                field_key='znvp_order_Key',
                caption='Ссылка на заказ клиента'
            ),
                source_caption='Планировщик мес',
                entity_caption='План'
            ),
            CC.CatalogFieldChoice(
                CL.CatalogLinkEndpoint(
                provider=AB.SourceProvider.ERP,
                source_key='Документ.ЗаказКлиента',
                entity_key='ЗаказКлиента',
                field_key='Ссылка',
                caption='Ссылка на заказ клиента'
            ),
                source_caption='ERP',
                entity_caption='Заказ клиента'
            ),
            CC.CatalogFieldChoice(
                CL.CatalogLinkEndpoint(
                provider=AB.SourceProvider.ERP,
                source_key='Документ.ЗаказНаПроизводство2_2',
                entity_key='ЗаказНаПроизводство2_2',
                field_key='Ссылка',
                caption='Ссылка на заказ на производство'
            ),
                source_caption='ERP',
                entity_caption='Заказ на производство'
            ),
            CC.CatalogFieldChoice(
                CL.CatalogLinkEndpoint(
                provider=AB.SourceProvider.ERP,
                source_key='Документ.ЗаказНаВнутреннееПотребление',
                entity_key='ЗаказНаВнутреннееПотребление',
                field_key='Ссылка',
                caption='Заказ на внутреннее потребление'
            ),
                source_caption='УКЗ',
                entity_caption='Заказ на внутреннее потребление'
            ),
        )

    from project_cust_38 import Cust_application as CAPP
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = CAPP.SafeApplication(sys.argv)
        CAPP.install_crash_guard(app, app_name='редактор_связей', user_name='test')

    choices = demo()
    manager = CL.CatalogLinkManager()

    original = manager.create(
        choices[1].endpoint,
        choices[4].endpoint,
        link_key='demo_edit_link',
        caption='Проверка редактирования',
        cardinality=CL.CatalogLinkCardinality.ONE_TO_ONE
    )
    manager.register(original)

    dialog = CatalogLinkEditor(
        choices,
        link_spec=original
    )

    if dialog.exec() == QtWidgets.QDialog.Accepted:
        updated = dialog.link_spec

        print(
            'Ключ сохранён:',
            updated.link_key == original.link_key
        )
        print(
            'Исходный объект сохранён:',
            manager.get(original.link_key) is original
        )

        manager.replace(updated)
    else:
        print(
            'Отмена, объект сохранён:',
            manager.get(original.link_key) is original
        )

    print('Количество связей:', len(manager))
    print(
        'Название в менеджере:',
        manager.get(original.link_key).caption
    )
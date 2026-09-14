import sys
import typing

from PyQt5 import QtCore, QtWidgets

from project_cust_38.sub_mes.resource_planning import catalog_link as CL
from project_cust_38.sub_mes.resource_planning import attribute_binding as AB

class CatalogLinksDialog(QtWidgets.QDialog):
    link_removed = QtCore.pyqtSignal(str)

    def __init__(
            self,
            manager: CL.CatalogLinkManager,
            parent = None,
            *,
            edit_link: typing.Callable[[str, "CatalogLinksDialog"], CL.CatalogLinkSpec] = None
    ):
        super().__init__(parent)

        self.__manager = manager
        self.__edit_link = edit_link

        self.setWindowTitle("Связи справочников")
        self.resize(1050, 430)
        self.lbl_count = QtWidgets.QLabel(self)

        self.tbl_links = QtWidgets.QTableWidget(self)
        self.tbl_links.setColumnCount(4)
        self.tbl_links.setHorizontalHeaderLabels((
            'Название',
            'Откуда',
            'Куда',
            'Соотношение'
        ))
        self.tbl_links.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tbl_links.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tbl_links.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tbl_links.setAlternatingRowColors(True)
        self.tbl_links.verticalHeader().setVisible(False)
        header = self.tbl_links.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)

        self.btn_remove = QtWidgets.QPushButton('Удалить связь', self)
        self.btn_close = QtWidgets.QPushButton('Закрыть', self)
        self.btn_edit = QtWidgets.QPushButton('Редактировать', self)

        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.addWidget(self.btn_edit)
        buttons_layout.addWidget(self.btn_remove)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btn_close)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.lbl_count)
        layout.addWidget(self.tbl_links)
        layout.addLayout(buttons_layout)

        self.tbl_links.itemSelectionChanged.connect(self.__refresh_actions)
        self.btn_remove.clicked.connect(self.__remove_selected)
        self.btn_edit.clicked.connect(self.__edit_selected)
        self.btn_close.clicked.connect(self.accept)

        self.reload_links()

    def selected_link_key(self) -> str | None:
        selected_rows = self.tbl_links.selectionModel().selectedRows()
        if not selected_rows:
            return None
        item = self.tbl_links.item(selected_rows[0].row(), 0)
        if item is None:
            return None
        return item.date(QtCore.Qt.UserRole)

    def __edit_selected(self):
        link_key = self.selected_link_key()
        if link_key is None or self.__edit_link is None and not callable(self.__edit_link):
            return
        updated = self.__edit_link(link_key, parent=self)
        if updated is None:
            return
        self.reload_links()

        for row in range(self.tbl_links.rowCount()):
            item = self.tbl_links.item(row, 0)
            if item.data(QtCore.Qt.UserRole) == updated.link_key:
                self.tbl_links.setCurrentCell(row, 0)
                self.tbl_links.selectRow(row)
                break

    def reload_links(self):
        links = self.__manager.all()
        print(links)
        with QtCore.QSignalBlocker(self.tbl_links):
            self.tbl_links.setRowCount(len(links))
            for row, link in enumerate(links):
                name_item = QtWidgets.QTableWidgetItem(link.display_text)
                name_item.setData(QtCore.Qt.UserRole, link.link_key)
                name_item.setToolTip(f'ключ ссылки: {link.link_key}')

                left_item = QtWidgets.QTableWidgetItem(self.__endpoint_text(link.left))
                right_item = QtWidgets.QTableWidgetItem(self.__endpoint_text(link.right))
                cardinality_item = QtWidgets.QTableWidgetItem(self.__cardinality_text(link.cardinality))
                self.tbl_links.setItem(row, 0, name_item)
                self.tbl_links.setItem(row, 1, left_item)
                self.tbl_links.setItem(row, 2, right_item)
                self.tbl_links.setItem(row, 3, cardinality_item)
        self.lbl_count.setText(f'Связей: {len(links)}')
        self.__refresh_actions()

    def __remove_selected(self):
        link_key = self.selected_link_key()
        if not link_key:
            return
        link = self.__manager.get(link_key)
        if link is None:
            self.reload_links()
            return
        answer = QtWidgets.QMessageBox.question(
            self,
            'Удаление связи',
            f'Удалить связь <{link.display_text}>',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        if answer != QtWidgets.QMessageBox.Yes:
            return

        if self.__manager.remove(link_key):
            self.link_removed.emit(link_key)
        self.reload_links()

    @staticmethod
    def __endpoint_text(endpoint: CL.CatalogLinkEndpoint) -> str:
        return ' / '.join((
            str(endpoint.provider),
            endpoint.source_key,
            endpoint.entity_key,
            endpoint.display_name
        ))

    def __refresh_actions(self):
        has_selection = self.selected_link_key() is not None
        self.btn_remove.setEnabled(self.selected_link_key() is not None)
        self.btn_edit.setEnabled(has_selection and callable(self.__edit_link))

    def __cardinality_text(self, cardinality) -> str:
        return {
            CL.CatalogLinkCardinality.MANY_TO_ONE: 'Многие к одному',
            CL.CatalogLinkCardinality.ONE_TO_ONE: 'Один к одному'
        }.get(cardinality, str(cardinality))

if __name__ == '__main__':
    manager = CL.CatalogLinkManager()

    te = (
        (
            CL.CatalogLinkEndpoint(
                provider=AB.SourceProvider.MES,
                source_key='resource_planning',
                entity_key='plan',
                field_key='Пномер'
            ),
            CL.CatalogLinkEndpoint(
                provider=AB.SourceProvider.MES,
                source_key='resource_planning',
                entity_key='пл_оуп',
                field_key='НомПл'
            ),
            'План -> оп'
        ),
        (
            CL.CatalogLinkEndpoint(
                provider=AB.SourceProvider.MES,
                source_key='resource_planning',
                entity_key='пл_оуп',
                field_key='Пномер_ЗП'
            ),
            CL.CatalogLinkEndpoint(
                provider=AB.SourceProvider.MES,
                source_key='resource_planning',
                entity_key='знпр',
                field_key='s_num'
            ),
            'Операции -> заказ на производство'
        )
    )
    for left, right, caption in te:
        manager.register(manager.create(
            left,
            right,
            caption=caption
        ))

    application = QtWidgets.QApplication(sys.argv)


    dialog = CatalogLinksDialog(manager)

    dialog.exec()
    print(manager.to_list())
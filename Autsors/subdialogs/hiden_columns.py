from PyQt5 import QtWidgets, QtCore, QtGui


class CheckableComboBox(QtWidgets.QComboBox):
    def __init__(self, main_self, columns = [], on_change = None):
        super().__init__()
        self.view().pressed.connect(self.handle_item_pressed)
        self._model = QtGui.QStandardItemModel(self)
        self.setModel(self._model)
        self.all_columns = ['Скрыть поля']
        # self.all_columns.extend([i.replace('\n', '') for i in settings.TABLE_COLUMNS.keys()])
        self.all_columns.extend(columns)
        self.main_self = main_self
        hidden_columns = self.get_hidden_columns()


        for i in self.all_columns:
            item = QtGui.QStandardItem()
            item.setText(i)
            if not i in hidden_columns:
                item.setCheckState(QtCore.Qt.CheckState.Checked)
            else:
                item.setCheckState(QtCore.Qt.CheckState.Unchecked)
            self._model.appendRow(item)
        self.on_change = on_change
        self.is_view = False

    def showPopup(self):
        self.is_view = True
        super().showPopup()

    def hidePopup(self): ...

    def mousePressEvent(self, event):

        if self.geometry().contains(event.globalPos()):
            super().hidePopup()
        super().mousePressEvent(event)


    def get_hidden_columns(self):
        settings = QtCore.QSettings('outsource')
        hidden_columns = settings.value('HIDDEN_COLUMNS')
        if not hidden_columns:
            hidden_columns = []
        return hidden_columns

    def set_hidden_columns(self, hidden_columns):
        settings = QtCore.QSettings('outsource')
        settings.setValue('HIDDEN_COLUMNS', hidden_columns)

    def handle_item_pressed(self, index):
        print(self.is_view)
        item = self.model().itemFromIndex(index)
        hidden_columns = self.get_hidden_columns()
        colunm_name = index.data()

        if item.checkState() == QtCore.Qt.CheckState.Checked:
            item.setCheckState(QtCore.Qt.CheckState.Unchecked)
            hidden_columns.append(colunm_name)
        else:
            item.setCheckState(QtCore.Qt.CheckState.Checked)
            if colunm_name in hidden_columns:
                hidden_columns.remove(colunm_name)
        self.set_hidden_columns(hidden_columns)
        if callable(self.on_change):
            self.on_change(hidden_columns)
        return

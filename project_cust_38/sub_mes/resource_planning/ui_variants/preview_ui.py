from pathlib import Path
from PyQt5 import QtCore, QtWidgets, uic

VARIANTS = ('resource', 'event', 'relations')
CAPTIONS = ('От ресурса', 'От события', 'Три сущности рядом')


class Ui_mainWindow:
    def __init__(self, variant='event'):
        self._initial_variant = variant

    def setupUi(self, window):
        path = Path(__file__).resolve().parent / f'main_{self._initial_variant}.ui'
        form_type, _ = uic.loadUiType(str(path))
        form = form_type()
        form.setupUi(window)
        self.__dict__.update(vars(form))
        self._form = form
        self._layout_controller = LayoutController(window, self, self._initial_variant)

    def retranslateUi(self, window):
        self._form.retranslateUi(window)


class LayoutController(QtCore.QObject):
    def __init__(self, window, ui, variant):
        super().__init__(window)
        self.window = window
        self.ui = ui
        self.variant = variant
        self._user_changed = False
        self.apply(variant)
        ui.cmb_preview_layout.currentIndexChanged.connect(self.choose)
        ui.btn_preview_reset.clicked.connect(self.reset_sizes)
        self._initial_geometry = QtCore.QTimer(self)
        self._initial_geometry.setSingleShot(True)
        self._initial_geometry.timeout.connect(self._finish_initial_geometry)
        self._initial_geometry.start(350)

    def _finish_initial_geometry(self):
        if not self._user_changed:
            self.reset_sizes()

    def choose(self, index):
        if 0 <= index < len(VARIANTS):
            self._user_changed = True
            self.apply(VARIANTS[index])

    def apply(self, variant):
        if variant not in VARIANTS:
            raise ValueError(variant)
        ui = self.ui
        focus = QtWidgets.QApplication.focusWidget()
        enabled = self.window.updatesEnabled()
        self.window.setUpdatesEnabled(False)
        try:
            for panel in (ui.fr_resources, ui.fr_events, ui.fr_cross):
                panel.setParent(ui.fr_work)
            ui.splitter.setParent(ui.fr_work)
            if variant == 'event':
                leading, secondary = ui.fr_events, ui.fr_resources
            else:
                leading, secondary = ui.fr_resources, ui.fr_events
            ui.splitter_2.setOrientation(QtCore.Qt.Horizontal)
            ui.splitter.setOrientation(
                QtCore.Qt.Horizontal if variant == 'relations' else QtCore.Qt.Vertical
            )
            ui.splitter_2.addWidget(leading)
            ui.splitter_2.addWidget(ui.splitter)
            ui.splitter.addWidget(ui.fr_cross)
            ui.splitter.addWidget(secondary)
            for widget in (leading, ui.splitter, ui.fr_cross, secondary):
                widget.show()
            self.variant = variant
            old = ui.cmb_preview_layout.blockSignals(True)
            ui.cmb_preview_layout.setCurrentIndex(VARIANTS.index(variant))
            ui.cmb_preview_layout.blockSignals(old)
            self.reset_sizes()
            if focus is not None and self.window.isAncestorOf(focus):
                focus.setFocus(QtCore.Qt.OtherFocusReason)
        finally:
            self.window.setUpdatesEnabled(enabled)

    def reset_sizes(self, _checked=False):
        ui = self.ui
        outer = max(ui.splitter_2.width(), 900)
        if self.variant == 'relations':
            ui.splitter_2.setSizes([int(outer * .30), int(outer * .70)])
            ui.splitter.setSizes([520, 360])
        else:
            ui.splitter_2.setSizes([int(outer * .36), int(outer * .64)])
            height = max(ui.splitter.height(), 420)
            ui.splitter.setSizes([int(height * .57), int(height * .43)])
        ui.splitter_3.setSizes([260, 900])
        self.window.resizeDocks([ui.dck_info], [300], QtCore.Qt.Horizontal)
        self.window.resizeDocks([ui.dckGraph], [270], QtCore.Qt.Vertical)


class DemoWindow(QtWidgets.QMainWindow):
    def __init__(self, variant='resource'):
        super().__init__()
        self.ui = Ui_mainWindow(variant)
        self.ui.setupUi(self)
        u = self.ui
        self.setWindowTitle('resource_planning — примерка Qt / демонстрационные данные')
        u.lbl_preview_mode.setText('ДЕМО · без подключения к MES')
        u.cmb_select_sbjpl.addItem('Рабочее место')
        u.cmb_select_sbjpl.addItem('Шеф-инженер (демо не заполнено)')
        u.cmb_type_gr.addItem('Таблица участий — демо')
        u.fr_settings.hide()
        u.btn_shab_extit.hide()
        u.fr_cont_res.show()
        u.fr_cont_event.show()
        for n in ('fr_orn_g_l','fr_orn_g_r','fr_orn_vl','fr_orn_vr'):
            getattr(u, n).hide()
        self.resources = [
            ['1', 'Сборочный пост № 1', 'Рабочее место'],
            ['2', 'Сборочный пост № 2', 'Рабочее место'],
            ['3', 'Сварочный пост', 'Рабочее место'],
        ]
        self.events = [
            ['1', 'Сборка узла А', '21.09.2026', '25.09.2026'],
            ['2', 'Сборка узла Б', '23.09.2026', '25.09.2026'],
            ['3', 'Сварка корпуса', '21.09.2026', '24.09.2026'],
            ['4', 'Сборка узла В', '22.09.2026', '25.09.2026'],
        ]
        self.crosses = [
            ['1', '1', '1', '21.09.2026', '23.09.2026'],
            ['2', '2', '1', '23.09.2026', '25.09.2026'],
            ['3', '1', '2', '23.09.2026', '25.09.2026'],
            ['4', '3', '3', '21.09.2026', '24.09.2026'],
        ]
        self.fill(u.tbl_resuorces, ['№', 'Название', 'Шаблон'], self.resources)
        self.fill(u.tbl_events, ['№', 'Название', 'Начало', 'Конец'], self.events)
        self._visible_crosses = self.crosses[:]
        self.show_crosses()
        all_rows = self.cross_rows(self.crosses)
        self.fill(u.tbl_gr, ['№', 'Ресурс', 'Событие', 'С', 'По'], all_rows)
        u.tbl_gr_v_sub.hide()
        for table, columns in [(u.tbl_resuorces_filtr,3),(u.tbl_events_filtr,4),(u.tbl_cross_filtr,5)]:
            self.fill(table, [''] * columns, [[''] * columns])
            table.horizontalHeader().hide()
            table.setToolTip('В режиме MES здесь работают штатные фильтры.')
        u.tbl_resuorces.itemClicked.connect(lambda item:self.select_resource(item.row()))
        u.tbl_events.itemClicked.connect(lambda item:self.select_event(item.row()))
        u.tbl_cross.itemClicked.connect(lambda item:self.show_cross_info(item.row()))
        u.btn_cross_show_all.clicked.connect(self.show_all)
        u.btn_shab_res.clicked.connect(lambda:self.templates('ресурсов'))
        u.btn_shab_eve.clicked.connect(lambda:self.templates('событий'))
        u.btn_shab_extit.clicked.connect(self.leave_templates)
        self.statusBar().showMessage('Демо: выбор строк, фильтрация участий, свойства и переключение компоновок.')
        self.select_resource(0)

    @staticmethod
    def fill(table, headers, rows):
        table.clear()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(rows))
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        table.verticalHeader().hide()
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                table.setItem(r,c,QtWidgets.QTableWidgetItem(str(value)))
        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setDefaultSectionSize(30)

    def cross_rows(self, rows):
        rs={r[0]:r[1] for r in self.resources}
        es={e[0]:e[1] for e in self.events}
        return [[c[0],rs[c[1]],es[c[2]],c[3],c[4]] for c in rows]

    def show_crosses(self):
        self.fill(self.ui.tbl_cross,['№','Ресурс','Событие','С','По'],self.cross_rows(self._visible_crosses))

    def select_resource(self, row):
        item=self.resources[row]
        self._visible_crosses=[c for c in self.crosses if c[1]==item[0]]
        self.show_crosses()
        self.ui.tbl_resuorces.selectRow(row)
        self.info([['Сущность','Ресурс'],['Название',item[1]],['Шаблон',item[2]]])

    def select_event(self, row):
        item=self.events[row]
        self._visible_crosses=[c for c in self.crosses if c[2]==item[0]]
        self.show_crosses()
        self.info([['Сущность','Событие'],['Название',item[1]],['Начало',item[2]],['Конец',item[3]]])

    def show_cross_info(self, row):
        c=self._visible_crosses[row]
        e=next(e for e in self.events if e[0]==c[2])
        r=next(r for r in self.resources if r[0]==c[1])
        self.info([['Сущность','Участие'],['№',c[0]],['Ресурс',r[1]],['Событие',e[1]],
                   ['Начало события',e[2]],['Конец события',e[3]],['С — участие',c[3]],['По — участие',c[4]]])

    def info(self, rows):
        self.fill(self.ui.tbl_info,['Свойство','Значение'],rows)

    def show_all(self):
        self._visible_crosses=self.crosses[:]
        self.show_crosses()

    def templates(self, kind):
        self.ui.fr_work.hide()
        self.ui.fr_settings.show()
        self.ui.btn_shab_extit.show()
        self.ui.label.setText('Шаблоны '+kind)
        self.fill(self.ui.tbl_s_list_shabl,['№','Название'],[['1','Рабочее место' if kind=='ресурсов' else 'Производственная работа']])

    def leave_templates(self):
        self.ui.fr_settings.hide()
        self.ui.fr_work.show()
        self.ui.btn_shab_extit.hide()

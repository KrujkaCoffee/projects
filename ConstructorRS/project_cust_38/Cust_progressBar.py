from PyQt5 import QtWidgets, QtCore
from collections import namedtuple


class LoadingBar(QtWidgets.QDialog):
    def __init__(self, stylesheets=None):
        super().__init__()
        self.setWindowTitle('Загрузка...')
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.ui = self
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setAlignment(QtCore.Qt.AlignCenter)
        self.setFixedSize(800, 150)

        self.label = QtWidgets.QLabel()
        self.label.setWordWrap(True)
        self.label.setFixedWidth(self.progress_bar.width())
        font = self.label.font()
        font.setPointSize(12)
        font.setItalic(True)
        self.label.setFont(font)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.progress_bar, 1, QtCore.Qt.AlignVCenter)
        self.layout.addWidget(self.label, 1, QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(self.layout)
        QtWidgets.QApplication.processEvents()
        if stylesheets:
            self.setStyleSheet(stylesheets)
        self.setStyleSheet(self.styleSheet() + """
            QLabel {
                    border-width: 0px;
            }""")

def progress_decorator(fn):
    """
    При старте обернутой функции появляется окно загрузки
    Функции передается в аргумент объект hook_prog_bar с тремя методами
    * open открыть окно
    * close закрыть окно
    * set назначить новое состояние загрузки
    * text назначить сообщение под шкалой загрузки
    """
    Hook = namedtuple('Hook', 'open,close,set,text')
    parent: QtWidgets.QMainWindow | None = None
    loading_bar: LoadingBar | None = None
    stylesheets = None
    hook_prog_bar: Hook | None = None

    def run_func(*args, **kwargs):
        if parent:
            parent.hide()
        try:
            result = fn(*args, **kwargs, hook_prog_bar=hook_prog_bar)
        except TypeError as e:
            if e.args and "got an unexpected keyword argument 'hook_prog_bar'" in e.args[0]:
                result = fn(*args, **kwargs)
            else:
                raise e
        if parent:
            parent.setHidden(False)
        return result

    def ui_loader(fn):
        def wrap(*args, **kwargs):
            fn(*args, **kwargs)
            QtWidgets.QApplication.processEvents()

        return wrap

    def startLoading(*args, **kwargs):
        nonlocal loading_bar, hook_prog_bar, parent, stylesheets
        from PyQt5 import QtWidgets
        last_window = (
            QtWidgets.QApplication.activeModalWidget() or
            QtWidgets.QApplication.activePopupWidget() or
            QtWidgets.QApplication.activeWindow()
        )

        if not parent and last_window:
            parent = last_window
            stylesheets = parent.styleSheet()

        loading_bar = LoadingBar(stylesheets)
        loading_bar.show()
        hook_prog_bar = Hook(
            ui_loader(loading_bar.show),
            ui_loader(loading_bar.hide),
            ui_loader(loading_bar.progress_bar.setValue),
            ui_loader(loading_bar.label.setText)
        )
        result = run_func(*args, **kwargs)
        loading_bar.hide()
        return result

    def wrap(*args, **kwargs):
        return startLoading(*args, **kwargs)

    return wrap
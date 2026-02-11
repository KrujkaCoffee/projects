from PyQt5.QtCore import (QCoreApplication, QEventLoop, QObject, QPointF, Qt,
                       QUrl, pyqtSlot)
from PyQt5.QtGui import QKeySequence, QPainter
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter, QPrintPreviewDialog
from PyQt5.QtWebEngineWidgets import QWebEnginePage, QWebEngineView
from PyQt5.QtWidgets import QApplication, QDialog, QLabel, QProgressBar, QProgressDialog, QShortcut


class PrintHandler(QObject):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.m_page = None
        self.m_inPrintPreview = False

    def setPage(self, page):
        assert not self.m_page
        self.m_page = page
        self.m_page.printRequested.connect(self.printPreview)

    @pyqtSlot()
    def print(self):
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self.m_page.view())
        if dialog.exec_() != QDialog.Accepted:
            return
        self.printDocument(printer)

    @pyqtSlot()
    def printPreview(self):
        if not self.m_page:
            return
        if self.m_inPrintPreview:
            return
        self.m_inPrintPreview = True
        printer = QPrinter()
        preview = QPrintPreviewDialog(printer, self.m_page.view())
        preview.paintRequested.connect(self.printDocument)
        preview.exec()
        self.m_inPrintPreview = False

    @pyqtSlot(QPrinter)
    def printDocument(self, printer):
        loop = QEventLoop()
        result = False

        def printPreview(success):
            nonlocal result
            result = success
            loop.quit()
        progressbar = QProgressDialog(self.m_page.view())
        progressbar.findChild(QProgressBar).setTextVisible(False)
        progressbar.setLabelText("Wait please...")
        progressbar.setRange(0, 0)
        progressbar.show()
        progressbar.canceled.connect(loop.quit)
        self.m_page.print(printer, printPreview)
        loop.exec_()
        progressbar.close()
        if not result:
            painter = QPainter()
            if painter.begin(printer):
                font = painter.font()
                font.setPixelSize(20)
                painter.setFont(font)
                painter.drawText(QPointF(10, 25), "Could not generate print preview.")
                painter.end()

def print_grafic(browser):
    handler = PrintHandler()
    handler.setPage(browser.page())
    handler.printPreview()

"""def main():
    import sys

    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    app.setApplicationName("Previewer")

    view = QWebEngineView()
    view.setUrl(QUrl("https://stackoverflow.com/questions/59438021"))
    view.resize(1024, 750)
    view.show()

    handler = PrintHandler()
    handler.setPage(view.page())

    printPreviewShortCut = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_P), view)
    printShortCut = QShortcut(QKeySequence(Qt.CTRL + Qt.SHIFT + Qt.Key_P), view)

    printPreviewShortCut.activated.connect(handler.printPreview)
    printShortCut.activated.connect(handler.print)

    sys.exit(app.exec_())"""


if __name__ == "__main__":
    main()
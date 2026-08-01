from PyQt5 import QtCore, QtGui, QtWidgets
import cv2
import numpy as np
#29.07.2026
"""
   Полупрозрачный overlay-виджет с эффектом размытия содержимого под ним.

   Используется для визуального затемнения области интерфейса:
   - делает снимок целевого QWidget;
   - при необходимости применяет Gaussian Blur;
   - накладывает полупрозрачный цвет;
   - отображает результат поверх исходного виджета.

   Overlay создается поверх окна, поэтому не зависит от вложенности
   целевого виджета (centralWidget, layout, QTabWidget и т.п.).

   Взаимодействие с мышью:
       - interactive=False:
           события мыши проходят сквозь overlay к исходному виджету;
       - interactive=True:
           overlay перехватывает события мыши и блокирует область.

   Пример:
       overlay = BlurOverlayFrame(table)

       overlay.update_background(
           rgba=(0, 0, 0, 100),
           blur_radius=12,
       )

       overlay.show()

   Очистка:
       overlay.clear_background()
   """
class BlurOverlayFrame(QtWidgets.QFrame):

    def __init__(self, target: QtWidgets.QWidget):
        super().__init__(target.window())

        self._target = target
        self._background = None

        self.setGeometry(
            QtCore.QRect(
                self.parentWidget().mapFromGlobal(
                    target.mapToGlobal(QtCore.QPoint())
                ),
                target.size()
            )
        )

        self.raise_()

        target.installEventFilter(self)

        self.sync_geometry()

    def eventFilter(self, obj, event):
        if obj == self._target:
            if event.type() in (
                    QtCore.QEvent.Move,
                    QtCore.QEvent.Resize,
                    QtCore.QEvent.Show,
            ):
                self.sync_geometry()

        return super().eventFilter(obj, event)

    def sync_geometry(self):
        if not self._target:
            return

        parent = self.parentWidget()

        pos = parent.mapFromGlobal(
            self._target.mapToGlobal(QtCore.QPoint())
        )

        self.setGeometry(
            QtCore.QRect(
                pos,
                self._target.size()
            )
        )

    def update_background(
            self,
            rgba=(0, 0, 0, 80),
            blur_radius=10,
    ):
        window = self.parentWidget()
        if window is None:
            return

        was_visible = self.isVisible()
        self.hide()

        QtWidgets.QApplication.processEvents()

        rect = QtCore.QRect(
            window.mapFromGlobal(
                self._target.mapToGlobal(QtCore.QPoint())
            ),
            self._target.size()
        )

        self.setGeometry(rect)

        pixmap = window.grab().copy(rect)

        if blur_radius > 0:
            pixmap = self.blur_pixmap(pixmap, blur_radius)

        painter = QtGui.QPainter(pixmap)
        painter.fillRect(
            pixmap.rect(),
            QtGui.QColor(*rgba)
        )
        painter.end()

        self._background = pixmap

        if was_visible:
            self.show()

        self.raise_()
        self.update()

    def clear_background(self):
        if self._target:
            self._target.removeEventFilter(self)

        self._background = None
        self.hide()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)

        if self._background is not None:
            painter.drawPixmap(self.rect(), self._background)

        super().paintEvent(event)

    @staticmethod
    def blur_pixmap(pixmap, radius):

        image = pixmap.toImage().convertToFormat(
            QtGui.QImage.Format_RGBA8888
        )

        ptr = image.bits()
        ptr.setsize(image.byteCount())

        img = np.frombuffer(
            ptr,
            np.uint8
        ).reshape(image.height(), image.width(), 4)

        img = cv2.GaussianBlur(
            img,
            (0, 0),
            sigmaX=radius,
            sigmaY=radius,
        )

        qimg = QtGui.QImage(
            img.data,
            img.shape[1],
            img.shape[0],
            img.strides[0],
            QtGui.QImage.Format_RGBA8888
        )

        return QtGui.QPixmap.fromImage(qimg.copy())
def apply_blur(frame: QtWidgets.QWidget,
               alpha: int = 30,
               radius: int = 2,
               interactive:bool = False) -> BlurOverlayFrame:
    """
       Создает и отображает BlurOverlayFrame поверх указанного виджета.

       Args:
           frame:
               Виджет, область которого необходимо накрыть overlay.

           alpha:
               Прозрачность затемнения:
               0   - полностью прозрачный,
               255 - полностью непрозрачный.

           radius:
               Радиус размытия Gaussian Blur.
               0 - отключает размытие.

           interactive:
               Режим обработки мыши:
               False - события проходят к исходному виджету;
               True  - overlay блокирует взаимодействие.

       Returns:
           BlurOverlayFrame:
               Созданный overlay. Его необходимо сохранить,
               если потребуется последующее удаление.

       Example:
           self.overlay = apply_blur(
               self.ui.fr_events,
               alpha=90,
               radius=12,
               interactive=False,
           )

       Remove:
           self.overlay.clear_background()
           self.overlay.deleteLater()
       """
    overlay = BlurOverlayFrame(frame)

    overlay.setAttribute(
        QtCore.Qt.WA_TransparentForMouseEvents,
         interactive
    )

    overlay.update_background(
        rgba=(0, 0, 0, alpha),
        blur_radius=radius,
    )

    overlay.show()
    overlay.raise_()

    return overlay




from PyQt5.QtWidgets import QMainWindow, QApplication, QFileDialog, QLabel
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor
from PyQt5 import QtCore
class ClickLabel(QLabel):
    clicked = QtCore.pyqtSignal(QtCore.QPoint)
    released = QtCore.pyqtSignal(QtCore.QPoint)

    def mousePressEvent(self, event):
        self.clicked.emit(event.pos())
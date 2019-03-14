import sys
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QPushButton, QAction, QLineEdit, QMessageBox
from PyQt5 import uic

UI_SCREEN = "leonardo.ui"
 
 
class App(QMainWindow):
 
    def __init__(self):
        super().__init__()
        uic.loadUi(UI_SCREEN, self)
        self.title = 'Leonardo monitor using PyFirmata'
        self.show()

 
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())

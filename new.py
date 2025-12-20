from string import ascii_uppercase
from PyQt5 import QtCore, QtWidgets

class Keyboard(QtWidgets.QWidget):
    ASCII, QWERTY, DVORAK = 0, 1, 2
    KeyLayoutLetters = {
        ASCII: [ascii_uppercase[r*9:r*9+9] for r in range(3)], 
        QWERTY: ['QWERTYUIOP', 'ASDFGHJKL', 'ZXCVBNM'], 
        DVORAK: ['PYFGCRL', 'AOEUIDHTNS ', 'QJKXBMWVZ'], 
    }

    # some default special stretch set for specific keyboard layouts
    KeyStretch = {
        QWERTY: [(1, 1), (1, 1), (1, 2)], 
        DVORAK: [(2, 1), (1, 2), (3, 1)], 
    }

    keySize = 50
    spacing = 2
    letterClicked = QtCore.pyqtSignal(object)

    def __init__(self):
        super(Keyboard, self).__init__()
        self.setKeyboardLayout()

    def setKeyboardLayout(self, keyLayout=None):
        keyLayout = keyLayout if keyLayout is not None else self.ASCII
        if self.layout() is not None:
            QtWidgets.QWidget().setLayout(self.layout())
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(self.spacing)
        stretches = self.KeyStretch.get(keyLayout, [(1, 1)] * 3)
        for row, rowChars in enumerate(self.KeyLayoutLetters.get(keyLayout, self.KeyLayoutLetters[self.ASCII])):
            rowLayout = QtWidgets.QHBoxLayout()
            rowLayout.setSpacing(self.spacing)
            layout.addLayout(rowLayout)

            stretchLeft, stretchRight = stretches[row]
            rowLayout.addStretch(stretchLeft)
            for letter in rowChars:
                if not letter.strip():
                    spacer = QtWidgets.QWidget()
                    rowLayout.addWidget(spacer)
                    spacer.setFixedSize(self.keySize * .5, self.keySize)
                    continue
                letterButton = QtWidgets.QPushButton(letter)
                rowLayout.addWidget(letterButton, stretch=0)
                letterButton.setFixedSize(self.keySize, self.keySize)
                letterButton.clicked.connect(lambda _, key=letter: self.letterClicked.emit(key))
            rowLayout.addStretch(stretchRight)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        # just a QLineEdit widget to test the text intertion
        self.lineEdit = QtWidgets.QLineEdit()
        layout.addWidget(self.lineEdit)

        self.keyboard = Keyboard()
        layout.addWidget(self.keyboard)
        self.keyboard.setKeyboardLayout(Keyboard.DVORAK)
        self.keyboard.letterClicked.connect(self.lineEdit.insert)

        self.keySelector = QtWidgets.QComboBox()
        layout.addWidget(self.keySelector)
        self.keySelector.addItems(['ASCII', 'QWERTY', 'DVORAK'])
        self.keySelector.currentIndexChanged.connect(self.keyboard.setKeyboardLayout)


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    keyboard = MainWindow()
    keyboard.show()
    sys.exit(app.exec_())
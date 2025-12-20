import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt5 Main Window Example")
        self.resize(1000, 500)

        # Create a central widget (important for QMainWindow)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create widgets
        self.label = QLabel("Enter your name:")
        self.textbox = QLineEdit()
        self.button = QPushButton("Submit")
        self.output = QLabel("")

        # Connect button click to function
        self.button.clicked.connect(self.show_name)

        # Layout (vertical stack)
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.textbox)
        layout.addWidget(self.button)
        layout.addWidget(self.output)

        central_widget.setLayout(layout)

    def show_name(self):
        name = self.textbox.text()
        self.output.setText(f"Hello, {name}!")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()




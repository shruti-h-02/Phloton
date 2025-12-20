import sys
import serial
import serial.tools.list_ports
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QLabel, QPushButton, QComboBox, QMessageBox
)


class BoardTester(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Board Auto Test GUI")
        self.resize(1000, 500)

        # Serial object
        self.ser = None

        # Central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout()

        # Port selection
        self.port_label = QLabel("Select COM Port:")
        self.port_combo = QComboBox()
        self.refresh_ports()
        layout.addWidget(self.port_label)
        layout.addWidget(self.port_combo)

        # Buttons
        self.connect_button = QPushButton("Connect")
        self.start_button = QPushButton("Start Test")
        self.stop_button = QPushButton("Stop Test")

        layout.addWidget(self.connect_button)
        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)

        # Status labels
        self.status_label = QLabel("Status: Disconnected")
        self.voltage_label = QLabel("Voltage: ---")
        self.ambient_label = QLabel("Ambient: ---")
        self.coldsink_label = QLabel("Cold Sink: ---")
        self.heatsink_label = QLabel("Heat Sink: ---")
        self.flashtop_label = QLabel("Flask Top: ---")
        self.csfan_label = QLabel("CSFAN Current: ---")
        self.hsfan_label = QLabel("HSFAN Current: ---")

        layout.addWidget(self.status_label)
        layout.addWidget(self.voltage_label)
        layout.addWidget(self.ambient_label)
        layout.addWidget(self.coldsink_label)
        layout.addWidget(self.heatsink_label)
        layout.addWidget(self.flashtop_label)
        layout.addWidget(self.csfan_label)
        layout.addWidget(self.hsfan_label)

        self.central_widget.setLayout(layout)

        # Timer for updating serial data
        self.timer = QTimer()
        self.timer.timeout.connect(self.read_serial_data)

        # Connect button actions
        self.connect_button.clicked.connect(self.connect_serial)
        self.start_button.clicked.connect(self.start_test)
        self.stop_button.clicked.connect(self.stop_test)

    def refresh_ports(self):
        """Refresh available serial ports."""
        ports = serial.tools.list_ports.comports()
        self.port_combo.clear()
        for port in ports:
            self.port_combo.addItem(port.device)

    def connect_serial(self):
        """Connect to the selected COM port."""
        port_name = self.port_combo.currentText()
        try:
            self.ser = serial.Serial(port_name, 115200, timeout=1)
            self.status_label.setText(f"Status: Connected to {port_name}")
        except serial.SerialException as e:
            QMessageBox.critical(self, "Error", f"Could not open {port_name}\n{e}")

    def start_test(self):
        """Start reading data."""
        if self.ser and self.ser.is_open:
            self.timer.start(1000)  # every 1 second
            self.status_label.setText("Status: Testing...")
        else:
            QMessageBox.warning(self, "Warning", "Please connect to a board first!")

    def stop_test(self):
        """Stop reading data."""
        self.timer.stop()
        self.status_label.setText("Status: Test Stopped")

    def read_serial_data(self):
        """Read and parse serial data from the board."""
        if not self.ser or not self.ser.is_open:
            return

        try:
            line = self.ser.readline().decode("utf-8").strip()
            if line:
                # Example parsing from your code’s Serial output
                if "Ambient:" in line:
                    self.ambient_label.setText(line)
                elif "Cold Sink:" in line:
                    self.coldsink_label.setText(line)
                elif "Heat Sink:" in line:
                    self.heatsink_label.setText(line)
                elif "Flask Top:" in line:
                    self.flashtop_label.setText(line)
                elif "Current CSFAN:" in line:
                    self.csfan_label.setText(line)
                elif "Current HSFAN:" in line:
                    self.hsfan_label.setText(line)
                elif "Voltage:" in line:
                    self.voltage_label.setText(line)
        except Exception as e:
            print("Serial Read Error:", e)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BoardTester()
    window.show()
    sys.exit(app.exec_())

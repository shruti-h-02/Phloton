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
        self.setWindowTitle("Phloton Control Board - Temperature Monitor")
        self.resize(1000, 500)

        self.ser = None

        # Main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()

        # Port selector
        layout.addWidget(QLabel("Select COM Port:"))
        self.port_combo = QComboBox()
        self.refresh_ports()
        layout.addWidget(self.port_combo)

        # Buttons
        self.connect_button = QPushButton("Connect")
        self.start_button = QPushButton("Start Reading")
        self.stop_button = QPushButton("Stop Reading")

        layout.addWidget(self.connect_button)
        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)

        # Status and readings
        self.status_label = QLabel("Status: Disconnected")
        self.ambient_label = QLabel("Ambient: --- °C")
        self.coldsink_label = QLabel("Cold Sink: --- °C")
        self.heatsink_label = QLabel("Heat Sink: --- °C")
        self.flashtop_label = QLabel("Flask Top: --- °C")

        for lbl in [
            self.status_label,
            self.ambient_label,
            self.coldsink_label,
            self.heatsink_label,
            self.flashtop_label,
        ]:
            lbl.setStyleSheet("font-size: 16px;")
            layout.addWidget(lbl)

        central_widget.setLayout(layout)

        # Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.read_serial_data)

        # Button actions
        self.connect_button.clicked.connect(self.connect_serial)
        self.start_button.clicked.connect(self.start_reading)
        self.stop_button.clicked.connect(self.stop_reading)

        # Auto-refresh ports every few seconds
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_ports)
        self.refresh_timer.start(3000)

    def refresh_ports(self):
        """List available COM ports."""
        ports = serial.tools.list_ports.comports()
        current = self.port_combo.currentText()
        self.port_combo.clear()
        for port in ports:
            self.port_combo.addItem(port.device)
        # Preserve previous selection if possible
        idx = self.port_combo.findText(current)
        if idx >= 0:
            self.port_combo.setCurrentIndex(idx)

    def connect_serial(self):
        port_name = self.port_combo.currentText()
        try:
            self.ser = serial.Serial(port_name, 115200, timeout=1)
            self.status_label.setText(f"Status: Connected to {port_name}")
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", str(e))

    def start_reading(self):
        if self.ser and self.ser.is_open:
            self.timer.start(1000)
            self.status_label.setText("Status: Reading Data...")
        else:
            QMessageBox.warning(self, "Warning", "Please connect to a COM port first.")

    def stop_reading(self):
        self.timer.stop()
        self.status_label.setText("Status: Stopped")

    def read_serial_data(self):
        if not self.ser or not self.ser.is_open:
            return
        try:
            line = self.ser.readline().decode("utf-8", errors="ignore").strip()
            if not line:
                return
            print(line)  # debug output
            # Parse example: "25.32°C | 23.98°C | 26.45°C | 25.12°C"
            if "°C" in line:
                parts = [p.strip().replace("°C", "") for p in line.split("|")]
                if len(parts) == 4:
                    self.ambient_label.setText(f"Ambient: {parts[0]} °C")
                    self.coldsink_label.setText(f"Cold Sink: {parts[1]} °C")
                    self.heatsink_label.setText(f"Heat Sink: {parts[2]} °C")
                    self.flashtop_label.setText(f"Flask Top: {parts[3]} °C")
        except Exception as e:
            print("Serial Read Error:", e)
            self.status_label.setText("Status: Serial Error")
            self.timer.stop()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BoardTester()
    window.show()
    sys.exit(app.exec_())

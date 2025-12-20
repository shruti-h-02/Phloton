import sys
import time

import serial
import serial.tools.list_ports

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QLineEdit,
    QComboBox, QPlainTextEdit, QVBoxLayout, QHBoxLayout, QGroupBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont


# =========================================================
# SERIAL READER THREAD (runs in background)
# =========================================================
class SerialReader(QThread):
    line_received = pyqtSignal(str)

    def __init__(self, port, baud=115200):
        super().__init__()
        self.port = port
        self.baud = baud
        self._running = True
        self.ser = None

    def run(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=1)
        except Exception as e:
            self.line_received.emit(f"[ERROR] Could not open {self.port}: {e}")
            return

        while self._running:
            try:
                if self.ser.in_waiting:
                    line = self.ser.readline().decode(errors="ignore").strip()
                    if line:
                        self.line_received.emit(line)
            except Exception as e:
                self.line_received.emit(f"[SERIAL ERROR] {e}")
                break

        if self.ser:
            self.ser.close()

    def stop(self):
        self._running = False


# =========================================================
# MAIN GUI + AUTOMATION CLASS
# =========================================================
class PhlotonAutomatedFlashTool(QWidget):
    def __init__(self):
        super().__init__()
        self.serial_thread = None

        # 1️⃣ Build GUI first
        self.init_ui()

        # 2️⃣ THEN start automation
        QTimer.singleShot(0, self.auto_detect_com_port)

    # -----------------------------------------------------
    # GUI CREATION (LAYOUT IS FROZEN)
    # -----------------------------------------------------
    def init_ui(self):
        self.setWindowTitle("Phloton Automated Flash Tool")
        self.setFixedSize(820, 470)

        self.setStyleSheet("""
        QWidget {
            background-color: #ffffff;
            color: #000000;
            font-family: Segoe UI;
            font-size: 9pt;
        }
        QGroupBox {
            border: 1px solid #9cb9d9;
            margin-top: 12px;
            padding: 6px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 8px;
            padding: 0 4px;
            color: #0b4f7c;
            font-weight: bold;
        }
        QPushButton {
            background: #eef5fb;
            border: 1px solid #9ec9eb;
            padding: 6px;
        }
        QPushButton:hover {
            background: #ddeaf6;
        }
        QLineEdit, QComboBox {
            background: #ffffff;
            border: 1px solid #b7d7f7;
            padding: 4px;
        }
        QPlainTextEdit {
            background: #ffffff;
            border: 1px solid #9cb9d9;
            font-family: Consolas;
            font-size: 9pt;
        }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(6)

        # ================= TOP ROW =================
        top_layout = QHBoxLayout()

        # -------- Connection --------
        conn_group = QGroupBox("Connection")
        conn_layout = QVBoxLayout()

        port_row = QHBoxLayout()
        port_row.addWidget(QLabel("Port:"))
        self.port_combo = QComboBox()
        port_row.addWidget(self.port_combo)

        self.refresh_btn = QPushButton("Refresh")
        self.chip_label = QLabel("Chip: --")

        self.charger_label = QLabel("Charger: --")
        self.ec200_status_label = QLabel("EC200: --")

        conn_layout.addLayout(port_row)
        conn_layout.addWidget(self.refresh_btn)
        conn_layout.addWidget(self.chip_label)
        conn_layout.addWidget(self.charger_label)
        conn_layout.addWidget(self.ec200_status_label)
        conn_layout.addStretch()

        conn_group.setLayout(conn_layout)
        conn_group.setFixedWidth(220)

        # -------- Flash / Firmware --------
        flash_group = QGroupBox("Flash / Firmware")
        flash_layout = QVBoxLayout()

        flash_layout.addWidget(QLabel("Application (.bin):"))
        self.app_path = QLineEdit()
        self.app_path.setReadOnly(True)
        self.app_path.setPlaceholderText("Auto-detecting firmware...")
        flash_layout.addWidget(self.app_path)

        self.flash_status = QLabel("Flash Status: Idle")
        flash_layout.addWidget(self.flash_status)
        flash_layout.addStretch()

        flash_group.setLayout(flash_layout)

        top_layout.addWidget(conn_group)
        top_layout.addWidget(flash_group)

        main_layout.addLayout(top_layout)

        # ================= LOG CONSOLE =================
        log_group = QGroupBox("Log Console")
        log_layout = QVBoxLayout()

        self.status_label = QLabel("Status: Not Connected")
        self.log_console = QPlainTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setFont(QFont("Consolas", 9))

        log_layout.addWidget(self.status_label)
        log_layout.addWidget(self.log_console)
        log_group.setLayout(log_layout)

        main_layout.addWidget(log_group)

    # -----------------------------------------------------
    # SECTION 2: AUTO COM + SERIAL LISTENER
    # -----------------------------------------------------
    def auto_detect_com_port(self):
        ports = list(serial.tools.list_ports.comports())

        if not ports:
            self.log_console.appendPlainText("No COM ports found")
            return

        for p in ports:
            self.log_console.appendPlainText(f"Trying {p.device}...")
            try:
                ser = serial.Serial(p.device, 115200, timeout=1)
                ser.reset_input_buffer()

                start = time.time()
                while time.time() - start < 2.0:
                    if ser.in_waiting:
                        line = ser.readline().decode(errors="ignore")
                        if (
                            "Enter option number" in line or
                            "Device MAC ID" in line
                        ):
                            ser.close()
                            self.log_console.appendPlainText(
                                f"Detected board on {p.device}"
                            )
                            self.start_serial_listener(p.device)
                            return

                ser.close()
            except Exception as e:
                self.log_console.appendPlainText(
                    f"{p.device} skipped ({e})"
                )

        self.log_console.appendPlainText("No compatible device detected")

    def start_serial_listener(self, port):
        self.status_label.setText("Status: Connected")

        self.serial_thread = SerialReader(port)
        self.serial_thread.line_received.connect(self.handle_serial_line)
        self.serial_thread.start()

    def handle_serial_line(self, line):
        self.log_console.appendPlainText(line)

        if "CHARGER:CONNECTED" in line:
            self.charger_label.setText("Charger: Connected")
        elif "CHARGER:DISCONNECTED" in line:
            self.charger_label.setText("Charger: Disconnected")


# =========================================================
# APP ENTRY POINT
# =========================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PhlotonAutomatedFlashTool()
    window.show()
    sys.exit(app.exec())

import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QLineEdit,
    QComboBox, QPlainTextEdit, QVBoxLayout, QHBoxLayout, QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class PhlotonAutomatedFlashTool(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        # ================= Window =================
        self.setWindowTitle("Phloton Automated Flash Tool")
        self.setFixedSize(820, 470)

        # ================= Style (LIGHT – reference aligned) =================
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
        # ================= Main Layout =================
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(6)

        # ================= Top Row =================
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)

        # -------- Connection --------
        conn_group = QGroupBox("Connection")
        conn_layout = QVBoxLayout()

        port_row = QHBoxLayout()
        port_row.addWidget(QLabel("Port:"))
        self.port_combo = QComboBox()
        port_row.addWidget(self.port_combo)

        self.refresh_btn = QPushButton("Refresh")
        self.chip_label = QLabel("Chip: --")

        conn_layout.addLayout(port_row)
        conn_layout.addWidget(self.refresh_btn)
        conn_layout.addWidget(self.chip_label)
        conn_layout.addStretch()

        conn_group.setLayout(conn_layout)
        conn_group.setFixedWidth(220)

        # -------- Flash / Firmware (AUTO FLASH) --------
        flash_group = QGroupBox("Flash / Firmware")
        flash_layout = QVBoxLayout()

        flash_layout.addWidget(QLabel("Application (.bin):"))

        self.app_path = QLineEdit()
        self.app_path.setReadOnly(True)
        self.app_path.setPlaceholderText("Auto-detecting firmware...")
        flash_layout.addWidget(self.app_path)

        self.flash_status = QLabel("Flash Status: Idle")
        self.flash_status.setStyleSheet("color: #0b4f7c;")
        flash_layout.addWidget(self.flash_status)

        flash_layout.addStretch()
        flash_group.setLayout(flash_layout)

        # ---- Add groups to top row ----
        top_layout.addWidget(conn_group)
        top_layout.addWidget(flash_group)

        #  THIS LINE IS CRITICAL
        main_layout.addLayout(top_layout)

        # ================= Log Console Group =================
        log_group = QGroupBox("Log Console")
        log_layout = QVBoxLayout()
        log_layout.setSpacing(4)
        log_layout.setContentsMargins(6, 10, 6, 6)

        # Status INSIDE log box
        self.status_label = QLabel("Status: Not Connected")
        self.status_label.setStyleSheet("color: #000000;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Log text area
        self.log_console = QPlainTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setFont(QFont("Consolas", 9))

        log_layout.addWidget(self.status_label)
        log_layout.addWidget(self.log_console)

        log_group.setLayout(log_layout)

        # Add to main layout
        main_layout.addWidget(log_group)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PhlotonAutomatedFlashTool()
    window.show()
    sys.exit(app.exec())

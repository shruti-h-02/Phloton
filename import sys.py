import sys
import os
import glob
import subprocess
import time
import serial


from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QFileDialog, QPlainTextEdit, QVBoxLayout, QHBoxLayout,
    QComboBox, QGroupBox
)
from serial.tools import list_ports

# ============================================================
# LIGHT THEME
# ============================================================
def apply_light_theme(app):
    app.setStyleSheet("""
    QWidget { background:#ffffff; color:#000; font-family:Segoe UI; }
    #Header { background:#0b4f7c; color:white; padding:6px; font-weight:bold; }
    QGroupBox { border:1px solid #b7d7f7; margin-top:10px; padding-top:16px; }
    QGroupBox::title { color:#0b4f7c; font-weight:bold; }
    QPushButton { background:#eef5fb; border:1px solid #9ec9eb; padding:6px; }
    QPlainTextEdit { font-family:Consolas; font-size:10pt; }
    """)
# ============================================================
# WORKER: CHIP DETECTION
# ============================================================
class ChipDetectWorker(QThread):
    detected = pyqtSignal(str)
    failed = pyqtSignal()

    def __init__(self, port):
        super().__init__()
        self.port = port

    def run(self):
        try:
            p = subprocess.run(
                [sys.executable, "-m", "esptool", "--port", self.port, "chip_id"],
                capture_output=True, text=True, timeout=5
            )
            out = p.stdout.lower()
            if "esp32-s3" in out:
                self.detected.emit("esp32s3")
            elif "esp32-s2" in out:
                self.detected.emit("esp32s2")
            elif "esp32" in out:
                self.detected.emit("esp32")
            else:
                self.failed.emit()
        except:
            self.failed.emit()
# ============================================================
# WORKER: FLASH TOOL
# ============================================================
class FlashWorker(QThread):
    log = pyqtSignal(str)
    finished = pyqtSignal(bool)

    def __init__(self, port, chip, firmware):
        super().__init__()
        self.port = port
        self.chip = chip
        self.firmware = firmware

    def run(self):
        fw_dir = os.path.dirname(self.firmware)
        boot = part = None

        # auto-find bootloader + partition files
        for root, _, _ in os.walk(fw_dir):
            if not boot:
                b = glob.glob(os.path.join(root, "*bootloader*.bin"))
                if b:
                    boot = b[0]

            if not part:
                p = glob.glob(os.path.join(root, "*partitions*.bin"))
                if p:
                    part = p[0]

            if boot and part:
                break

        if not boot or not part:
            self.log.emit("ERROR: bootloader or partition bin not found!")
            self.finished.emit(False)
            return
        cmd = [
            sys.executable, "-m", "esptool",
            "--chip", self.chip,
            "--port", self.port,
            "--baud", "921600",
            "--before", "default_reset",
            "--after", "hard_reset",
            "write_flash", "-z",
            "0x0000", boot,
            "0x8000", part,
            "0x10000", self.firmware
        ]
        p = subprocess.run(cmd, capture_output=True, text=True)
        self.log.emit(p.stdout + p.stderr)
        self.finished.emit(p.returncode == 0)

# ============================================================
# SERIAL MONITOR THREAD
# ============================================================
class SerialReader(QThread):
    data = pyqtSignal(str)

    def __init__(self, port):
        super().__init__()
        self.port = port
        self.running = True

    def run(self):
        try:
            ser = serial.Serial(self.port, 115200, timeout=1)
            while self.running:
                if ser.in_waiting:
                    line = ser.readline().decode(errors="ignore").strip()
                    if line:
                        self.data.emit(line)
            ser.close()
        except:
            pass

    def stop(self):
        self.running = False


# ============================================================
# MAIN UI TOOL
# ============================================================
class AutomationTool(QWidget):
    def __init__(self):
        super().__init__()
        self.chip = None
        self.reader = None

        self.setWindowTitle("Phloton Automated Flash Tool")

        self.build_ui()
        self.refresh_ports()

        self.status.setText("Status: Not Connected")
        self.flash_btn.setEnabled(False)
        self.mac_found_in_sd = False

    # ========================================================
    # UI LAYOUT
    # ========================================================
    def build_ui(self):
        main = QVBoxLayout(self)

        # HEADER
        header = QLabel("  Phloton Automated Flash Tool")
        header.setObjectName("Header")
        header.setFixedHeight(32)
        main.addWidget(header)

        # TOP AREA
        top = QHBoxLayout()
        main.addLayout(top)

        # --------------------------------------------------------------------
        # CONNECTION BOX (LEFT)
        # --------------------------------------------------------------------
        conn = QGroupBox("Connection")
        cl = QVBoxLayout(conn)

        self.port_cb = QComboBox()
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh_ports)

        self.chip_lbl = QLabel("Chip: --")

        cl.addWidget(QLabel("Port:"))
        cl.addWidget(self.port_cb)
        cl.addWidget(refresh)
        cl.addSpacing(6)
        cl.addWidget(self.chip_lbl)
        cl.addStretch()

        top.addWidget(conn, 0)

        # --------------------------------------------------------------------
        # FLASH / FIRMWARE BOX (RIGHT)
        # --------------------------------------------------------------------
        flash = QGroupBox("Flash / Firmware")
        fl = QVBoxLayout(flash)

        self.bin_edit = QLineEdit()
        browse = QPushButton("Browse")
        browse.clicked.connect(self.browse)

        self.flash_btn = QPushButton("Flash")
        self.flash_btn.clicked.connect(self.flash)

        fl.addWidget(QLabel("Application (.bin):"))
        fl.addWidget(self.bin_edit)
        fl.addWidget(browse)
        fl.addSpacing(6)
        fl.addWidget(self.flash_btn)
        fl.addStretch()

        top.addWidget(flash, 1)

        # --------------------------------------------------------------------
        # LOG CONSOLE (BOTTOM)
        # --------------------------------------------------------------------
        log_box = QGroupBox("Log Console")
        ll = QVBoxLayout(log_box)

        self.status = QLabel("Status:")
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)

        ll.addWidget(self.status)
        ll.addWidget(self.log)

        main.addWidget(log_box, 1)

        self.port_cb.currentTextChanged.connect(self.detect_chip)

    # ========================================================
    # HELPERS
    # ========================================================
    def refresh_ports(self):
        self.port_cb.clear()
        for p in list_ports.comports():
            self.port_cb.addItem(p.device)

    def browse(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select firmware", "", "Binary Files (*.bin)")
        if f:
            self.bin_edit.setText(f)

    # ========================================================
    # CHIP DETECTION
    # ========================================================
    def detect_chip(self):
        port = self.port_cb.currentText()
        if not port:
            self.status.setText("Status: Not Connected")
            self.flash_btn.setEnabled(False)
            return

        self.status.setText("Status: Detecting Chip")
        self.flash_btn.setEnabled(False)

        self.detector = ChipDetectWorker(port)
        self.detector.detected.connect(self.chip_ok)
        self.detector.failed.connect(self.chip_fail)
        self.detector.start()

    def chip_ok(self, chip):
        self.chip = chip
        self.chip_lbl.setText(f"Chip: {chip}")
        self.flash_btn.setEnabled(True)
        self.status.setText("Status: Ready")

    def chip_fail(self):
        self.chip_lbl.setText("Chip: --")
        self.flash_btn.setEnabled(False)
        self.status.setText("Status: Chip Detect Failed")

    # ========================================================
    # FLASH PROCESS
    # ========================================================
    def flash(self):
        self.log.clear()
        self.status.setText("Status: Flashing")

        self.worker = FlashWorker(
            self.port_cb.currentText(),
            self.chip,
            self.bin_edit.text()
        )
        self.worker.log.connect(self.log.appendPlainText)
        self.worker.finished.connect(self.after_flash)
        self.worker.start()

    def after_flash(self, ok):
        if ok:
            self.status.setText("Status: Monitoring")
            time.sleep(2)
            self.start_serial()
        else:
            self.status.setText("Status: Flash Failed")

    # ========================================================
    # SERIAL MONITOR
    # ========================================================
    def start_serial(self):
        if self.reader:
            self.reader.stop()

        self.reader = SerialReader(self.port_cb.currentText())
        self.reader.data.connect(self.handle_serial)
        self.reader.start()

    #=======================================================
    # Mac ID=======================================
        def handle_serial(self, line):
        # Always show raw output
         self.log.appendPlainText(line)

        # Detect SD MAC line exactly as firmware prints
         if line.startswith("Device MAC ID"):
            self.mac_found_in_sd = True
            self.status.setText("Status: MAC Written in SD (Verified)")

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_light_theme(app)

    win = AutomationTool()
    win.resize(1100, 700)
    win.show()

    sys.exit(app.exec())

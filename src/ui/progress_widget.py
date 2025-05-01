from PyQt5.QtWidgets import QProgressBar, QLabel, QVBoxLayout, QWidget
from PyQt5.QtCore import pyqtSignal


class TranscriptionProgressWidget(QWidget):
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        self.status_label = QLabel("Esperando archivo...")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)

        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        self.setLayout(layout)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def update_status(self, message):
        self.status_label.setText(message)

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QMessageBox
from PyQt5.QtCore import Qt


class ConfigDialog(QDialog):
    def __init__(self, current_config=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración API y AI")
        self.setModal(True)
        self.resize(400, 200)

        layout = QVBoxLayout(self)

        # API Key input
        api_layout = QHBoxLayout()
        api_label = QLabel("Clave API:")
        self.api_key_edit = QLineEdit()
        if current_config and "google_api_key" in current_config:
            self.api_key_edit.setText(current_config["google_api_key"])
        api_layout.addWidget(api_label)
        api_layout.addWidget(self.api_key_edit)
        layout.addLayout(api_layout)

        # AI Engine dropdown
        ai_layout = QHBoxLayout()
        ai_label = QLabel("Procesador AI:")
        self.ai_combo = QComboBox()
        # Add AI engine options
        self.ai_combo.addItems(["Gemini", "DeepSeek"])
        if current_config and "text_processor_type" in current_config:
            index = self.ai_combo.findText(
                current_config["text_processor_type"])
            if index >= 0:
                self.ai_combo.setCurrentIndex(index)
        ai_layout.addWidget(ai_label)
        ai_layout.addWidget(self.ai_combo)
        layout.addLayout(ai_layout)

        # Buttons
        buttons_layout = QHBoxLayout()
        self.ok_button = QPushButton("Aceptar")
        self.cancel_button = QPushButton("Cancelar")
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)

        self.ok_button.clicked.connect(self.validate_and_accept)
        self.cancel_button.clicked.connect(self.reject)

    def validate_and_accept(self):
        api_key = self.api_key_edit.text().strip()
        if len(api_key) < 10:
            QMessageBox.warning(self, "Clave API inválida",
                                "La clave API debe tener al menos 10 caracteres.")
            return
        self.accept()

    def get_config(self):
        return {
            "google_api_key": self.api_key_edit.text(),
            "text_processor_type": self.ai_combo.currentText()
        }

# src/ui/main_window.py
import sys
import os
import logging
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget,
                             QTabWidget, QLineEdit, QPushButton, QLabel,
                             QHBoxLayout, QComboBox, QCheckBox, QGroupBox,
                             QFileDialog, QSpinBox, QDoubleSpinBox, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, QSettings

# Importar DragDropArea usando importación relativa
# Ya que main_window.py está dentro del subpaquete src.ui,
# y drag_drop_area.py está en el mismo subpaquete, usamos '.'
# CORREGIDO: Importación relativa para DragDropArea
from .drag_drop_area import DragDropArea  # Importación relativa

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    # Señal para notificar cambios en la configuración (ej. tipo de reconocedor, idioma)
    # Emite un diccionario con los valores de configuración relevantes
    config_changed = pyqtSignal(dict)

    def __init__(self, config_settings: dict = None):
        super().__init__()
        logger.info("Inicializando MainWindow...")

        self.setWindowTitle("Video Transcriber")
        self.setGeometry(100, 100, 800, 600)  # Tamaño y posición inicial

        # Widget central y layout principal
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # Área de arrastrar y soltar
        self.drag_drop_area = DragDropArea(self)
        self.drag_drop_area.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)  # Permitir que se expanda
        self.main_layout.addWidget(self.drag_drop_area)

        # Pestañas para configuración y otras opciones futuras
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        # Pestaña de Configuración
        self.config_tab = QWidget()
        self.tabs.addTab(self.config_tab, "Configuración")
        # Configurar la pestaña de configuración
        self.setup_config_tab(config_settings)

        # Conectar señales (si DragDropArea tiene alguna señal que MainWindow necesite manejar)
        # self.drag_drop_area.file_dropped.connect(self.handle_file_dropped) # Ejemplo si necesitas manejar el drop aquí

        logger.info("MainWindow inicializada.")

    def setup_config_tab(self, config_settings: dict = None):
        """Configura la pestaña de configuración con los ajustes actuales."""
        logger.info("Configurando pestaña de configuración...")
        config_layout = QVBoxLayout(self.config_tab)
        config_layout.setAlignment(Qt.AlignTop)  # Alinear contenido arriba

        # Usar QSettings para cargar y guardar la configuración
        # self.settings = QSettings("YourCompanyName", "VideoTranscriber") # Usa un nombre de organización y aplicación únicos

        # --- Configuración General ---
        general_group = QGroupBox("General")
        general_layout = QVBoxLayout(general_group)

        # Directorio de Salida
        output_dir_layout = QHBoxLayout()
        self.output_dir_label = QLabel("Directorio de Salida:")
        self.output_dir_edit = QLineEdit(config_settings.get(
            "output_dir", "./output"))  # Valor por defecto
        self.output_dir_button = QPushButton("Seleccionar")
        self.output_dir_button.clicked.connect(self.select_output_directory)
        output_dir_layout.addWidget(self.output_dir_label)
        output_dir_layout.addWidget(self.output_dir_edit)
        output_dir_layout.addWidget(self.output_dir_button)
        general_layout.addLayout(output_dir_layout)

        config_layout.addWidget(general_group)

        # --- Configuración del Reconocedor de Voz ---
        recognizer_group = QGroupBox("Reconocimiento de Voz")
        recognizer_layout = QVBoxLayout(recognizer_group)

        # Tipo de Reconocedor
        recognizer_type_layout = QHBoxLayout()
        self.recognizer_type_label = QLabel("Tipo de Reconocedor:")
        self.recognizer_type_combo = QComboBox()
        # Asegúrate de que estos nombres coincidan con las claves en tu Config y la lógica de inicialización
        self.recognizer_type_combo.addItems(
            ["Google", "Whisper"])  # Opciones disponibles
        # Seleccionar el valor actual de la configuración
        current_recognizer_index = self.recognizer_type_combo.findText(
            config_settings.get("recognizer_type", "Google"), Qt.MatchExactly)
        if current_recognizer_index >= 0:
            self.recognizer_type_combo.setCurrentIndex(
                current_recognizer_index)

        self.recognizer_type_combo.currentIndexChanged.connect(
            self.on_config_value_changed)  # Conectar señal
        recognizer_type_layout.addWidget(self.recognizer_type_label)
        recognizer_type_layout.addWidget(self.recognizer_type_combo)
        recognizer_layout.addLayout(recognizer_type_layout)

        # Idioma del Reconocedor
        # Idioma del Reconocedor (usando ComboBox en lugar de QLineEdit)
        recognizer_language_layout = QHBoxLayout()
        self.recognizer_language_label = QLabel("Idioma:")
        self.recognizer_language_combo = QComboBox()

        # Añadir opciones de idioma con sus códigos
        language_options = [
            ("Español", "es-ES"),
            ("Inglés", "en-US"),
            ("Francés", "fr-FR"),
            ("Portugués", "pt-PT"),
            ("Chino (Mandarín)", "zh-CN")
        ]

        for display_name, lang_code in language_options:
            self.recognizer_language_combo.addItem(display_name, lang_code)

        # Seleccionar el idioma actual de la configuración
        current_language = config_settings.get("recognizer_language", "es-ES")
        for i in range(self.recognizer_language_combo.count()):
            if self.recognizer_language_combo.itemData(i) == current_language:
                self.recognizer_language_combo.setCurrentIndex(i)
                break

        self.recognizer_language_combo.currentIndexChanged.connect(
            self.on_config_value_changed)  # Conectar señal
        recognizer_language_layout.addWidget(self.recognizer_language_label)
        recognizer_language_layout.addWidget(self.recognizer_language_combo)
        recognizer_layout.addLayout(recognizer_language_layout)

        # Opción para traducir al español
        translate_layout = QHBoxLayout()
        self.translate_label = QLabel("Traducir resultado:")
        self.translate_checkbox = QCheckBox("Traducir al español")
        self.translate_checkbox.setChecked(
            config_settings.get("translate_to_spanish", False))
        self.translate_checkbox.stateChanged.connect(
            self.on_config_value_changed)
        translate_layout.addWidget(self.translate_label)
        translate_layout.addWidget(self.translate_checkbox)
        recognizer_layout.addLayout(translate_layout)

        # Clave API de Google (si usas Google)
        # Considera manejar esto de forma más segura, como con variables de entorno.
        # Por ahora, un campo de texto simple para la demostración.
        google_api_key_layout = QHBoxLayout()
        self.google_api_key_label = QLabel("Google API Key:")
        self.google_api_key_edit = QLineEdit(
            config_settings.get("google_api_key", ""))  # Valor por defecto
        self.google_api_key_edit.setEchoMode(
            QLineEdit.PasswordEchoOnEdit)  # Ocultar texto
        self.google_api_key_edit.editingFinished.connect(
            self.on_config_value_changed)  # Conectar señal
        google_api_key_layout.addWidget(self.google_api_key_label)
        google_api_key_layout.addWidget(self.google_api_key_edit)
        recognizer_layout.addLayout(google_api_key_layout)

        config_layout.addWidget(recognizer_group)

        # --- Configuración del Procesamiento de Texto (AI) ---
        text_processing_group = QGroupBox("Procesamiento de Texto (AI)")
        text_processing_layout = QVBoxLayout(text_processing_group)

        # Tipo de Procesador de Texto AI (Gemini, DeepSeek, etc.)
        text_processor_type_layout = QHBoxLayout()
        self.text_processor_type_label = QLabel("Procesador AI:")
        self.text_processor_type_combo = QComboBox()
        # Asegúrate de que estos nombres coincidan con las claves en tu Config y la lógica de inicialización
        self.text_processor_type_combo.addItems(
            ["Gemini", "DeepSeek"])  # Opciones disponibles
        # Seleccionar el valor actual de la configuración
        current_processor_index = self.text_processor_type_combo.findText(
            config_settings.get("text_processor_type", "Gemini"), Qt.MatchExactly)
        if current_processor_index >= 0:
            self.text_processor_type_combo.setCurrentIndex(
                current_processor_index)
        self.text_processor_type_combo.currentIndexChanged.connect(
            self.on_config_value_changed)  # Conectar señal
        text_processor_type_layout.addWidget(self.text_processor_type_label)
        text_processor_type_layout.addWidget(self.text_processor_type_combo)
        text_processing_layout.addLayout(text_processor_type_layout)

        # Configuración específica del formateador (ej. duración mínima de línea, caracteres por línea)
        formatter_settings_group = QGroupBox("Formato de Transcripción")
        formatter_settings_layout = QVBoxLayout(formatter_settings_group)

        min_line_duration_layout = QHBoxLayout()
        self.min_line_duration_label = QLabel("Duración mínima de línea (s):")
        self.min_line_duration_spinbox = QDoubleSpinBox()
        self.min_line_duration_spinbox.setRange(0.1, 10.0)
        self.min_line_duration_spinbox.setSingleStep(0.1)
        self.min_line_duration_spinbox.setValue(config_settings.get(
            "text_processing", {}).get("min_line_duration", 0.5))
        self.min_line_duration_spinbox.valueChanged.connect(
            self.on_config_value_changed)
        min_line_duration_layout.addWidget(self.min_line_duration_label)
        min_line_duration_layout.addWidget(self.min_line_duration_spinbox)
        formatter_settings_layout.addLayout(min_line_duration_layout)

        max_chars_per_line_layout = QHBoxLayout()
        self.max_chars_per_line_label = QLabel("Máx. caracteres por línea:")
        self.max_chars_per_line_spinbox = QSpinBox()
        self.max_chars_per_line_spinbox.setRange(20, 200)
        self.max_chars_per_line_spinbox.setSingleStep(10)
        self.max_chars_per_line_spinbox.setValue(config_settings.get(
            "text_processing", {}).get("max_chars_per_line", 80))
        self.max_chars_per_line_spinbox.valueChanged.connect(
            self.on_config_value_changed)
        max_chars_per_line_layout.addWidget(self.max_chars_per_line_label)
        max_chars_per_line_layout.addWidget(self.max_chars_per_line_spinbox)
        formatter_settings_layout.addLayout(max_chars_per_line_layout)

        text_processing_layout.addWidget(formatter_settings_group)

        config_layout.addWidget(text_processing_group)

        # --- Botón para guardar configuración (opcional, si no guardas automáticamente) ---
        # self.save_button = QPushButton("Guardar Configuración")
        # self.save_button.clicked.connect(self.save_settings)
        # config_layout.addWidget(self.save_button)

        config_layout.addStretch(1)  # Empujar todo el contenido hacia arriba

        logger.info("Pestaña de configuración configurada.")

    def select_output_directory(self):
        """Abre un diálogo para seleccionar el directorio de salida."""
        logger.info("Abriendo diálogo para seleccionar directorio de salida...")
        options = QFileDialog.Options()
        # options |= QFileDialog.DontUseNativeDialog # Descomentar si hay problemas con el diálogo nativo

        # Obtener el directorio actual del QLineEdit como directorio inicial
        initial_dir = self.output_dir_edit.text()
        if not os.path.isdir(initial_dir):
            # Fallback al directorio de inicio del usuario
            initial_dir = os.path.expanduser("~")

        directory = QFileDialog.getExistingDirectory(self, "Seleccionar Directorio de Salida",
                                                     initial_dir, options=options)

        if directory:
            logger.info(f"Directorio de salida seleccionado: {directory}")
            self.output_dir_edit.setText(directory)
            self.on_config_value_changed()  # Notificar el cambio de configuración

    def on_config_value_changed(self):
        """
        Recopila los valores de configuración actuales de la UI y emite la señal config_changed.
        Esta función se conecta a las señales de cambio de los widgets de configuración.
        """
        logger.debug(
            "Valor de configuración de UI cambiado. Recopilando y emitiendo señal...")
        current_config = {
            "output_dir": self.output_dir_edit.text(),
            "recognizer_type": self.recognizer_type_combo.currentText(),
            "recognizer_language": self.recognizer_language_combo.itemData(self.recognizer_language_combo.currentIndex()),
            "translate_to_spanish": self.translate_checkbox.isChecked(),
            # Considera no emitir la API key en la señal si no es necesario
            "google_api_key": self.google_api_key_edit.text(),
            "text_processor_type": self.text_processor_type_combo.currentText(),
            "text_processing": {  # Configuración anidada para el formateador
                "min_line_duration": self.min_line_duration_spinbox.value(),
                "max_chars_per_line": self.max_chars_per_line_spinbox.value()
            }
            # Añadir aquí otros ajustes de configuración de la UI
        }
        # Emitir la señal con los valores actuales
        self.config_changed.emit(current_config)
        logger.debug(f"Señal config_changed emitida con: {current_config}")

    # NOTA: La lógica para guardar la configuración en el archivo
    # se maneja en main.py cuando recibe esta señal.

    # def save_settings(self):
    #     """Guarda la configuración actual de la UI usando QSettings."""
    #     logger.info("Guardando configuración desde UI...")
    #     self.settings.setValue("output_dir", self.output_dir_edit.text())
    #     self.settings.setValue("recognizer_type", self.recognizer_type_combo.currentText())
    #     self.settings.setValue("recognizer_language", self.recognizer_language_edit.text())
    #     self.settings.setValue("google_api_key", self.google_api_key_edit.text())
    #
    #     self.settings.setValue("text_processor_type", self.text_processor_type_combo.currentText())
    #
    #     # Guardar configuración anidada para text_processing
    #     self.settings.setValue("text_processing/min_line_duration", self.min_line_duration_spinbox.value())
    #     self.settings.setValue("text_processing/max_chars_per_line", self.max_chars_per_line_spinbox.value())
    #
    #     logger.info("Configuración guardada.")
    #     QMessageBox.information(self, "Configuración Guardada", "La configuración ha sido guardada correctamente.")

    # def load_settings(self):
    #     """Carga la configuración guardada usando QSettings y actualiza la UI."""
    #     logger.info("Cargando configuración para actualizar UI...")
    #     self.output_dir_edit.setText(self.settings.value("output_dir", "./output"))
    #
    #     recognizer_type = self.settings.value("recognizer_type", "Google")
    #     index = self.recognizer_type_combo.findText(recognizer_type, Qt.MatchExactly)
    #     if index >= 0:
    #         self.recognizer_type_combo.setCurrentIndex(index)
    #
    #     self.recognizer_language_edit.setText(self.settings.value("recognizer_language", "en-US"))
    #     self.google_api_key_edit.setText(self.settings.value("google_api_key", ""))
    #
    #     text_processor_type = self.settings.value("text_processor_type", "Gemini")
    #     index = self.text_processor_type_combo.findText(text_processor_type, Qt.MatchExactly)
    #     if index >= 0:
    #         self.text_processor_type_combo.setCurrentIndex(index)
    #
    #     # Cargar configuración anidada para text_processing
    #     min_line_duration = float(self.settings.value("text_processing/min_line_duration", 0.5))
    #     self.min_line_duration_spinbox.setValue(min_line_duration)
    #
    #     max_chars_per_line = int(self.settings.value("text_processing/max_chars_per_line", 80))
    #     self.max_chars_per_line_spinbox.setValue(max_chars_per_line)
    #
    #     logger.info("Configuración cargada y UI actualizada.")

    # def handle_file_dropped(self, file_path):
    #     """Ejemplo de cómo MainWindow podría manejar el evento de archivo soltado."""
    #     logger.info(f"MainWindow recibió archivo soltado: {file_path}")
    #     # Aquí podrías iniciar el proceso de transcripción llamando a una función en main.py
    #     # o pasar el archivo a otra parte de la lógica de la aplicación.
    #     # En nuestra estructura actual, DragDropArea maneja directamente el inicio de la transcripción.
    #     pass

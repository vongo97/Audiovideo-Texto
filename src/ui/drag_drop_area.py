# src/ui/drag_drop_area.py
import logging
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QMimeData, QUrl
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QFrame, QWidget, QProgressDialog, QMessageBox, QApplication
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QDragLeaveEvent
import os
from typing import Dict, Any, Union

# Importar los tipos para tipado usando importaciones relativas
# Si GeminiProcessor y TextProcessor están en src/utils, las importaciones deben ser relativas a src
# Si SpeechRecognizer está en src/transcriber, la importación debe ser relativa a src

from src.utils.gemini_processor import GeminiProcessor
from src.utils.text_processor import TextProcessor
from src.transcriber.speech_recognition_factory import SpeechRecognizer
from src.transcriber.audio_extractor import extract_and_transcribe

# Importar la función extract_and_transcribe usando IMPORTACIÓN RELATIVA
# Ya que drag_drop_area.py está dentro del subpaquete src.ui,
# y audio_extractor está en el subpaquete src.transcriber,
# necesitamos subir un nivel (de src.ui a src) y luego bajar a transcriber.
# La importación correcta desde src.ui a src.transcriber es:
# <-- Importación relativa corregida
from ..transcriber.audio_extractor import extract_and_transcribe


logger = logging.getLogger(__name__)


# Define el hilo para la transcripción
class TranscriptionThread(QThread):
    # Señales para comunicar el progreso y resultado a la UI
    # Emite (mensaje de progreso, porcentaje 0-100)
    progress_updated = pyqtSignal(str, int)
    # Emite (ruta del archivo de salida) en caso de éxito
    transcription_completed = pyqtSignal(str)
    # Emite (mensaje de error) en caso de error
    transcription_error = pyqtSignal(str)

    # Aceptar ai_text_processor y formatter por separado
    def __init__(self, file_path: str,
                 # Usamos Any para DeepSeek si no está importado
                 ai_text_processor: Union[GeminiProcessor, Any],
                 formatter: TextProcessor,
                 recognizer: SpeechRecognizer,
                 language: str):
        super().__init__()
        self.file_path = file_path
        # <-- Guardar el procesador de texto AI
        self.ai_text_processor = ai_text_processor
        self.formatter = formatter  # <-- Guardar el formateador
        self.recognizer = recognizer
        self.language = language
        self._is_canceled = False

    def run(self):
        """Ejecuta el proceso de transcripción en el hilo."""
        self.progress_updated.emit(
            f"Iniciando transcripción de {os.path.basename(self.file_path)}...", 0)
        try:
            # Crear una instancia de Config para acceder a settings
            # Asegúrate de que la ruta sea correcta según tu estructura de proyecto
            from src.config import Config
            config = Config()

            output_path = extract_and_transcribe(
                file_path=self.file_path,
                ai_text_processor=self.ai_text_processor,
                formatter=self.formatter,
                recognizer=self.recognizer,
                language=self.language,
                config_settings=config.settings
            )

            if not self._is_canceled:
                self.progress_updated.emit("¡Transcripción completada!", 100)
                self.transcription_completed.emit(output_path)

        except Exception as e:
            if not self._is_canceled:
                error_message = f"Error en el hilo de transcripción para {os.path.basename(self.file_path)}: {str(e)}"
                logging.error(error_message)
                self.progress_updated.emit(
                    "¡Error durante la transcripción!", -1)  # Indicador de error
                self.transcription_error.emit(error_message)

    def cancel(self):
        """Cancela el proceso de transcripción."""
        self._is_canceled = True
        # NOTA: La cancelación en TranscriptionThread es simple.
        # Para una cancelación real durante el proceso (ej. en moviepy, whisper),
        # necesitarías añadir lógica de cancelación a extract_and_transcribe y process_in_chunks.
        self.requestInterruption()
        logging.info(
            f"Solicitud de cancelación para {os.path.basename(self.file_path)}.")


logger = logging.getLogger(__name__)


class DragDropArea(QFrame):
    # Señal emitida cuando un archivo es soltado
    file_dropped = pyqtSignal(str)

    # set_processors ahora acepta ai_text_processor y formatter por separado
    def set_processors(self, ai_text_processor: Union[GeminiProcessor, Any],  # Usamos Any para DeepSeek si no está importado
                       formatter: TextProcessor, recognizer: SpeechRecognizer, language: str):
        """
        Establece las instancias de los procesadores, reconocedor e idioma para el área de arrastre.
        """
        # Guardar las instancias y el idioma
        # <-- Guardar el procesador de texto genérico
        self.ai_text_processor = ai_text_processor
        self.formatter = formatter  # <-- Guardar el formateador
        self.recognizer = recognizer
        self.language = language

        logger.info(
            "AI Text Processor, Formatter, Recognizer e Idioma set in DragDropArea.")

    def __init__(self, parent=None):
        super().__init__(parent)
        # Habilitar la funcionalidad de arrastrar y soltar
        self.setAcceptDrops(True)

        self.layout = QVBoxLayout(self)
        self.label = QLabel(
            "Arrastra y suelta un archivo de video o audio aquí", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWordWrap(True)
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)

        # Estilo visual (opcional)
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #aaa;
                border-radius: 10px;
                background-color: #f8f8f8;
                color: #333;
            }
            QLabel {
                font-size: 16px;
                font-weight: bold;
            }
        """)

        # Atributos para manejar el proceso de transcripción
        self.transcription_thread: TranscriptionThread | None = None
        self.progress_dialog: QProgressDialog | None = None

        # Atributos para las instancias de procesadores (inicializados en set_processors)
        self.ai_text_processor: Union[GeminiProcessor, Any] | None = None
        self.formatter: TextProcessor | None = None  # Instancia del formateador
        self.recognizer: SpeechRecognizer | None = None
        self.language: str | None = None

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Maneja el evento de arrastrar un objeto sobre el área."""
        # Aceptar solo archivos o URLs
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
            # Opcional: Cambiar estilo para indicar que se puede soltar
            # self.setStyleSheet("...")

    def dragLeaveEvent(self, event: QDragLeaveEvent):
        """Maneja el evento de salir del área arrastrando un objeto."""
        # Opcional: Restaurar estilo original
        # self.setStyleSheet("...")
        event.accept()

    def dropEvent(self, event: QDropEvent):
        """Maneja el evento de soltar un objeto sobre el área."""
        # Restaurar estilo original (si lo cambiaste en dragEnterEvent)
        # self.setStyleSheet("...")

        mime_data: QMimeData = event.mimeData()

        if mime_data.hasUrls():
            # Manejar URLs (puede ser ruta de archivo local o URL web)
            urls = mime_data.urls()
            if urls:
                # Tomar la primera URL soltada
                url: QUrl = urls[0]
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    logger.info(f"Archivo local soltado: {file_path}")
                    self.process_file(file_path)
                else:
                    # Aquí manejarías URLs web (como YouTube), lo cual no está implementado aún.
                    web_url = url.toString()
                    logger.warning(
                        f"URL web soltada (no soportado aún): {web_url}")
                    QMessageBox.warning(self, "Formato no soportado",
                                        f"Arrastrar URLs web no está soportado en este momento.\nIntenta con un archivo local.")
        elif mime_data.hasText():
            # Manejar texto plano (podría ser una URL pegada)
            text_data = mime_data.text()
            try:
                # Intentar si el texto es una URL
                url = QUrl(text_data)
                if url.isValid() and url.scheme() in ['http', 'https']:
                    logger.warning(
                        f"URL web soltada como texto (no soportado aún): {text_data}")
                    QMessageBox.warning(self, "Formato no soportado",
                                        f"Pegar URLs web no está soportado en este momento.\nIntenta con un archivo local.")
                else:
                    logger.warning(
                        f"Texto soltado (no es una URL de archivo ni web): {text_data}")
                    QMessageBox.warning(self, "Formato no soportado",
                                        f"Pegar texto plano no está soportado. Arrastra o pega un archivo.")

            except Exception:
                logger.warning(
                    f"Texto soltado no pudo ser interpretado como URL: {text_data}")
                QMessageBox.warning(self, "Formato no soportado",
                                    f"Pegar texto plano no está soportado. Arrastra o pega un archivo.")

        event.acceptProposedAction()

    def process_file(self, file_path):
        """Inicia el proceso de transcripción para un archivo local."""
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "Archivo no encontrado",
                                f"El archivo no existe:\n{file_path}")
            logger.warning(f"Archivo no encontrado: {file_path}")
            return

        # Verificar que las instancias de procesador y reconocedor estén seteados
        # MODIFICADO: Verificar ai_text_processor
        if self.ai_text_processor is None or self.formatter is None or self.recognizer is None or self.language is None:
            QMessageBox.critical(self, "Error de configuración",
                                 "Los procesadores o el reconocedor no han sido inicializados correctamente.")
            logger.error(
                "Intento de procesar archivo sin procesadores/reconocedor/idioma inicializados.")
            return

        # Si ya hay una transcripción en curso, preguntar al usuario
        if self.transcription_thread and self.transcription_thread.isRunning():
            reply = QMessageBox.question(self, "Proceso en curso",
                                         "Ya hay un proceso de transcripción activo. ¿Deseas cancelarlo e iniciar uno nuevo?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.cancel_transcription()
                # Esperar un momento para que el hilo actual termine
                if self.transcription_thread and self.transcription_thread.isRunning():
                    self.transcription_thread.wait(
                        2000)  # Esperar hasta 2 segundos
                    if self.transcription_thread.isRunning():
                        logger.warning(
                            "El hilo anterior no terminó después de la cancelación.")

            else:
                logger.info(
                    "Nueva solicitud de archivo ignorada, proceso en curso.")
                return  # No iniciar un nuevo proceso

        logger.info(f"Procesando archivo: {file_path}")
        # Actualizar texto de la UI
        self.label.setText(f"Procesando: {os.path.basename(file_path)}")

        # Crear y ejecutar el hilo de transcripción
        # MODIFICADO: Pasar ai_text_processor y formatter al hilo
        self.transcription_thread = TranscriptionThread(
            file_path=file_path,
            # <-- Pasar la instancia del procesador de texto
            ai_text_processor=self.ai_text_processor,
            formatter=self.formatter,  # <-- Pasar el formateador
            recognizer=self.recognizer,
            language=self.language  # Asegurarse de pasar el idioma guardado
        )

        # Conectar señales del hilo
        self.transcription_thread.progress_updated.connect(
            self.on_progress_updated)
        self.transcription_thread.transcription_completed.connect(
            self.on_transcription_completed)
        self.transcription_thread.transcription_error.connect(
            self.on_transcription_error)
        # conectar la señal finished para limpiar al terminar (éxito o error)
        self.transcription_thread.finished.connect(
            self.on_transcription_finished)

        # Mostrar diálogo de progreso
        self.progress_dialog = QProgressDialog(
            f"Transcribiendo {os.path.basename(file_path)}...", "Cancelar", 0, 100, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.setAutoReset(False)
        self.progress_dialog.canceled.connect(self.cancel_transcription)
        self.progress_dialog.show()

        self.transcription_thread.start()

    def on_progress_updated(self, message: str, percentage: int):
        """Actualiza el diálogo de progreso con el estado actual."""
        if self.progress_dialog:
            self.progress_dialog.setLabelText(message)
            # Solo actualizar el valor si el porcentaje es válido (no -1 para error)
            if percentage >= 0:
                self.progress_dialog.setValue(percentage)
            # Si porcentaje es -1, es un error, podríamos querer mantener el 0 o mostrar un estado visual de error
            elif percentage == -1:
                # O algún indicador visual de error
                self.progress_dialog.setValue(0)

    def on_transcription_completed(self, output_path: str):
        """Maneja la señal de transcripción completada."""
        logger.info(f"Proceso de transcripción finalizado para {output_path}")
        if self.progress_dialog:
            self.progress_dialog.setLabelText("¡Completado!")
            self.progress_dialog.setValue(100)
            # Podrías auto-cerrar el diálogo después de un pequeño retraso o dejar que el usuario lo cierre
            # self.progress_dialog.close() # Opcional: cerrar automáticamente

        self.label.setText(
            f"¡Transcripción completada!\nArchivo guardado en:\n{output_path}\n\nArrastra otro archivo para procesar")

        # Limpiar la referencia al hilo (se hace mejor en on_transcription_finished)
        # self.transcription_thread = None

    def on_transcription_error(self, error_message: str):
        """Maneja la señal de error durante la transcripción."""
        logger.error(
            f"Error recibido en on_transcription_error: {error_message}")
        if self.progress_dialog:
            self.progress_dialog.setLabelText("¡Error!")
            # Resetear o poner un valor de error
            self.progress_dialog.setValue(0)
            # Mostrar un mensaje de error al usuario
            QMessageBox.critical(self, "Error de Transcripción",
                                 f"Ocurrió un error durante la transcripción:\n{error_message}")

        self.label.setText(
            f"Error durante la transcripción:\n{error_message}\n\nArrastra otro archivo para intentar de nuevo")

        # Limpiar la referencia al hilo (se hace mejor en on_transcription_finished)
        # self.transcription_thread = None

    def on_transcription_finished(self):
        """Señal emitida cuando el hilo de transcripción termina (éxito o error)."""
        logger.info("Hilo de transcripción finalizado.")
        if self.transcription_thread:
            # Desconectar señales para evitar conexiones múltiples si el hilo se reusa (no es el caso aquí)
            # Usar un bloque try para manejar el caso si las señales ya fueron desconectadas
            try:
                self.transcription_thread.progress_updated.disconnect()
                self.transcription_thread.transcription_completed.disconnect()
                self.transcription_thread.transcription_error.disconnect()
                self.transcription_thread.finished.disconnect()
            # Capturar TypeError o RuntimeError si la señal ya está desconectada
            except (TypeError, RuntimeError):
                pass  # Señales ya desconectadas o no conectadas

            self.transcription_thread = None  # Limpiar la referencia al hilo

        if self.progress_dialog:
            # Mantener el diálogo abierto para que el usuario vea el estado final (Completado o Error)
            # Si quieres que se cierre automáticamente después de un pequeño retraso o éxito, añade un timer aquí.
            pass  # No cerrar automáticamente

    def cancel_transcription(self):
        """Cancela el hilo de transcripción si está corriendo."""
        if self.transcription_thread and self.transcription_thread.isRunning():
            logger.warning("Cancelando hilo de transcripción...")
            self.transcription_thread.cancel()  # Llamar al método cancel del hilo
            if self.progress_dialog:
                self.progress_dialog.setLabelText("Cancelando...")
                # Deshabilitar el botón de cancelar mientras se cancela
                self.progress_dialog.setEnabled(False)
            # El hilo emitirá finished cuando la cancelación sea efectiva

        else:
            logger.info(
                "No hay hilo de transcripción corriendo para cancelar.")
            if self.progress_dialog:
                # Si el diálogo está abierto pero no hay hilo corriendo, solo cerrarlo
                self.progress_dialog.close()


# NOTA: La función extract_and_transcribe está en audio_extractor.py
# Asegúrate de que extract_and_transcribe acepte ai_text_processor y formatter
# y que TranscriptionThread la llame con los argumentos correctos.
# Esta importación debe ser relativa

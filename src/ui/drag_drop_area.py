from transcriber.audio_extractor import extract_and_transcribe
from PyQt5.QtWidgets import QLabel, QMessageBox
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import sys
sys.path.append('..')


class TranscriptionThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            result = extract_and_transcribe(self.file_path)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class DragDropArea(QLabel):
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setText("Arrastra y suelta tu archivo de video aquí")
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 5px;
                padding: 20px;
                background: #f0f0f0;
            }
        """)
        self.setAcceptDrops(True)
        self.thread = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            self.setStyleSheet("""
                QLabel {
                    border: 2px dashed #4CAF50;
                    border-radius: 5px;
                    padding: 20px;
                    background: #E8F5E9;
                }
            """)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 5px;
                padding: 20px;
                background: #f0f0f0;
            }
        """)

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.process_file(files[0])

    def process_file(self, file_path):
        self.setText("Procesando archivo...\nPor favor espere...")
        self.thread = TranscriptionThread(file_path)
        self.thread.finished.connect(self.on_transcription_finished)
        self.thread.error.connect(self.on_transcription_error)
        self.thread.start()

    def on_transcription_finished(self, output_path):
        self.setText(
            "¡Transcripción completada!\nArrasta otro archivo para procesar")
        QMessageBox.information(self, "Éxito",
                                f"Transcripción guardada en:\n{output_path}")

    def on_transcription_error(self, error_message):
        self.setText("Arrastra y suelta tu archivo de video aquí")
        QMessageBox.critical(self, "Error",
                             f"Error durante la transcripción:\n{error_message}")

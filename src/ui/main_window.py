from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget
from .drag_drop_area import DragDropArea


class MainWindow(QMainWindow):
    def __init__(self, text_processor=None):  # Hacemos opcional el text_processor
        super().__init__()
        self.text_processor = text_processor
        self.init_ui()

    def init_ui(self):
        """Inicializa la interfaz de usuario"""
        # Configuración de la ventana
        self.setWindowTitle("Transcriptor de Video")
        self.setMinimumSize(600, 400)

        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout principal
        layout = QVBoxLayout(central_widget)

        # Área de arrastrar y soltar
        self.drag_drop_area = DragDropArea()
        layout.addWidget(self.drag_drop_area)

        # Si tenemos procesador de texto, lo pasamos al área de arrastre
        if self.text_processor:
            self.drag_drop_area.set_text_processor(self.text_processor)
